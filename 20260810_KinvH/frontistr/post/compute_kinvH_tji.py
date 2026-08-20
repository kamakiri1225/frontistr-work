#!/usr/bin/env python3
"""
compute_kinvH_tji.py — FrontISTRが出力したK・Hから W = K^-1 H を計算し、
                        Point_A-Point_O の相対変位用行列 Wdiff を作る。
                        post/compute_kinvH.py のTjiモデル向け版。所要時間も計測する。
                        --workdir でフォルダを切り替えれば model/008, 009, 010 いずれでも使える。

使い方:
  python3 compute_kinvH_tji.py --workdir model/008_Tji_compare \
      --k K_fistr_tji.mm --h H_fistr_tji.npz --out Wdiff_fistr_tji.npy
  python3 compute_kinvH_tji.py --workdir model/009_Tji_H_direct \
      --k K_fistr_tji.mm --h H_matrix.mtx --out Wdiff_fistr_tji.npy
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

POINT_A_NODE = 19   # tool
POINT_O_NODE = 103  # origin


def load_matrix(path):
    if path.endswith('.npz'):
        return load_npz(path)
    return mmread(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workdir', default='model/008_Tji_compare')
    ap.add_argument('--k', default='K_fistr_tji.mm')
    ap.add_argument('--h', default='H_fistr_tji.npz')
    ap.add_argument('--out', default='Wdiff_fistr_tji.npy')
    ap.add_argument('--mesh-npz', default=None,
                     help='リファインメッシュなど、元のinpと節点数が異なる場合に指定する'
                          '（refine_tji_mesh.pyが作るmesh_fine.npzなど）')
    args = ap.parse_args()

    work = os.path.join(ROOT, args.workdir)

    t0 = time.time()
    K = csc_matrix(load_matrix(os.path.join(work, args.k)))
    H = load_matrix(os.path.join(work, args.h))
    t1 = time.time()
    print(f'load: K {K.shape}, H {H.shape}  ({t1 - t0:.3f} s)')

    # H側も同じ固定節点でBC適用（Kは!BOUNDARYで既にBC適用済みのdump）
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

    Hd = H.toarray() if hasattr(H, 'toarray') else np.asarray(H)
    Hd[fixed_dof, :] = 0.0

    t2 = time.time()
    solve = factorized(K)
    W = np.empty_like(Hd)
    for j in range(Hd.shape[1]):
        W[:, j] = solve(Hd[:, j])
    t3 = time.time()
    print(f'W = K^-1 H solve: {t3 - t2:.3f} s  ({Hd.shape[1]} columns)')

    R = K.dot(W) - Hd
    rel = np.linalg.norm(R) / (np.linalg.norm(Hd) or 1.0)
    print(f'[検証] ||K W - H_bc|| / ||H_bc|| = {rel:.3e}')

    tool_idx = nid_to_idx[POINT_A_NODE]
    origin_idx = nid_to_idx[POINT_O_NODE]
    bt, bo = 3 * tool_idx, 3 * origin_idx
    Wdiff = W[bt:bt + 3, :] - W[bo:bo + 3, :]
    out_path = os.path.join(work, args.out)
    np.save(out_path, Wdiff)
    print(f'{out_path}: {Wdiff.shape}  saved')
    print(f'total (load+BC+solve): {time.time() - t0:.3f} s')


if __name__ == '__main__':
    main()
