#!/usr/bin/env python3
"""
build_H_tji.py — model/008_Tji_compare の570節点メッシュに対して、
                 標準機能だけでH（生、境界条件なし）をFrontISTRから組み立てる。
                 model/004_H/build_H.py と同じ手法（節点ごとに単位温度を与えて
                 570回実行しRHSを集める）を、Tjiモデル向けに焼き直したもの。

出力:
  model/008_Tji_compare/H_fistr_tji.npz
  model/008_Tji_compare/H_fistr_tji.mtx
"""
import os
import subprocess
import sys
import numpy as np
from scipy import sparse
from scipy.io import mmwrite

FISTR = os.path.expanduser('~/local/frontistr/bin/fistr1')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, 'model', '008_Tji_compare')
CNT = os.path.join(WORK, 'FistrModel.cnt')
RHS = os.path.join(WORK, 'dump_matrix_1_0.rhs')
MM = os.path.join(WORK, 'dump_matrix_1_0.mm')

YOUNG = 130000000.0
POISSON = 0.27
DENSITY = 7.4e-06
CTE = 1.2e-05

CNT_TEMPLATE = f"""!VERSION
 3
!SOLUTION,TYPE=STATIC
!TEMPERATURE
 {{node}}, 1.0
!SOLVER,METHOD=DIRECT,ITERLOG=NO,TIMELOG=NO, DUMPTYPE = MM, DUMPEXIT = YES
 10000, 1
 1.0e-8, 1.0, 0.0
!MATERIAL, NAME=FC300
!ELASTIC, TYPE=ISOTROPIC
 {YOUNG}, {POISSON}
!DENSITY
 {DENSITY}
!EXPANSION_COEFF
 {CTE}
!END
"""


def count_nodes(mesh):
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


def main():
    nnode = count_nodes(os.path.join(WORK, 'FistrModel.msh'))
    ndof = 3 * nnode
    print(f'nodes={nnode}, n_dof={ndof} -> H は {ndof} x {nnode}')

    rows, cols, vals = [], [], []
    for j in range(1, nnode + 1):
        with open(CNT, 'w', encoding='utf-8') as f:
            f.write(CNT_TEMPLATE.format(node=j))
        for path in (RHS, MM):
            if os.path.exists(path):
                os.remove(path)
        result = subprocess.run([FISTR], cwd=WORK, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f'node {j}: fistr1 failed\n{result.stderr}')
        if not os.path.exists(RHS):
            raise RuntimeError(f'node {j}: RHS not produced')
        b = read_rhs(RHS)
        if b.size != ndof:
            raise RuntimeError(f'node {j}: RHS length {b.size} != {ndof}')
        nz = np.nonzero(np.abs(b) > 1e-30)[0]
        rows.extend(nz.tolist())
        cols.extend([j - 1] * len(nz))
        vals.extend(b[nz].tolist())
        for path in (RHS, MM):
            if os.path.exists(path):
                os.remove(path)
        if j % 50 == 0 or j == nnode:
            print(f'  ... {j}/{nnode}', flush=True)

    H = sparse.csr_matrix((vals, (rows, cols)), shape=(ndof, nnode))
    sparse.save_npz(os.path.join(WORK, 'H_fistr_tji.npz'), H)
    mmwrite(os.path.join(WORK, 'H_fistr_tji.mtx'), H)
    print(f'H: {H.shape}, nnz {H.nnz}')
    print('saved H_fistr_tji.npz / H_fistr_tji.mtx')


if __name__ == '__main__':
    main()
