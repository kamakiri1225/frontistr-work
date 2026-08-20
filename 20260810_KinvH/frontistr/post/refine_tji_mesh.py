#!/usr/bin/env python3
"""
refine_tji_mesh.py — sample/002_thermalSensitive/Inp_Data/Quad4_FEM_Tji.inp
（570節点・1699要素のC3D4四面体メッシュ、元ファイルは一切変更しない）を、
各四面体を8個の子四面体に分割する一様細分割（各辺の中点を新しい節点として追加する
標準的な"red refinement"）でリファインし、より細かいメッシュを作る。
`--levels N` でN回繰り返し適用する（N=2なら8×8=64倍の要素数）。

節点数・要素数がともに増えるため、Python実装とFrontISTR(DUMPH改造版)の比較を
より大きな問題サイズで行える。Fixed節点・Point_A・Point_Oは元の節点番号のまま
（リファインで座標も番号も変わらない）なので、そのまま引き継げる。

出力:
  model/010_Tji_fine_H_direct/FistrModel.msh   （FrontISTR形式）
  model/010_Tji_fine_H_direct/hecmw_ctrl.dat
  model/010_Tji_fine_H_direct/mesh_fine.npz    （Python側の計算スクリプトが読む中間形式）
  model/010_Tji_fine_H_direct/Quad4_FEM_Tji_fine.inp （Abaqus形式、ThermoSenseAnalyzer_00.py用）
"""
import argparse
import os
import sys
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from inp_to_fistr_msh import parse_inp, INP, write_ctrl  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'model', '010_Tji_fine_H_direct')


def refine(model):
    """各C3D4要素を8個の子要素に一様分割する(red refinement)。"""
    nodes = dict(model['nodes'])
    elements = model['elements']
    next_id = max(nodes) + 1

    edge_mid = {}  # (nid_a, nid_b) sorted -> 新しい節点id

    def midpoint(a, b):
        nonlocal next_id
        key = (a, b) if a < b else (b, a)
        if key in edge_mid:
            return edge_mid[key]
        xa, ya, za = nodes[a]
        xb, yb, zb = nodes[b]
        nodes[next_id] = ((xa + xb) / 2, (ya + yb) / 2, (za + zb) / 2)
        edge_mid[key] = next_id
        next_id += 1
        return edge_mid[key]

    new_elements = {}
    eid = 1
    for old_eid in sorted(elements):
        v0, v1, v2, v3 = elements[old_eid]
        m01 = midpoint(v0, v1)
        m02 = midpoint(v0, v2)
        m03 = midpoint(v0, v3)
        m12 = midpoint(v1, v2)
        m13 = midpoint(v1, v3)
        m23 = midpoint(v2, v3)

        # 4つの角(コーナー)四面体 + 中心の八面体を対角線 m01-m23 で4分割 = 計8個
        children = [
            (v0, m01, m02, m03),
            (v1, m01, m12, m13),
            (v2, m02, m12, m23),
            (v3, m03, m13, m23),
            (m01, m02, m03, m23),
            (m01, m02, m12, m23),
            (m01, m03, m13, m23),
            (m01, m12, m13, m23),
        ]
        for c in children:
            new_elements[eid] = list(c)
            eid += 1

    return {
        'nodes': nodes, 'elements': new_elements,
        'fixed_nodes': model['fixed_nodes'],
        'point_a': model['point_a'], 'point_o': model['point_o'],
        'young': model['young'], 'poisson': model['poisson'],
        'density': model['density'], 'cte': model['cte'],
    }


def write_inp(model, path):
    """ThermoSenseAnalyzer_00.py（Data_import.data_import_01）が読めるAbaqus形式で書き出す。
    材料定数はData_import側では使われない（ThermoSenseAnalyzer_00.py側でハードコード）ため、
    参考情報として元のQuad4_FEM_Tji.inpと同じ形式で書いておくだけでよい。"""
    nodes = model['nodes']
    elements = model['elements']
    with open(path, 'w', encoding='ascii') as f:
        f.write('*NODE\n')
        for nid in sorted(nodes):
            x, y, z = nodes[nid]
            f.write(f'{nid}, {x!r}, {y!r}, {z!r}\n')
        f.write('*NSET, NSET="Fixed (26)-1"\n')
        fixed = model['fixed_nodes']
        for k in range(0, len(fixed), 8):
            f.write(', '.join(str(v) for v in fixed[k:k + 8]) + '\n')
        f.write('*NSET, NSET="Point_A (29)-1"\n')
        f.write(f'{model["point_a"]}\n')
        f.write('*NSET, NSET="Point_O (32)-1"\n')
        f.write(f'{model["point_o"]}\n')
        f.write('*ELEMENT, TYPE=C3D4\n')
        for eid in sorted(elements):
            n1, n2, n3, n4 = elements[eid]
            f.write(f'{eid}, {n1}, {n2}, {n3}, {n4}\n')
        f.write('*ELSET, ELSET="Solid Section1-1"\n')
        elem_ids = sorted(elements)
        for k in range(0, len(elem_ids), 8):
            f.write(', '.join(str(v) for v in elem_ids[k:k + 8]) + '\n')
        f.write('*MATERIAL, NAME="FC300 --- SHARED"\n')
        f.write('*ELASTIC, TYPE=ISOTROPIC\n')
        f.write(f'{model["young"]!r}, {model["poisson"]!r}\n')
        f.write('*DENSITY\n')
        f.write(f'{model["density"]!r}\n')
        f.write('*EXPANSION, TYPE=ISOTROPIC, ZERO=0.\n')
        f.write(f'{model["cte"]!r}\n')
        f.write('*SOLID SECTION, MATERIAL="FC300 --- SHARED", ELSET="Solid Section1-1"\n')
        f.write('*END\n')


def write_msh(model, path):
    nodes = model['nodes']
    elements = model['elements']
    with open(path, 'w', encoding='ascii') as f:
        f.write('!HEADER\n 3\n')
        f.write('!NODE\n')
        for nid in sorted(nodes):
            x, y, z = nodes[nid]
            f.write(f' {nid}, {x!r}, {y!r}, {z!r}\n')
        f.write('!ELEMENT, TYPE=341, EGRP=body\n')
        for eid in sorted(elements):
            n1, n2, n3, n4 = elements[eid]
            f.write(f' {eid}, {n1}, {n2}, {n3}, {n4}\n')
        f.write('!NGROUP, NGRP=fix\n')
        fixed = model['fixed_nodes']
        for k in range(0, len(fixed), 8):
            f.write(' ' + ', '.join(str(v) for v in fixed[k:k + 8]) + '\n')
        f.write('!MATERIAL, NAME=FC300, ITEM=2\n')
        f.write('!ITEM=1, SUBITEM=2\n')
        f.write(f' {model["young"]!r}, {model["poisson"]!r}\n')
        f.write('!ITEM=2, SUBITEM=1\n')
        f.write(f' {model["density"]!r}\n')
        f.write('!SECTION, TYPE=SOLID, EGRP=body, MATERIAL=FC300\n')
        f.write('!END\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--levels', type=int, default=1, help='refine()を繰り返す回数（既定1）')
    args = ap.parse_args()

    t0 = time.time()
    fine = parse_inp(INP)
    base_nodes, base_elems = len(fine['nodes']), len(fine['elements'])
    for lv in range(args.levels):
        fine = refine(fine)
        print(f'  level {lv + 1}: {len(fine["nodes"])}節点 {len(fine["elements"])}要素')
    t1 = time.time()

    n_node = len(fine['nodes'])
    n_elem = len(fine['elements'])
    print(f'元メッシュ: {base_nodes}節点 {base_elems}要素')
    print(f'リファイン後({args.levels}段): {n_node}節点 {n_elem}要素  ({t1 - t0:.3f} s)')
    print(f'fixed={len(fine["fixed_nodes"])}, point_a={fine["point_a"]}, point_o={fine["point_o"]}')

    os.makedirs(OUT_DIR, exist_ok=True)
    write_msh(fine, os.path.join(OUT_DIR, 'FistrModel.msh'))
    write_ctrl(os.path.join(OUT_DIR, 'hecmw_ctrl.dat'))
    write_inp(fine, os.path.join(OUT_DIR, 'Quad4_FEM_Tji_fine.inp'))

    node_ids = sorted(fine['nodes'])
    elem_ids = sorted(fine['elements'])
    coords = np.array([fine['nodes'][n] for n in node_ids])
    conn = np.array([fine['elements'][e] for e in elem_ids])  # 節点番号(1-based)のまま
    np.savez(
        os.path.join(OUT_DIR, 'mesh_fine.npz'),
        node_ids=np.array(node_ids), coords=coords,
        elem_ids=np.array(elem_ids), conn=conn,
        fixed_nodes=np.array(fine['fixed_nodes']),
        point_a=fine['point_a'], point_o=fine['point_o'],
        young=fine['young'], poisson=fine['poisson'],
        density=fine['density'], cte=fine['cte'],
    )
    print(f'wrote {OUT_DIR}/FistrModel.msh, hecmw_ctrl.dat, mesh_fine.npz, Quad4_FEM_Tji_fine.inp')


if __name__ == '__main__':
    main()
