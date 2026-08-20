#!/usr/bin/env python3
"""
ccx_wdiff.py — CalculiX(改造版)が出力した K.mtx / H.mtx / nactdof.txt から、
   感度行列 W = K^-1 H の測定点差 Wdiff(=Point_A行 - Point_O行) をアジョイント法で求め、
   ParaView用VTK と数値テキストに書き出す。K・H はソルバ(CalculiX)側で出力済み。

CalculiX は固定(SPC)自由度を系から除くので、K・H は「アクティブ自由度(方程式)」番号で
出ている。nactdof.txt が (節点, 方向) -> 方程式番号 の対応。Point_O(節点103)は固定なので
その変位感度は0（Wdiff = W[Point_A] となる）。

使い方（calculix/model/011_Tji_ccx/ で K.mtx 等を出したあと）:
  python3 ../../post/ccx_wdiff.py --workdir . --inp Quad4_FEM_Tji.inp
"""
import argparse, os
import numpy as np
from scipy.io import mmread
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import factorized

POINT_A, POINT_O = 19, 103


def parse_inp(path):
    nodes, elems = {}, []
    mode = None
    for line in open(path):
        s = line.strip()
        if not s:
            continue
        if s.startswith('*'):
            u = s.upper()
            if u.startswith('*NODE'):
                mode = 'n'
            elif u.startswith('*ELEMENT') and 'C3D4' in u:
                mode = 'e'
            else:
                mode = None
            continue
        p = [x.strip() for x in s.split(',') if x.strip() != '']
        if mode == 'n':
            nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == 'e':
            elems.append((int(p[0]), [int(x) for x in p[1:5]]))
    return nodes, elems


def read_nactdof(path):
    d = {}
    for line in open(path):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        node, dr, eq = (int(x) for x in s.split())
        d[(node, dr)] = eq
    return d


def write_vtk(path, nodes, elems, wdiff):
    nid = sorted(nodes)
    idx = {n: i for i, n in enumerate(nid)}
    with open(path, 'w') as f:
        f.write('# vtk DataFile Version 2.0\n')
        f.write('CalculiX sensitivity Wdiff (Point_A - Point_O per unit nodal temperature)\n')
        f.write('ASCII\nDATASET UNSTRUCTURED_GRID\n')
        f.write(f'POINTS {len(nid)} double\n')
        for n in nid:
            x, y, z = nodes[n]
            f.write(f'{x} {y} {z}\n')
        f.write(f'CELLS {len(elems)} {len(elems)*5}\n')
        for _, c in elems:
            f.write('4 ' + ' '.join(str(idx[v]) for v in c) + '\n')
        f.write(f'CELL_TYPES {len(elems)}\n')
        for _ in elems:
            f.write('10\n')
        f.write(f'POINT_DATA {len(nid)}\nVECTORS Sensitivity double\n')
        for n in nid:
            w = wdiff[:, n - 1]
            f.write(f'{w[0]} {w[1]} {w[2]}\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workdir', default='.')
    ap.add_argument('--inp', default='Quad4_FEM_Tji.inp')
    args = ap.parse_args()
    wd = args.workdir

    K = csc_matrix(mmread(os.path.join(wd, 'K.mtx')))   # symmetric -> full
    H = mmread(os.path.join(wd, 'H.mtx')).tocsc()        # (neq x nnode) active-DOF rows
    nactdof = read_nactdof(os.path.join(wd, 'nactdof.txt'))
    nodes, elems = parse_inp(os.path.join(wd, args.inp))
    nnode = len(nodes)
    neq = K.shape[0]
    print(f'K {K.shape}, H {H.shape}, nodes {nnode}, active DOFs {neq}')

    # Point_A active equations (x,y,z). Point_O(103) is fixed -> contributes 0.
    eqA = [nactdof[(POINT_A, d)] for d in (1, 2, 3)]
    eqO = [nactdof[(POINT_O, d)] for d in (1, 2, 3)]
    print('Point_A eqs:', eqA, ' Point_O eqs:', eqO, '(<=0 means fixed)')

    solve = factorized(K)
    Wdiff = np.zeros((3, nnode))
    for c in range(3):
        row = np.zeros(3)
        for name, eqs, sign in [('A', eqA, +1.0), ('O', eqO, -1.0)]:
            eq = eqs[c]
            if eq > 0:                       # free DOF: adjoint solve
                e = np.zeros(neq)
                e[eq - 1] = 1.0
                z = solve(e)
                Wdiff[c, :] += sign * (H.T @ z)
            # eq<=0 (fixed): displacement sensitivity is 0 -> add nothing
    # save
    with open(os.path.join(wd, 'Wdiff_ccx.txt'), 'w') as f:
        f.write('# node_id  Wdiff_x  Wdiff_y  Wdiff_z\n')
        for n in range(1, nnode + 1):
            f.write(f'{n} {Wdiff[0,n-1]:.12e} {Wdiff[1,n-1]:.12e} {Wdiff[2,n-1]:.12e}\n')
    write_vtk(os.path.join(wd, 'sensitivity_Wdiff_ccx.vtk'), nodes, elems, Wdiff)
    print('wrote Wdiff_ccx.txt and sensitivity_Wdiff_ccx.vtk')

    # optional: compare with FrontISTR DUMPW result (same model) if present
    ref = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '../../frontistr/model/011_Tji_DUMPW/Wdiff_fistr.txt')
    if os.path.exists(ref):
        rf = {}
        for line in open(ref):
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            p = s.split()
            rf[int(p[0])] = np.array(list(map(float, p[1:4])))
        Wref = np.zeros((3, nnode))
        for n in range(1, nnode + 1):
            if n in rf:
                Wref[:, n - 1] = rf[n]
        rel = np.linalg.norm(Wdiff - Wref) / np.linalg.norm(Wref)
        print(f'vs FrontISTR DUMPW (011): relative diff = {rel:.3e}')


if __name__ == '__main__':
    main()
