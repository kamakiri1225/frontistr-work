#!/usr/bin/env python3
"""
python_H_tji.py — sample/002_thermalSensitive/Inp_Data/ThermoSenseAnalyzer_00.py と
                   同じ要素定式化（C3D4, make_D/make_CTE/make_B/make_He/make_Ke）を
                   忠実に再現し、Quad4_FEM_Tji.inp から H・K・W を直接計算する。

ThermoSenseAnalyzer_00.py をそのまま動かさない理由:
  ・settings/settings.yml, settings/settings_cores.yml が本リポジトリに無い
  ・CLI引数・マルチプロセスなどFrontISTR比較に不要な処理が多い
  ここでは同じ数式だけを取り出し、*.inpの実際の材料定数
  （E=130000000, nu=0.27, density=7.4e-06, CTE=1.2e-05）をそのまま使う。
  ※ThermoSenseAnalyzer_00.py は E=130000.0, nu=0.27, CTE=1e-5 を
    ハードコードしており、このinpの実際の値とは一致しない点に注意。

出力:
  model/008_Tji_compare/H_python_tji.npz  （生H, 境界条件なし）
  model/008_Tji_compare/Wdiff_python_tji.npy （(3, n_node), 節点19-節点103の変位差用）
"""
import os
import sys
import time
import numpy as np
import numpy.linalg as LA
from scipy import sparse
from scipy.io import mmwrite
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from inp_to_fistr_msh import parse_inp, INP  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'model', '008_Tji_compare')

NODE_TET4 = 4
COMPONENTS = 6
DOF_NODE = 3
weight = 1.0 / 6.0


def main():
    model = parse_inp(INP)
    nodes = model['nodes']
    elements = model['elements']
    young, poisson, cte = model['young'], model['poisson'], model['cte']

    node_ids = sorted(nodes)
    nid_to_idx = {nid: i for i, nid in enumerate(node_ids)}  # 0-based
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

    # D matrix
    coef = young / (1 - 2 * poisson) / (1 + poisson)
    D = np.array([
        [coef * (1 - poisson), coef * poisson, coef * poisson, 0, 0, 0],
        [coef * poisson, coef * (1 - poisson), coef * poisson, 0, 0, 0],
        [coef * poisson, coef * poisson, coef * (1 - poisson), 0, 0, 0],
        [0, 0, 0, coef * (1 - 2 * poisson) / 2, 0, 0],
        [0, 0, 0, 0, coef * (1 - 2 * poisson) / 2, 0],
        [0, 0, 0, 0, 0, coef * (1 - 2 * poisson) / 2],
    ])

    # CTE matrix (1/4 averaging over 4 nodes, same as ThermoSenseAnalyzer_00.py)
    CTE_T = np.array([[cte, cte, cte, 0.0, 0.0, 0.0]] * 4)
    CTE = (1 / 4.0) * CTE_T.T  # (6,4)

    dN_dabc = np.array([
        [-1.0, -1.0, -1.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ])  # (4,3): dNi/da,db,dc

    rows_H, cols_H, vals_H = [], [], []
    rows_K, cols_K, vals_K = [], [], []

    t_assemble0 = time.time()
    for e in range(ELEMENTS):
        c = connectivity[e]
        xe, ye, ze = X[c], Y[c], Z[c]
        Jmat = dN_dabc.T @ np.column_stack([xe, ye, ze])  # (3,3): rows a,b,c / cols x,y,z
        dN_dxyz = LA.solve(Jmat, dN_dabc.T).T  # (4,3): dNi/dx,dy,dz

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

        Huq = np.column_stack([np.ones(4), xe, ye, ze])  # (4,4)
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

        He = weight * C_mat.T @ D @ CTE * detHuq  # (12,4)

        for r in range(DOF_TET4):
            rt = c[r // DOF_NODE] * DOF_NODE + (r % DOF_NODE)
            for cc in range(NODE_TET4):
                ct = c[cc]
                rows_H.append(rt); cols_H.append(ct); vals_H.append(He[r, cc])
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

    # --- boundary condition (same as set_baoudary(): fixed dof rows/cols -> identity, H row -> 0)
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
    K_bc = K_lil.tocsc()
    # also zero the fixed columns to mirror set_baoudary()'s K[:,r]=0 (symmetric BC)
    K_bc = K_bc.tolil()
    for r in fixed_dof:
        col = K_bc[:, r]
        rows_nz = col.nonzero()[0]
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

    print(f'point_a(node {model["point_a"]}) idx={tool_idx}, '
          f'point_o(node {model["point_o"]}) idx={origin_idx}')
    print(f'Wdiff: {Wdiff.shape}')
    print('saved H_python_tji.npz / K_python_tji_bc.mtx / Wdiff_python_tji.npy')
    print(f'[time] 合計 (K・H組立+保存+BC+W求解): {time.time() - t_assemble0:.3f} s')


if __name__ == '__main__':
    main()
