#!/usr/bin/env python3
"""
compare_K.py — FrontISTR と Python(Quad4_main.py) の全体剛性行列 K を比較する。

自由度の並びの違い:
  FrontISTR : 節点n -> 行 (3(n-1), +1, +2) = (x, y, z)   … 自然順
  Python    : 節点g -> 行 (3g=y, 3g+1=x, 3g+2=z)          … make_K の添字式で x,y が入替
節点の並び順は両者とも inp の節点順（1..N）で一致。

したがって「節点内で x と y を入れ替える」置換 perm で Python K を FrontISTR 並びに整列し、
K_fistr と比較する。

使い方:
  python3 compare_K.py <K_fistr.csr(or .mm)> <K_python.npz>
"""
import sys
import numpy as np
from scipy import sparse

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from read_fistr_matrix import read_csr, read_mm


def align_perm(n):
    """FrontISTR並び i -> Python並び perm[i]（節点内 x<->y 入替）。"""
    perm = np.arange(n)
    for g in range(n // 3):
        perm[3 * g] = 3 * g + 1      # FrontISTR x  = Python 3g+1
        perm[3 * g + 1] = 3 * g      # FrontISTR y  = Python 3g
        perm[3 * g + 2] = 3 * g + 2  # z 同じ
    return perm


def load_any(path):
    if path.endswith('.npz'):
        return sparse.load_npz(path).tocsr().astype(float)
    if path.endswith('.mm'):
        return read_mm(path).astype(float)
    return read_csr(path).tocsr().astype(float)


def frob(A):
    return float(np.sqrt((A.multiply(A)).sum()))


def main():
    fistr = sys.argv[1] if len(sys.argv) > 1 else 'model/001_K/K_bc.csr'
    py = sys.argv[2] if len(sys.argv) > 2 else \
        'sample/001_3DFEM/Quad4_structual/K_python_bc.npz'

    Kf = load_any(fistr)
    Kp = load_any(py)
    print(f'FrontISTR K: {Kf.shape}, nnz {Kf.nnz}   ({fistr})')
    print(f'Python    K: {Kp.shape}, nnz {Kp.nnz}   ({py})')
    assert Kf.shape == Kp.shape, 'shape mismatch'

    n = Kf.shape[0]
    perm = align_perm(n)
    Kp_al = Kp[perm][:, perm]

    nf = frob(Kf)
    D_raw = Kf - Kp
    D_al = Kf - Kp_al
    print()
    print(f'[整列なし] ||Kf-Kp||/||Kf|| = {frob(D_raw)/nf:.4e}')
    print(f'[x,y整列 ] ||Kf-Kp||/||Kf|| = {frob(D_al)/nf:.4e}   '
          f'max|diff|={abs(D_al).max():.3e}  (max|K|={abs(Kf).max():.3e})')

    rel = frob(D_al) / nf
    if rel < 1e-5:
        print('\n=> 一致（差はPython側 float32 精度）。FrontISTRとPythonのKは同一。')
    else:
        print('\n=> 差が大きい。並び順や条件を再確認。')


if __name__ == '__main__':
    main()
