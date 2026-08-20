#!/usr/bin/env python3
"""
ThermoSenseAnalyzer_standalone.py — ThermoSenseAnalyzer_00.py と完全に同じ数式
    （make_D/make_CTE/make_B/make_He/make_Ke, 全体K・全体H・W=K^-1Hの組み立て）を、
    settings.yml不要・マルチプロセス不要で動かせるようにした単体版。

ThermoSenseAnalyzer_00.py をこのフォルダでそのまま実行できない理由:
  ・setting/settings.yml, setting/settings_cores.yml が本リポジトリに無い
    （Word_1〜Word_11の*NSET検索キーワード、コア数設定）
  ・CLI引数・multiprocessingなど、FrontISTRとの数値比較には不要な処理が多い

このファイルは ThermoSenseAnalyzer_00.py と同じ Inp_Data フォルダに置き、
同じ Quad4_FEM_Tji.inp をこのフォルダ内で直接読み、結果もこのフォルダ内
（Results/）に書き出す。

材料定数は Quad4_FEM_Tji.inp の実際の値を使う:
  E=130000000, nu=0.27, density=7.4e-06, CTE=1.2e-05
※ ThermoSenseAnalyzer_00.py 本体は E=130000.0, CTE=1e-5 をハードコードしており、
  このinpの実際の値とは一致しない（このファイルはinpの値を優先する）。

出力（このフォルダ内 Results/）:
  H_python_tji.npz        生H（境界条件なし, DOF_TOTAL x NODES）
  K_python_tji_bc.mtx     境界条件適用後のK
  Wdiff_python_tji.npy    W=K^-1H から Point_A(節点19)-Point_O(節点103) を抜き出した (3, NODES)
"""
import os
import re
import time
import numpy as np
import numpy.linalg as LA
from scipy import sparse
from scipy.io import mmwrite
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, 'Quad4_FEM_Tji.inp')
OUT_DIR = os.path.join(HERE, 'Results')

NODE_TET4 = 4
COMPONENTS = 6
DOF_NODE = 3
weight = 1.0 / 6.0


def parse_inp(path):
    """Quad4_FEM_Tji.inp から節点・要素・固定節点・Point_A/O・材料定数を読む。"""
    nodes, elements = {}, {}
    fixed_nodes = []
    point_a = point_o = None
    young = poisson = density = cte = None

    section, nset_name = None, None
    for raw in open(path, encoding='utf-8', errors='ignore'):
        s = raw.strip()
        if s.startswith('*'):
            head = s.upper()
            if head.startswith('*NODE'):
                section = 'NODE'
            elif head.startswith('*ELEMENT') and 'C3D4' in head:
                section = 'ELEMENT'
            elif head.startswith('*NSET'):
                section = 'NSET'
                m = re.search(r'NSET="([^"]+)"', s)
                nset_name = m.group(1) if m else ''
            elif head.startswith('*ELASTIC'):
                section = 'ELASTIC'
            elif head.startswith('*DENSITY'):
                section = 'DENSITY'
            elif head.startswith('*EXPANSION'):
                section = 'EXPANSION'
            else:
                section = None
            continue

        if section == 'NODE' and s:
            p = s.split(',')
            nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif section == 'ELEMENT' and s:
            p = s.split(',')
            elements[int(p[0])] = [int(v) for v in p[1:5]]
        elif section == 'NSET' and s:
            ids = [int(v) for v in s.replace(',', ' ').split()]
            if nset_name.startswith('Fixed'):
                fixed_nodes.extend(ids)
            elif nset_name.startswith('Point_A'):
                point_a = ids[0]
            elif nset_name.startswith('Point_O'):
                point_o = ids[0]
        elif section == 'ELASTIC' and s:
            p = s.split(',')
            young, poisson = float(p[0]), float(p[1])
            section = None
        elif section == 'DENSITY' and s:
            density = float(s.split(',')[0])
            section = None
        elif section == 'EXPANSION' and s:
            cte = float(s.split(',')[0])
            section = None

    return {
        'nodes': nodes, 'elements': elements, 'fixed_nodes': sorted(set(fixed_nodes)),
        'point_a': point_a, 'point_o': point_o,
        'young': young, 'poisson': poisson, 'density': density, 'cte': cte,
    }


def write_vtk(path, nodes, node_ids, elements, elem_ids, vec_field, field_name):
    nid_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    with open(path, 'w', encoding='ascii') as f:
        f.write('# vtk DataFile Version 2.0\n')
        f.write(f'{field_name} (Wdiff: Point_A - Point_O per unit nodal temperature)\n')
        f.write('ASCII\nDATASET UNSTRUCTURED_GRID\n')
        f.write(f'POINTS {len(node_ids)} double\n')
        for nid in node_ids:
            x, y, z = nodes[nid]
            f.write(f'{x} {y} {z}\n')
        f.write(f'CELLS {len(elem_ids)} {len(elem_ids) * 5}\n')
        for eid in elem_ids:
            conn = [nid_to_idx[n] for n in elements[eid]]
            f.write('4 ' + ' '.join(str(c) for c in conn) + '\n')
        f.write(f'CELL_TYPES {len(elem_ids)}\n')
        for _ in elem_ids:
            f.write('10\n')
        f.write(f'POINT_DATA {len(node_ids)}\nVECTORS {field_name} double\n')
        for i in range(len(node_ids)):
            vx, vy, vz = vec_field[0, i], vec_field[1, i], vec_field[2, i]
            f.write(f'{vx} {vy} {vz}\n')


def main():
    model = parse_inp(INP)
    nodes, elements = model['nodes'], model['elements']
    young, poisson, cte = model['young'], model['poisson'], model['cte']

    node_ids = sorted(nodes)
    nid_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    NODES = len(node_ids)
    elem_ids = sorted(elements)
    ELEMENTS = len(elem_ids)
    DOF_TOTAL = DOF_NODE * NODES
    DOF_TET4 = NODE_TET4 * DOF_NODE

    X = np.array([nodes[nid][0] for nid in node_ids])
    Y = np.array([nodes[nid][1] for nid in node_ids])
    Z = np.array([nodes[nid][2] for nid in node_ids])
    connectivity = np.array([[nid_to_idx[n] for n in elements[eid]] for eid in elem_ids])

    print(f'NODES={NODES}, ELEMENTS={ELEMENTS}, DOF_TOTAL={DOF_TOTAL}')
    print(f'material: E={young}, nu={poisson}, density={model["density"]}, CTE={cte}')

    coef = young / (1 - 2 * poisson) / (1 + poisson)
    D = np.array([
        [coef * (1 - poisson), coef * poisson, coef * poisson, 0, 0, 0],
        [coef * poisson, coef * (1 - poisson), coef * poisson, 0, 0, 0],
        [coef * poisson, coef * poisson, coef * (1 - poisson), 0, 0, 0],
        [0, 0, 0, coef * (1 - 2 * poisson) / 2, 0, 0],
        [0, 0, 0, 0, coef * (1 - 2 * poisson) / 2, 0],
        [0, 0, 0, 0, 0, coef * (1 - 2 * poisson) / 2],
    ])

    CTE_T = np.array([[cte, cte, cte, 0.0, 0.0, 0.0]] * 4)
    CTE = (1 / 4.0) * CTE_T.T

    dN_dabc = np.array([[-1.0, -1.0, -1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    rows_H, cols_H, vals_H = [], [], []
    rows_K, cols_K, vals_K = [], [], []

    t_assemble0 = time.time()
    for e in range(ELEMENTS):
        c = connectivity[e]
        xe, ye, ze = X[c], Y[c], Z[c]
        Jmat = dN_dabc.T @ np.column_stack([xe, ye, ze])
        dN_dxyz = LA.solve(Jmat, dN_dabc.T).T

        B = np.zeros((COMPONENTS, DOF_TET4))
        for a in range(4):
            dx, dy, dz = dN_dxyz[a]
            B[0, 3 * a + 0] = dx
            B[1, 3 * a + 1] = dy
            B[2, 3 * a + 2] = dz
            B[3, 3 * a + 0] = dy
            B[3, 3 * a + 1] = dx
            B[4, 3 * a + 1] = dz
            B[4, 3 * a + 2] = dy
            B[5, 3 * a + 0] = dz
            B[5, 3 * a + 2] = dx

        detJ = LA.det(Jmat)
        Ke = weight * B.T @ D @ B * detJ

        Huq = np.column_stack([np.ones(4), xe, ye, ze])
        Hqu = LA.inv(Huq)
        detHuq = LA.det(Huq)

        C_mat = np.zeros((COMPONENTS, DOF_TET4))
        for a in range(4):
            h1, h2, h3 = Hqu[1, a], Hqu[2, a], Hqu[3, a]
            C_mat[0, 3 * a + 0] = h1
            C_mat[1, 3 * a + 1] = h2
            C_mat[2, 3 * a + 2] = h3
            C_mat[3, 3 * a + 0] = h2
            C_mat[3, 3 * a + 1] = h1
            C_mat[4, 3 * a + 1] = h3
            C_mat[4, 3 * a + 2] = h2
            C_mat[5, 3 * a + 0] = h3
            C_mat[5, 3 * a + 2] = h1

        He = weight * C_mat.T @ D @ CTE * detHuq

        for r in range(DOF_TET4):
            rt = c[r // DOF_NODE] * DOF_NODE + (r % DOF_NODE)
            for cc in range(NODE_TET4):
                rows_H.append(rt); cols_H.append(c[cc]); vals_H.append(He[r, cc])
            for cc in range(DOF_TET4):
                ct = c[cc // DOF_NODE] * DOF_NODE + (cc % DOF_NODE)
                rows_K.append(rt); cols_K.append(ct); vals_K.append(Ke[r, cc])

        if (e + 1) % 300 == 0 or e + 1 == ELEMENTS:
            print(f'  assembled {e + 1}/{ELEMENTS} elements', flush=True)

    H = sparse.coo_matrix((vals_H, (rows_H, cols_H)), shape=(DOF_TOTAL, NODES)).tocsr()
    K = sparse.coo_matrix((vals_K, (rows_K, cols_K)), shape=(DOF_TOTAL, DOF_TOTAL)).tocsr()
    t_assemble1 = time.time()
    print(f'H: {H.shape} nnz={H.nnz}')
    print(f'K: {K.shape} nnz={K.nnz}')
    print(f'[time] K・H 要素ループ組み立て: {t_assemble1 - t_assemble0:.3f} s')

    os.makedirs(OUT_DIR, exist_ok=True)
    sparse.save_npz(os.path.join(OUT_DIR, 'H_python_tji.npz'), H)
    t_h_save = time.time()
    print(f'[time] H 保存 (npz): {t_h_save - t_assemble1:.3f} s')

    t_bc0 = time.time()
    fixed_dof = []
    for nid in model['fixed_nodes']:
        b = nid_to_idx[nid] * DOF_NODE
        fixed_dof.extend([b, b + 1, b + 2])
    fixed_dof = np.array(sorted(set(fixed_dof)))

    K_lil = K.tolil()
    Hd = H.toarray()
    Hd[fixed_dof, :] = 0.0
    for r in fixed_dof:
        K_lil.rows[r] = [r]
        K_lil.data[r] = [1.0]
    K_bc = K_lil.tocsc().tolil()
    for r in fixed_dof:
        rows_nz = K_bc[:, r].nonzero()[0]
        for rr in rows_nz:
            if rr != r:
                K_bc[rr, r] = 0.0
    K_bc = K_bc.tocsc()
    t_bc1 = time.time()
    print(f'[time] 境界条件処理(K・H): {t_bc1 - t_bc0:.3f} s')
    mmwrite(os.path.join(OUT_DIR, 'K_python_tji_bc.mtx'), K_bc)

    t_solve0 = time.time()
    solve = factorized(K_bc)
    W = np.empty_like(Hd)
    for j in range(Hd.shape[1]):
        W[:, j] = solve(Hd[:, j])
    t_solve1 = time.time()
    print(f'[time] W = K^-1 H 求解 ({Hd.shape[1]}列): {t_solve1 - t_solve0:.3f} s')

    tool_idx = nid_to_idx[model['point_a']]
    origin_idx = nid_to_idx[model['point_o']]
    b_t, b_o = 3 * tool_idx, 3 * origin_idx
    Wdiff = W[b_t:b_t + 3, :] - W[b_o:b_o + 3, :]
    np.save(os.path.join(OUT_DIR, 'Wdiff_python_tji.npy'), Wdiff)
    write_vtk(os.path.join(OUT_DIR, 'Wdiff_python_tji.vtk'), nodes, node_ids, elements, elem_ids,
              Wdiff, 'Sensitivity_Python')

    print(f'point_a(node {model["point_a"]}) idx={tool_idx}, '
          f'point_o(node {model["point_o"]}) idx={origin_idx}')
    print(f'Wdiff: {Wdiff.shape}')
    print(f'saved to {OUT_DIR}: H_python_tji.npz / K_python_tji_bc.mtx / '
          f'Wdiff_python_tji.npy / Wdiff_python_tji.vtk')
    print(f'[time] 合計 (K・H組立+保存+BC+W求解): {time.time() - t_assemble0:.3f} s')


if __name__ == '__main__':
    main()
