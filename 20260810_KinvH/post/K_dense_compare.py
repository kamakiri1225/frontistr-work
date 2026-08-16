#!/usr/bin/env python3
"""
K_dense_compare.py — FrontISTR と Python の K を「行×列の表(密行列CSV)」にして比較する。

- Python K は自由度並びが違う(節点内で x,y 入替)ので FrontISTR 並び(x,y,z) に整列。
- 行/列ラベルは「<節点番号><成分>」 例: 1x,1y,1z,2x,...
- 出力(model/001_K/ に):
    K_fistr_table.csv           FrontISTR K（BC適用後, ラベル付き表）
    K_python_table.csv          Python K（FrontISTR並びに整列, ラベル付き表）
    K_diff_table.csv            差 (FrontISTR - Python)
- 画面には左上の小ブロックを両者並べて表示。

使い方:
  python3 K_dense_compare.py
  python3 K_dense_compare.py --block 3 6   # 節点3..6の block を画面表示
"""
import os
import sys
import numpy as np
import pandas as pd
from scipy import sparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from read_fistr_matrix import read_csr

FISTR = os.path.join(ROOT, 'model/001_K/K_bc.csr')
PY = os.path.join(ROOT, 'sample/001_3DFEM/Quad4_structual/K_python_bc.npz')
OUT = os.path.join(ROOT, 'model/001_K')


def labels(n):
    comp = ['x', 'y', 'z']
    return [f'{i // 3 + 1}{comp[i % 3]}' for i in range(n)]


def align_python(Kp):
    """Python並び -> FrontISTR並び(x,y,z)。節点内で x,y を入替。"""
    n = Kp.shape[0]
    perm = np.arange(n)
    for g in range(n // 3):
        perm[3 * g] = 3 * g + 1
        perm[3 * g + 1] = 3 * g
    return Kp[perm][:, perm]


def main():
    Kf = read_csr(FISTR).tocsr().astype(float).toarray()
    Kp = align_python(sparse.load_npz(PY).tocsr().astype(float)).toarray()
    n = Kf.shape[0]
    lab = labels(n)

    df_f = pd.DataFrame(Kf, index=lab, columns=lab)
    df_p = pd.DataFrame(Kp, index=lab, columns=lab)
    df_d = pd.DataFrame(Kf - Kp, index=lab, columns=lab)

    df_f.to_csv(os.path.join(OUT, 'K_fistr_table.csv'))
    df_p.to_csv(os.path.join(OUT, 'K_python_table.csv'))
    df_d.to_csv(os.path.join(OUT, 'K_diff_table.csv'))
    print('wrote: K_fistr_table.csv / K_python_table.csv / K_diff_table.csv  (in model/001_K/)')
    print(f'shape: {n} x {n}  (行/列ラベル = 節点番号+成分)')

    # 一致度
    nf = np.linalg.norm(Kf); nd = np.linalg.norm(Kf - Kp)
    print(f'\n||Kf-Kp||/||Kf|| = {nd/nf:.3e}   max|diff| = {np.abs(Kf-Kp).max():.3e}')

    # 画面プレビュー（デフォルト 節点2..4 の 9x9）
    b0, b1 = 2, 4
    if '--block' in sys.argv:
        k = sys.argv.index('--block'); b0, b1 = int(sys.argv[k+1]), int(sys.argv[k+2])
    s, e = (b0-1)*3, b1*3
    pd.set_option('display.width', 200, 'display.max_columns', 30,
                  'display.float_format', lambda v: f'{v:11.3e}')
    print(f'\n===== FrontISTR  K[節点{b0}..{b1}] =====')
    print(df_f.iloc[s:e, s:e])
    print(f'\n===== Python(整列) K[節点{b0}..{b1}] =====')
    print(df_p.iloc[s:e, s:e])
    print(f'\n===== 差 (FrontISTR - Python) =====')
    print(df_d.iloc[s:e, s:e])


if __name__ == '__main__':
    main()
