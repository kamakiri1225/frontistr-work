#!/usr/bin/env python3
"""
compare_H.py — 改造版FrontISTR(DUMPH=YES)が直接出力したHと、
               標準機能だけで425回実行して組み立てたHを比較する。

  H_direct : model/005_H_direct/H_matrix.mtx （DUMPHで1回の実行から直接出力）
  H_brute  : model/004_H/H_fistr.mtx         （425回実行してRHSを列ごとに集めて構成）

両者が一致すれば、DUMPHパッチが正しく温度荷重行列Hを出力できていることの根拠になる。

使い方:
  python3 compare_H.py
  python3 compare_H.py <H_direct.mtx> <H_brute.mtx>
"""
import sys
import os
import numpy as np
from scipy.io import mmread
from scipy.sparse import issparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    direct = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(ROOT, 'model', '005_H_direct', 'H_matrix.mtx')
    brute = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(ROOT, 'model', '004_H', 'H_fistr.mtx')

    H_direct = mmread(direct)
    H_brute = mmread(brute)

    lines = []
    lines.append(f'H_direct (DUMPH直接出力): {H_direct.shape}  nnz={H_direct.nnz if issparse(H_direct) else "-"}  ({direct})')
    lines.append(f'H_brute  (425回ブルートフォース): {H_brute.shape}  nnz={H_brute.nnz if issparse(H_brute) else "-"}  ({brute})')

    if H_direct.shape != H_brute.shape:
        lines.append('=> shape不一致。比較不可。')
        print('\n'.join(lines))
        return 1

    Hd = H_direct.toarray() if issparse(H_direct) else np.asarray(H_direct)
    Hb = H_brute.toarray() if issparse(H_brute) else np.asarray(H_brute)
    diff = Hd - Hb
    max_abs = float(np.abs(diff).max())
    rel = float(np.linalg.norm(diff) / np.linalg.norm(Hb))

    lines.append('')
    lines.append(f'最大絶対差 max|H_direct - H_brute| = {max_abs:.6e}')
    lines.append(f'相対差(Frobenius) ||H_direct - H_brute|| / ||H_brute|| = {rel:.6e}')
    lines.append('')
    if rel < 1e-8:
        lines.append('=> 一致（数値誤差レベル）。DUMPHの直接出力は標準機能ベースのHと同じ。')
    else:
        lines.append('=> 差が大きい。DUMPH実装を再確認。')

    out = '\n'.join(lines)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
