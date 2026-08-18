#!/usr/bin/env python3
"""
python_H_tji_fine.py — post/refine_tji_mesh.py が作ったリファイン済みメッシュ
    (model/010_Tji_fine_H_direct/mesh_fine.npz) に対して、python_H_tji.py と
    同じ数式でH・K（境界条件適用後）・W=K^-1Hを計算する。

出力: model/010_Tji_fine_H_direct/ 以下に
  H_python_tji_fine.npz, K_python_tji_fine_bc.mtx, Wdiff_python_tji_fine.npy
"""
import os
import time
import numpy as np
import numpy.linalg as LA
from scipy import sparse
from scipy.io import mmwrite
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, 'model', '010_Tji_fine_H_direct')

NODE_TET4 = 4
COMPONENTS = 6
DOF_NODE = 3
weight = 1.0 / 6.0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--young', type=float, default=None,
                     help='ヤング率を上書き（既定はmesh_fine.npzの値）')
    ap.add_argument('--cte', type=float, default=None,
                     help='線膨張係数を上書き（既定はmesh_fine.npzの値）')
    args = ap.parse_args()

    data = np.load(os.path.join(WORK, 'mesh_fine.npz'), allow_pickle=True)
    node_ids = data['node_ids']
    coords = data['coords']
    elem_ids = data['elem_ids']
    conn_nid = data['conn']  # 節点番号(1-based)
    fixed_node_ids = data['fixed_nodes']
    point_a_nid = int(data['point_a'])
    point_o_nid = int(data['point_o'])
    young = float(data['young']); poisson = float(data['poisson']); cte = float(data['cte'])
    if args.young is not None:
        young = args.young
    if args.cte is not None:
        cte = args.cte

    nid_to_idx = {int(n): i for i, n in enumerate(node_ids)}
    NODES = len(node_ids)
    ELEMENTS = len(elem_ids)
    DOF_TOTAL = DOF_NODE * NODES
    DOF_TET4 = NODE_TET4 * DOF_NODE

    X, Y, Z = coords[:, 0], coords[:, 1], coords[:, 2]
    connectivity = np.array([[nid_to_idx[int(n)] for n in row] for row in conn_nid])

    print(f'NODES={NODES}, ELEMENTS={ELEMENTS}, DOF_TOTAL={DOF_TOTAL}')
    print(f'material: E={young}, nu={poisson}, CTE={cte}')

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

        if (e + 1) % 2000 == 0 or e + 1 == ELEMENTS:
            print(f'  assembled {e + 1}/{ELEMENTS} elements', flush=True)

    H = sparse.coo_matrix((vals_H, (rows_H, cols_H)), shape=(DOF_TOTAL, NODES)).tocsr()
    K = sparse.coo_matrix((vals_K, (rows_K, cols_K)), shape=(DOF_TOTAL, DOF_TOTAL)).tocsr()
    t_assemble1 = time.time()
    print(f'H: {H.shape} nnz={H.nnz}')
    print(f'K: {K.shape} nnz={K.nnz}')
    print(f'[time] K・H 要素ループ組み立て: {t_assemble1 - t_assemble0:.3f} s')

    sparse.save_npz(os.path.join(WORK, 'H_python_tji_fine.npz'), H)
    t_h_save = time.time()
    print(f'[time] H 保存 (npz): {t_h_save - t_assemble1:.3f} s')

    t_bc0 = time.time()
    fixed_dof = []
    for nid in fixed_node_ids:
        b = nid_to_idx[int(nid)] * DOF_NODE
        fixed_dof.extend([b, b + 1, b + 2])
    fixed_dof = np.array(sorted(set(fixed_dof)))

    # Hは大きい節点数だと密行列化できない（22123節点なら 66369x22123 = 約11.7GB）ので、
    # 疎行列のまま固定自由度の行だけ0にする。
    H_lil = H.tolil()
    for r in fixed_dof:
        H_lil.rows[r] = []
        H_lil.data[r] = []
    H_bc = H_lil.tocsr()

    K_lil = K.tolil()
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
    mmwrite(os.path.join(WORK, 'K_python_tji_fine_bc.mtx'), K_bc)

    # W = K^-1 H の全列を求めず、Point_A/Point_Oの6自由度だけアジョイント法で求める
    # （docs/12 参照）。K z_i = e_i を6回solveし、Wdiff = (z_A - z_O)^T H_bc。
    t_solve0 = time.time()
    solve = factorized(K_bc)
    tool_idx = nid_to_idx[point_a_nid]
    origin_idx = nid_to_idx[point_o_nid]
    dof_ids = [3 * tool_idx, 3 * tool_idx + 1, 3 * tool_idx + 2,
               3 * origin_idx, 3 * origin_idx + 1, 3 * origin_idx + 2]
    Z = np.empty((DOF_TOTAL, 6))
    for j, dof in enumerate(dof_ids):
        e = np.zeros(DOF_TOTAL)
        e[dof] = 1.0
        Z[:, j] = solve(e)
    t_solve1 = time.time()
    print(f'[time] アジョイント法W求解 (6回): {t_solve1 - t_solve0:.3f} s')

    rows = np.asarray(H_bc.T @ Z).T  # (6, n_node)
    Wdiff = rows[0:3, :] - rows[3:6, :]
    t_matmul = time.time()
    print(f'[time] Z^T H (疎×密 行列積): {t_matmul - t_solve1:.3f} s')
    np.save(os.path.join(WORK, 'Wdiff_python_tji_fine.npy'), Wdiff)

    print(f'point_a(node {point_a_nid}) idx={tool_idx}, point_o(node {point_o_nid}) idx={origin_idx}')
    print(f'Wdiff: {Wdiff.shape}')
    print('saved H_python_tji_fine.npz / K_python_tji_fine_bc.mtx / Wdiff_python_tji_fine.npy')
    print(f'[time] 合計 (K・H組立+保存+BC+アジョイントW求解): {time.time() - t_assemble0:.3f} s')


if __name__ == '__main__':
    main()
