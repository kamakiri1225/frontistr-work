#!/usr/bin/env python3
"""
csr_to_mtx_csv.py — FrontISTR の行列ダンプ(.csr/.mm) や .npz を
  - MatrixMarket (.mtx)
  - COO CSV (row,col,value の三つ組。1始まり、全非ゼロ)
  - 必要なら 密行列CSV (--dense)
に変換する。

使い方:
  python3 csr_to_mtx_csv.py K_bc.csr             # K_bc.mtx と K_bc.csv を作る
  python3 csr_to_mtx_csv.py K_bc.csr --dense     # 密行列CSV(K_bc_dense.csv)も作る（大きい）
"""
import sys
import os
import numpy as np
from scipy import sparse
from scipy.io import mmwrite

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_fistr_matrix import read_csr, read_mm


def load_any(path):
    if path.endswith('.npz'):
        return sparse.load_npz(path).tocsr().astype(float)
    if path.endswith('.mm'):
        return read_mm(path).astype(float)
    return read_csr(path).tocsr().astype(float)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    dense = '--dense' in sys.argv
    base = os.path.splitext(path)[0]

    K = load_any(path).tocoo()
    print(f'loaded {path}: shape {K.shape}, nnz {K.nnz}')

    # 1) MatrixMarket
    mtx = base + '.mtx'
    mmwrite(mtx, K.tocsr(), symmetry='general')
    print(f'wrote {mtx}  (MatrixMarket)')

    # 2) COO CSV （row,col,value / 1始まり / 行→列でソート）
    csv = base + '.csv'
    order = np.lexsort((K.col, K.row))
    r = K.row[order] + 1
    c = K.col[order] + 1
    v = K.data[order]
    with open(csv, 'w', encoding='utf-8') as f:
        f.write('row,col,value\n')
        for i in range(len(v)):
            f.write(f'{r[i]},{c[i]},{v[i]:.12e}\n')
    print(f'wrote {csv}  (COO: row,col,value, {len(v)} 非ゼロ)')

    # 3) 密行列CSV（オプション）
    if dense:
        dcsv = base + '_dense.csv'
        A = K.toarray()
        np.savetxt(dcsv, A, delimiter=',', fmt='%.10e')
        print(f'wrote {dcsv}  (dense {A.shape[0]}x{A.shape[1]})')


if __name__ == '__main__':
    main()
