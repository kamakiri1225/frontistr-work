#!/usr/bin/env python3
"""
inp2fistr.py — Abaqus .inp (C3D4 線形四面体) を FrontISTR の .msh に変換する。
このモデル(Quad4_FEM_01.inp)専用の最小コンバータ。

出力:
  FistrModel.msh   : NODE / ELEMENT(341) / NGROUP(fix,force) / MATERIAL / SECTION
解析条件は .cnt 側で与える。

単位系: mm-ton-s 系（= N-mm-s。Quad4_main.py に合わせる）
  長さ=mm, 質量=tonne, 時間=s, 力=N, E/応力=MPa(=N/mm^2), 変位=mm, 熱膨張=1/K
  例) E=130000 MPa = 130 GPa（鋳鉄FC300 / Quad4_main.py の YOUNG=130000 と一致）
  密度=tonne/mm^3。鋳鉄7400kg/m^3 = 7.4e-9 tonne/mm^3（K・熱応力には無関係だが整合のため）。
"""
import re
import sys


def parse_inp(path):
    nodes = []      # (id, x, y, z)
    elems = []      # (id, n1, n2, n3, n4)
    nsets = {}      # name -> [ids]
    section = None  # current keyword
    cur_nset = None
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith('*'):
                key = s.split(',')[0].strip().upper().lstrip('*')
                if key == 'NODE':
                    section = 'NODE'
                elif key == 'ELEMENT':
                    m = re.search(r'TYPE\s*=\s*([A-Za-z0-9]+)', s, re.I)
                    etype = m.group(1).upper() if m else ''
                    section = 'ELEMENT' if etype == 'C3D4' else 'SKIP'
                elif key == 'NSET':
                    m = re.search(r'NSET\s*=\s*"?([^",]+)"?', s, re.I)
                    cur_nset = m.group(1).strip() if m else 'unnamed'
                    nsets.setdefault(cur_nset, [])
                    section = 'NSET'
                else:
                    section = 'SKIP'
                continue
            # data line
            if section == 'NODE':
                p = [t.strip() for t in s.split(',')]
                nodes.append((int(p[0]), float(p[1]), float(p[2]), float(p[3])))
            elif section == 'ELEMENT':
                p = [t.strip() for t in s.split(',') if t.strip() != '']
                elems.append(tuple(int(x) for x in p[:5]))
            elif section == 'NSET':
                ids = [int(t) for t in s.split(',') if t.strip() != '']
                nsets[cur_nset].extend(ids)
    return nodes, elems, nsets


def wrap_ids(ids, per_line=8):
    out = []
    for i in range(0, len(ids), per_line):
        out.append(', '.join(str(x) for x in ids[i:i + per_line]))
    return '\n'.join(out)


def write_msh(path, nodes, elems, fix_ids, force_ids, egrp='body',
              matname='FC300', young=130000.0, poisson=0.27,
              density=7.4e-9, expansion=1.2e-5):
    L = []
    L.append('!HEADER')
    L.append(' 3')
    L.append('!NODE')
    for nid, x, y, z in nodes:
        L.append(f' {nid}, {x}, {y}, {z}')
    L.append(f'!ELEMENT, TYPE=341, EGRP={egrp}')
    for e in elems:
        eid, n1, n2, n3, n4 = e
        L.append(f' {eid}, {n1}, {n2}, {n3}, {n4}')
    L.append('!NGROUP, NGRP=fix')
    L.append(wrap_ids(sorted(set(fix_ids))))
    L.append('!NGROUP, NGRP=force')
    L.append(wrap_ids(sorted(set(force_ids))))
    # HECMW 形式の材料（.msh に埋め込まないと SECTION が材料を解決できない）
    #   ITEM=1 (SUBITEM=2): 弾性 E, poisson
    #   ITEM=2 (SUBITEM=1): 密度
    # ※熱膨張は K には不要。H 段階で .cnt 側 !EXPANSION_COEF で与える。
    L.append(f'!MATERIAL, NAME={matname}, ITEM=2')
    L.append('!ITEM=1, SUBITEM=2')
    L.append(f' {young}, {poisson}')
    L.append('!ITEM=2, SUBITEM=1')
    L.append(f' {density}')
    L.append(f'!SECTION, TYPE=SOLID, EGRP={egrp}, MATERIAL={matname}')
    L.append('!END')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')


def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else 'Quad4_FEM_01.inp'
    out = sys.argv[2] if len(sys.argv) > 2 else 'FistrModel.msh'
    nodes, elems, nsets = parse_inp(inp)
    # nset 名は「Fixed (26)-1」「Force (29)-1」
    fix_key = next(k for k in nsets if k.lower().startswith('fixed'))
    force_key = next(k for k in nsets if k.lower().startswith('force'))
    fix_ids = nsets[fix_key]
    force_ids = nsets[force_key]
    print(f'nodes={len(nodes)}, elems={len(elems)}')
    print(f'fix nset "{fix_key}": {len(fix_ids)} nodes -> {sorted(set(fix_ids))}')
    print(f'force nset "{force_key}": {force_ids}')
    write_msh(out, nodes, elems, fix_ids, force_ids)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
