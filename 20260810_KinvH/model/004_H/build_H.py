#!/usr/bin/env python3
"""
build_H.py — FrontISTR の既存機能だけで 温度荷重変換行列 H を組み立てる（ソース改造なし）。

原理:
  H の第 j 列 = 「節点 j に単位温度(1.0)を与えたときの温度荷重ベクトル f」
  FrontISTR は温度荷重を RHS に加算し、!SOLVER の DUMPTYPE に付随して RHS が
  dump_matrix_1_0.rhs に出力される（DUMPEXIT=YES で解かずに即ダンプ）。
  => 全節点 j に対して 1回ずつ実行し、RHS を集めれば H (n_dof × n_node) が得られる。

条件:
  ・荷重なし / 境界条件なし（生の H を得る）
  ・材料に熱膨張 !EXPANSION_COEFF が必要
  ・基準温度=0, 初期温度=0（既定）なので f = H·e_j がそのまま出る

出力:
  H_fistr.npz  … scipy 疎行列 (n_dof × n_node)
  H_fistr.mtx  … MatrixMarket
"""
import argparse
import os
import subprocess
import sys
import numpy as np
from scipy import sparse
from scipy.io import mmwrite

FISTR = os.path.expanduser('~/local/frontistr/bin/fistr1')
HERE = os.path.dirname(os.path.abspath(__file__))
CNT = os.path.join(HERE, 'FistrModel.cnt')
RHS = os.path.join(HERE, 'dump_matrix_1_0.rhs')
MM = os.path.join(HERE, 'dump_matrix_1_0.mm')
PARTIAL = os.path.join(HERE, 'H_fistr.partial.npz')
PROGRESS = os.path.join(HERE, 'H_fistr.progress')

CNT_TEMPLATE = """!VERSION
 3
!SOLUTION,TYPE=STATIC
!TEMPERATURE
 {node}, 1.0
!SOLVER,METHOD=DIRECT,ITERLOG=NO,TIMELOG=NO, DUMPTYPE = MM, DUMPEXIT = YES
 10000, 1
 1.0e-8, 1.0, 0.0
!MATERIAL, NAME=FC300
!ELASTIC, TYPE=ISOTROPIC
 130000.0, 0.27
!DENSITY
 7.4e-9
!EXPANSION_COEFF
 1.2e-5
!END
"""


def count_nodes(mesh):
    """.msh の !NODE 〜 次の ! までの行数で節点数を数える。"""
    n = 0
    in_node = False
    for line in open(mesh, encoding='utf-8', errors='ignore'):
        s = line.strip()
        if s.startswith('!NODE'):
            in_node = True
            continue
        if in_node:
            if s.startswith('!'):
                break
            if s:
                n += 1
    return n


def read_rhs(path):
    b = []
    for line in open(path, encoding='utf-8', errors='ignore'):
        s = line.strip()
        if s and not s.startswith('%'):
            b.append(float(s))
    return np.array(b)


def save_checkpoint(rows, cols, vals, shape, completed):
    """中断後に --resume で続けられるよう、組み立て済み列を保存する。"""
    H = sparse.csr_matrix((vals, (rows, cols)), shape=shape)
    sparse.save_npz(PARTIAL, H)
    with open(PROGRESS, 'w', encoding='ascii') as f:
        f.write(f'{completed}\n')


def load_checkpoint(shape):
    if not (os.path.exists(PARTIAL) and os.path.exists(PROGRESS)):
        return [], [], [], 0
    H = sparse.load_npz(PARTIAL)
    if H.shape != shape:
        raise ValueError(f'checkpoint shape {H.shape} != expected {shape}')
    completed = int(open(PROGRESS, encoding='ascii').read().strip())
    coo = H.tocoo()
    return coo.row.tolist(), coo.col.tolist(), coo.data.tolist(), completed


def parse_args():
    p = argparse.ArgumentParser(description='FrontISTR の RHS から H を組み立てる')
    p.add_argument('--resume', action='store_true', help='保存済みチェックポイントから再開')
    p.add_argument('--checkpoint-every', type=int, default=25,
                   help='チェックポイントを保存する列間隔 (default: 25)')
    return p.parse_args()


def main():
    args = parse_args()
    nnode = count_nodes(os.path.join(HERE, 'FistrModel.msh'))
    ndof = 3 * nnode
    print(f'nodes={nnode}, n_dof={ndof}  -> H は {ndof} x {nnode}')

    shape = (ndof, nnode)
    if args.resume:
        rows, cols, vals, completed = load_checkpoint(shape)
        print(f'checkpoint: {completed}/{nnode} 列から再開')
    else:
        rows, cols, vals, completed = [], [], [], 0

    original_cnt = open(CNT, 'rb').read() if os.path.exists(CNT) else None
    try:
        for j in range(completed + 1, nnode + 1):
            with open(CNT, 'w', encoding='utf-8') as f:
                f.write(CNT_TEMPLATE.format(node=j))
            for path in (RHS, MM):
                if os.path.exists(path):
                    os.remove(path)
            result = subprocess.run(
                [FISTR], cwd=HERE, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f'node {j}: fistr1 failed ({result.returncode})\n{result.stderr}')
            if not os.path.exists(RHS):
                raise RuntimeError(f'node {j}: RHS が出力されませんでした')
            b = read_rhs(RHS)                       # H の第 j 列
            if b.size != ndof:
                raise RuntimeError(
                    f'node {j}: RHS length {b.size} != expected {ndof}')
            nz = np.nonzero(np.abs(b) > 1e-30)[0]
            rows.extend(nz.tolist())
            cols.extend([j - 1] * len(nz))
            vals.extend(b[nz].tolist())
            # Kダンプは毎回同じなので捨てる。
            for path in (RHS, MM):
                if os.path.exists(path):
                    os.remove(path)
            if j % args.checkpoint_every == 0 or j == nnode:
                save_checkpoint(rows, cols, vals, shape, j)
                print(f'  ... {j}/{nnode} 完了 (累積非ゼロ {len(vals)})', flush=True)
    finally:
        if original_cnt is not None:
            with open(CNT, 'wb') as f:
                f.write(original_cnt)

    H = sparse.csr_matrix((vals, (rows, cols)), shape=shape)
    sparse.save_npz(os.path.join(HERE, 'H_fistr.npz'), H)
    mmwrite(os.path.join(HERE, 'H_fistr.mtx'), H)
    for path in (PARTIAL, PROGRESS):
        if os.path.exists(path):
            os.remove(path)
    print(f'\nH: {H.shape}, nnz {H.nnz}')
    print(f'saved: H_fistr.npz / H_fistr.mtx')


if __name__ == '__main__':
    main()
