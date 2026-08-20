#!/usr/bin/env python3
"""
wdiff_adjoint.py — Wdiff = (K^-1 H)[Point_A行] - (K^-1 H)[Point_O行] を、
    アジョイント（随伴）法で高速に計算する。

原理:
  Kは対称なので K^-1 も対称。Wdiffの各行（Point_A/Point_Oの3自由度ずつ、計6自由度）は
      row_i = e_i^T K^-1 H = (K^-1 e_i)^T H = z_i^T H       (z_i = K^-1 e_i を解く)
  で求まる。求める行が6本だけなら、Hの列数（節点数）に関係なく **6回のsolveだけ**で済む。
  ThermoSenseAnalyzer_00.py / python_H_tji.py / compute_kinvH_tji.py が使っている
  「Hの全列についてforward solve」方式（列数と同じ回数のsolveが必要）より、
  節点数が多いメッシュでは大幅に高速（ただし計算結果はWdiffとして数学的に同一）。

使い方:
  python3 wdiff_adjoint.py --workdir model/010_Tji_fine_H_direct \
      --k K_fistr_tji_fine.mm --h H_matrix.mtx --out Wdiff_fistr_tji_fine_adj.npy \
      --mesh-npz mesh_fine.npz
"""
import argparse
import os
import time
import numpy as np
from scipy.io import mmread
from scipy.sparse import csc_matrix, load_npz
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

POINT_A_NODE = 19
POINT_O_NODE = 103


def load_matrix(path):
    if path.endswith('.npz'):
        return load_npz(path)
    return mmread(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--k', required=True)
    ap.add_argument('--h', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mesh-npz', default=None)
    args = ap.parse_args()

    work = os.path.join(ROOT, args.workdir)

    t0 = time.time()
    K = csc_matrix(load_matrix(os.path.join(work, args.k)))
    H = load_matrix(os.path.join(work, args.h))
    t1 = time.time()
    print(f'load: K {K.shape}, H {H.shape}  ({t1 - t0:.3f} s)')

    if args.mesh_npz:
        data = np.load(os.path.join(work, args.mesh_npz), allow_pickle=True)
        node_ids = sorted(int(n) for n in data['node_ids'])
        fixed_nodes = [int(n) for n in data['fixed_nodes']]
    else:
        import sys
        sys.path.insert(0, HERE)
        from inp_to_fistr_msh import parse_inp, INP
        model = parse_inp(INP)
        node_ids = sorted(model['nodes'])
        fixed_nodes = model['fixed_nodes']
    nid_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    fixed_dof = []
    for nid in fixed_nodes:
        b = nid_to_idx[nid] * 3
        fixed_dof.extend([b, b + 1, b + 2])
    fixed_dof = np.array(sorted(set(fixed_dof)))

    Hs = H.tocsr() if hasattr(H, 'tocsr') else csc_matrix(H)
    n_dof = K.shape[0]

    t2 = time.time()
    solve = factorized(K)
    tool_idx = nid_to_idx[POINT_A_NODE]
    origin_idx = nid_to_idx[POINT_O_NODE]
    dof_ids = [3 * tool_idx, 3 * tool_idx + 1, 3 * tool_idx + 2,
               3 * origin_idx, 3 * origin_idx + 1, 3 * origin_idx + 2]

    Z = np.empty((n_dof, 6))
    for j, dof in enumerate(dof_ids):
        e = np.zeros(n_dof)
        e[dof] = 1.0
        Z[:, j] = solve(e)   # K z = e_dof  (6回のsolveのみ)
    t3 = time.time()
    print(f'adjoint solve (6回): {t3 - t2:.3f} s')

    # H側は固定自由度の行を0に（Kは既にBC適用済み）
    # z^T H は z の固定自由度成分をゼロにしておけば、Hを密行列化せずに疎行列のまま計算できる
    Z[fixed_dof, :] = 0.0

    # rows = Z^T H を、Hを密行列化せず疎×密として計算する（H.T @ Z は (n_node,n_dof)@(n_dof,6)）
    rows = np.asarray(Hs.T @ Z).T  # (6, n_node)
    Wdiff = rows[0:3, :] - rows[3:6, :]
    t4 = time.time()
    print(f'Z^T H (疎×密 行列積): {t4 - t3:.3f} s')

    out_path = os.path.join(work, args.out)
    np.save(out_path, Wdiff)
    print(f'{out_path}: {Wdiff.shape}  saved')
    print(f'total (load+adjoint solve+matmul): {time.time() - t0:.3f} s')


if __name__ == '__main__':
    main()
