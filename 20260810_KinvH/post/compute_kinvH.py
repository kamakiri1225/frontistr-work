#!/usr/bin/env python3
"""
compute_kinvH.py — FrontISTR の K と H から、節点温度 -> 節点変位 の変換行列
                   W = K^{-1} H を組み立て、任意の温度場に対する変位を計算する。

前提と関係式:
    K u = f,   f = H T   =>   u = K^{-1} H T = W T
  ・K   : 境界条件適用後の全体剛性行列（model/001_K/K_bc.csr）
          固定自由度は「対角=1, 他=0」に置換されている。
  ・H   : 生の温度荷重変換行列（model/004_H/H_fistr.npz, 1275x425）

境界条件の扱い（重要）:
  FrontISTR が熱応力を解くとき、固定自由度 i は u_i=0 に固定され、
  その行の右辺は 0 に置き換えられる。したがって温度荷重 H T も、
  固定自由度の行を 0 にしてから K_bc を解く必要がある。
    W = K_bc^{-1} (固定行を0にした H)
  これで u = W T の固定自由度は自動的に 0 になる。

使い方:
  python3 compute_kinvH.py                 # W を計算・保存し、検証と2点デモを表示
  python3 compute_kinvH.py --temp uniform:100   # 全節点 100 度のときの変位
  python3 compute_kinvH.py --points 283 100     # 変位を見る節点を指定（2点）
"""
import argparse
import os
import sys
import numpy as np
from scipy.sparse import csr_matrix, csc_matrix
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
K_CSR = os.path.join(ROOT, 'model', '001_K', 'K_bc.csr')
H_NPZ = os.path.join(ROOT, 'model', '004_H', 'H_fistr.npz')
MSH = os.path.join(ROOT, 'model', '001_K', 'FistrModel.msh')
OUT_NPY = os.path.join(ROOT, 'model', '004_H', 'KinvH.npy')

sys.path.insert(0, HERE)
from read_fistr_matrix import read_csr           # noqa: E402
from scipy.sparse import load_npz                 # noqa: E402


def read_fix_nodes(msh):
    """FistrModel.msh の !NGROUP=fix に属する節点番号（1-based）を返す。"""
    nodes = []
    in_fix = False
    for line in open(msh, encoding='utf-8', errors='ignore'):
        s = line.strip()
        if s.startswith('!'):
            in_fix = s.startswith('!NGROUP') and 'fix' in s
            continue
        if in_fix and s:
            for tok in s.replace(',', ' ').split():
                if tok.isdigit():
                    nodes.append(int(tok))
    return sorted(set(nodes))


def fixed_dofs(fix_nodes, ndof_per_node=3):
    """固定節点 -> 固定自由度番号（0-based）。FrontISTR: 節点n -> 3(n-1)+{0,1,2}."""
    d = []
    for n in fix_nodes:
        base = ndof_per_node * (n - 1)
        d.extend([base, base + 1, base + 2])
    return np.array(sorted(d), dtype=np.int64)


def build_W(K, H, fix_dof):
    """W = K^{-1} (固定行を0にしたH) を列ごとに解いて返す（dense n_dof x n_node）。"""
    K = csc_matrix(K)
    n = K.shape[0]
    Hd = H.toarray() if hasattr(H, 'toarray') else np.asarray(H, float)
    Hd = Hd.copy()
    Hd[fix_dof, :] = 0.0                 # 固定自由度の行を0に（BC適用）
    solve = factorized(K)               # K を1度だけLU分解して再利用
    W = np.empty_like(Hd)
    for j in range(Hd.shape[1]):
        W[:, j] = solve(Hd[:, j])
    return W, Hd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--temp', default='uniform:100',
                    help='温度場。uniform:VALUE か、node:val,node:val,... 形式')
    ap.add_argument('--points', type=int, nargs='+', default=[283, 100],
                    help='変位を表示する節点番号（既定: 283 と 100）')
    ap.add_argument('--diff', type=int, nargs=2, metavar=('N1', 'N2'),
                    help='2点の相対変位 u_N1 - u_N2 = (W_N1 - W_N2) T を計算する')
    args = ap.parse_args()

    print('K を読み込み:', K_CSR)
    K = read_csr(K_CSR)
    print('H を読み込み:', H_NPZ)
    H = load_npz(H_NPZ)
    nnode = H.shape[1]
    ndof = H.shape[0]
    print(f'  K: {K.shape},  H: {H.shape}  (節点数 {nnode}, 自由度 {ndof})')

    fix_nodes = read_fix_nodes(MSH)
    fix_dof = fixed_dofs(fix_nodes)
    print(f'  固定節点 {len(fix_nodes)} 個 -> 固定自由度 {len(fix_dof)} 個')

    W, Hbc = build_W(K, H, fix_dof)
    np.save(OUT_NPY, W)
    print(f'W = K^-1 H を保存: {OUT_NPY}  shape={W.shape}')

    # 妥当性チェック：K W = Hbc になっているか
    R = K.dot(W) - Hbc
    rel = np.linalg.norm(R) / (np.linalg.norm(Hbc) or 1.0)
    print(f'[検証] ||K W - H_bc|| / ||H_bc|| = {rel:.3e}')

    # 温度場 T を作る
    T = np.zeros(nnode)
    if args.temp.startswith('uniform:'):
        val = float(args.temp.split(':', 1)[1])
        T[:] = val
        desc = f'全節点 {val} 度'
    else:
        desc = args.temp
        for part in args.temp.split(','):
            nid, val = part.split(':')
            T[int(nid) - 1] = float(val)

    u = W @ T
    print(f'\n温度場: {desc}')
    print(f'最大変位 |u|max = {np.abs(u).max():.6e} mm')

    print('\n指定した点の変位:')
    for nid in args.points:
        b = 3 * (nid - 1)
        ux, uy, uz = u[b], u[b + 1], u[b + 2]
        print(f'  節点{nid:4d}: ux={ux:+.6e}  uy={uy:+.6e}  uz={uz:+.6e}  '
              f'|u|={np.sqrt(ux*ux+uy*uy+uz*uz):.6e}')

    # 2点の相対変位 u_N1 - u_N2 = (W_N1 - W_N2) T
    if args.diff:
        n1, n2 = args.diff
        b1, b2 = 3 * (n1 - 1), 3 * (n2 - 1)
        Wdiff = W[b1:b1 + 3, :] - W[b2:b2 + 3, :]     # 3 x nnode（相対変位の変換行列）
        u_rel = Wdiff @ T
        np.save(os.path.join(ROOT, 'model', '004_H', f'Wdiff_{n1}_{n2}.npy'), Wdiff)
        print(f'\n2点の相対変位  節点{n1} - 節点{n2}:')
        print(f'  (W_{n1} - W_{n2}) は {Wdiff.shape} の行列（この2点の相対変位専用）')
        print(f'  u_{n1} - u_{n2} = {u_rel}')
        print(f'  保存: Wdiff_{n1}_{n2}.npy')


if __name__ == '__main__':
    main()
