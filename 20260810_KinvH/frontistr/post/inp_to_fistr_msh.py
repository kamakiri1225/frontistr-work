#!/usr/bin/env python3
"""
inp_to_fistr_msh.py — Abaqus形式 *.inp（C3D4のみ）をFrontISTRの!MESH形式に変換する。

sample/002_thermalSensitive/Inp_Data/Quad4_FEM_Tji.inp を対象に、
model/008_Tji_compare/FistrModel.msh と hecmw_ctrl.dat を作る。
これはPython側(ThermoSenseAnalyzer_00.py)とFrontISTR側で
同一メッシュ・同一材料定数のHとWを比較するための変換である。

対応:
  *NODE                        -> !NODE
  *ELEMENT, TYPE=C3D4          -> !ELEMENT, TYPE=341
  *NSET, NSET="Fixed (26)-1"   -> !NGROUP, NGRP=fix   （全自由度固定として使う）
  *ELASTIC / *DENSITY / *EXPANSION -> !MATERIAL
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INP = os.path.join(ROOT, 'sample', '002_thermalSensitive', 'Inp_Data', 'Quad4_FEM_Tji.inp')
OUT_DIR = os.path.join(ROOT, 'model', '008_Tji_compare')
MSH = os.path.join(OUT_DIR, 'FistrModel.msh')
CTRL = os.path.join(OUT_DIR, 'hecmw_ctrl.dat')


def parse_inp(path):
    nodes = {}
    elements = {}
    fixed_nodes = []
    point_a = None
    point_o = None
    young = poisson = density = cte = None

    section = None
    nset_name = None
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        s = raw.strip()
        if s.startswith('*'):
            head = s.upper()
            if head.startswith('*NODE'):
                section = 'NODE'
            elif head.startswith('*ELEMENT') and 'C3D4' in head:
                section = 'ELEMENT'
            elif head.startswith('*NSET'):
                section = 'NSET'
                m = re.search(r'NSET="([^"]+)"', s)
                nset_name = m.group(1) if m else ''
            elif head.startswith('*ELASTIC'):
                section = 'ELASTIC'
            elif head.startswith('*DENSITY'):
                section = 'DENSITY'
            elif head.startswith('*EXPANSION'):
                section = 'EXPANSION'
            else:
                section = None
            i += 1
            continue

        if section == 'NODE' and s:
            p = s.split(',')
            nid = int(p[0])
            x, y, z = float(p[1]), float(p[2]), float(p[3])
            nodes[nid] = (x, y, z)
        elif section == 'ELEMENT' and s:
            p = s.split(',')
            eid = int(p[0])
            conn = [int(v) for v in p[1:5]]
            elements[eid] = conn
        elif section == 'NSET' and s:
            ids = [int(v) for v in s.replace(',', ' ').split()]
            if nset_name.startswith('Fixed'):
                fixed_nodes.extend(ids)
            elif nset_name.startswith('Point_A'):
                point_a = ids[0]
            elif nset_name.startswith('Point_O'):
                point_o = ids[0]
        elif section == 'ELASTIC' and s:
            p = s.split(',')
            young, poisson = float(p[0]), float(p[1])
            section = None
        elif section == 'DENSITY' and s:
            density = float(s.split(',')[0])
            section = None
        elif section == 'EXPANSION' and s:
            cte = float(s.split(',')[0])
            section = None
        i += 1

    return {
        'nodes': nodes, 'elements': elements, 'fixed_nodes': sorted(set(fixed_nodes)),
        'point_a': point_a, 'point_o': point_o,
        'young': young, 'poisson': poisson, 'density': density, 'cte': cte,
    }


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
        f.write(f'!MATERIAL, NAME=FC300, ITEM=2\n')
        f.write('!ITEM=1, SUBITEM=2\n')
        f.write(f' {model["young"]!r}, {model["poisson"]!r}\n')
        f.write('!ITEM=2, SUBITEM=1\n')
        f.write(f' {model["density"]!r}\n')
        f.write('!SECTION, TYPE=SOLID, EGRP=body, MATERIAL=FC300\n')
        f.write('!END\n')


def write_ctrl(path):
    with open(path, 'w', encoding='ascii') as f:
        f.write(
            "!MESH, NAME=fstrMSH, TYPE=HECMW-ENTIRE\nFistrModel.msh\n"
            "!MESH, NAME=mesh, TYPE=HECMW-ENTIRE\nFistrModel.msh\n"
            "!CONTROL,NAME=fstrCNT\nFistrModel.cnt\n"
            "!RESULT,NAME=fstrRES,IO=OUT\nFistrModel.res\n"
            "!RESULT,NAME=vis_out,IO=OUT\nFistrModel.vis\n"
        )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    model = parse_inp(INP)
    print(f'nodes={len(model["nodes"])}, elements={len(model["elements"])}, '
          f'fixed={len(model["fixed_nodes"])}, point_a={model["point_a"]}, point_o={model["point_o"]}')
    print(f'material: E={model["young"]}, nu={model["poisson"]}, '
          f'density={model["density"]}, CTE={model["cte"]}')
    write_msh(model, MSH)
    write_ctrl(CTRL)
    print(f'wrote {MSH}')
    print(f'wrote {CTRL}')


if __name__ == '__main__':
    main()
