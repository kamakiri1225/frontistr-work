#!/usr/bin/env python3
"""
read_fistr_matrix.py — FrontISTR の行列ダンプ(!SOLVER DUMPTYPE=...)を scipy 疎行列に読む。

対応形式:
  .csr : '%%CSR matrix real general'  （index(0:nrow) / item(1:nnz) / value(1:nnz)）
  .mm  : '%%MatrixMarket matrix coordinate real general'
  .rhs : 右辺ベクトル（1値/行）

使い方（モジュール）:
  from read_fistr_matrix import read_csr, read_rhs
  K = read_csr('dump_matrix_1_0.csr')     # scipy.sparse.csr_matrix
  b = read_rhs('dump_matrix_1_0.rhs')     # numpy 1D
"""
import sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.io import mmread


def _data_lines(path):
    """% で始まるコメントと空行を除いた数値行を順に返す。"""
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('%'):
                continue
            yield s


def read_csr(path):
    it = _data_lines(path)
    nrow, ncol, nnz = (int(x) for x in next(it).split())
    indptr = np.empty(nrow + 1, dtype=np.int64)
    for i in range(nrow + 1):
        indptr[i] = int(next(it))
    indices = np.empty(nnz, dtype=np.int64)
    for i in range(nnz):
        indices[i] = int(next(it)) - 1     # 1-based -> 0-based
    data = np.empty(nnz, dtype=float)
    for i in range(nnz):
        data[i] = float(next(it))
    if indptr[-1] != nnz:
        raise ValueError(f"indptr[-1]={indptr[-1]} != nnz={nnz}")
    return csr_matrix((data, indices, indptr), shape=(nrow, ncol))


def read_mm(path):
    return mmread(path).tocsr()


def read_rhs(path):
    return np.array([float(s) for s in _data_lines(path)])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'dump_matrix_1_0.csr'
    if path.endswith('.mm'):
        K = read_mm(path)
    else:
        K = read_csr(path)
    print(f'file: {path}')
    print(f'shape: {K.shape}, nnz: {K.nnz}')
    # 対称性チェック
    asym = abs(K - K.T)
    amax = asym.max() if asym.nnz else 0.0
    kmax = abs(K).max()
    print(f'max|K|: {kmax:.6e}')
    print(f'max|K - K^T|: {amax:.6e}  (rel {amax/kmax:.2e})')
    # 対角の様子
    d = K.diagonal()
    print(f'diag: min {d.min():.4e}, max {d.max():.4e}, '
          f'#(diag==1): {(d == 1.0).sum()}  (拘束されたDOFの目安)')


if __name__ == '__main__':
    main()
