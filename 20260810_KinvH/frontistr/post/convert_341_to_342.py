#!/usr/bin/env python3
"""
convert_341_to_342.py — 一次四面体(341, C3D4)のFrontISTRメッシュを、
    二次四面体(342, C3D10)へ変換する。各辺の中点に節点を追加し、
    FrontISTRの342ファイル規約の節点順で要素を書き出す。

FrontISTRの342ファイル節点順（B342.mshで実測して確認した規約）:
  1..4 = 角節点 (n1,n2,n3,n4)
  5 = mid(n2,n3)  6 = mid(n1,n3)  7 = mid(n1,n2)
  8 = mid(n1,n4)  9 = mid(n2,n4)  10 = mid(n3,n4)

固定節点群(fix)は、元の角節点に加えて「両端がともに固定されている辺」の
中点も固定に含める（固定面を二次要素でも固定面のまま保つため）。

使い方:
  python3 convert_341_to_342.py <in_341.msh> <out_342.msh>
"""
import sys


def parse_msh(path):
    header, nodes, elems, fix, material, section = ['3'], {}, [], [], [], []
    node_order = []
    with open(path) as f:
        lines = f.read().splitlines()
    sect = None
    for ln in lines:
        s = ln.strip()
        u = s.upper()
        if u.startswith('!HEADER'):
            sect = 'header'; continue
        if u.startswith('!NODE'):
            sect = 'node'; continue
        if u.startswith('!ELEMENT'):
            sect = 'elem'; continue
        if u.startswith('!NGROUP'):
            sect = 'fix'; continue
        if u.startswith('!MATERIAL'):
            sect = 'mat'; material.append(ln); continue
        if u.startswith('!SECTION'):
            sect = 'sec'; section.append(ln); continue
        if u.startswith('!END'):
            sect = None; continue
        if u.startswith('!'):
            # material sub-items (!ITEM=...) belong to the material block
            if sect == 'mat':
                material.append(ln)
            continue
        if not s:
            continue
        if sect == 'header':
            header = [s]
        elif sect == 'node':
            p = [x.strip() for x in s.split(',')]
            nid = int(p[0])
            nodes[nid] = (float(p[1]), float(p[2]), float(p[3]))
            node_order.append(nid)
        elif sect == 'elem':
            p = [int(x) for x in s.replace(',', ' ').split()]
            elems.append(p)   # [eid, n1, n2, n3, n4]
        elif sect == 'fix':
            fix += [int(x) for x in s.replace(',', ' ').split()]
        elif sect == 'mat':
            material.append(ln)
        elif sect == 'sec':
            section.append(ln)
    return header, nodes, node_order, elems, fix, material, section


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    inp, outp = sys.argv[1], sys.argv[2]
    header, nodes, node_order, elems, fix, material, section = parse_msh(inp)

    fixset = set(fix)
    next_id = max(nodes) + 1
    edge_mid = {}          # (min,max) -> mid node id
    mid_nodes = {}         # id -> coord
    fixed_mid = []

    def get_mid(a, b):
        nonlocal next_id
        key = (a, b) if a < b else (b, a)
        if key in edge_mid:
            return edge_mid[key]
        mid_id = next_id; next_id += 1
        edge_mid[key] = mid_id
        ax, ay, az = nodes[a]; bx, by, bz = nodes[b]
        mid_nodes[mid_id] = ((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2)
        if a in fixset and b in fixset:
            fixed_mid.append(mid_id)
        return mid_id

    out_elems = []
    for e in elems:
        eid, n1, n2, n3, n4 = e[0], e[1], e[2], e[3], e[4]
        m5 = get_mid(n2, n3)   # mid(2,3)
        m6 = get_mid(n1, n3)   # mid(1,3)
        m7 = get_mid(n1, n2)   # mid(1,2)
        m8 = get_mid(n1, n4)   # mid(1,4)
        m9 = get_mid(n2, n4)   # mid(2,4)
        m10 = get_mid(n3, n4)  # mid(3,4)
        out_elems.append([eid, n1, n2, n3, n4, m5, m6, m7, m8, m9, m10])

    all_fix = sorted(set(fix) | set(fixed_mid))

    with open(outp, 'w') as f:
        f.write('!HEADER\n %s\n' % header[0])
        f.write('!NODE\n')
        for nid in node_order:
            x, y, z = nodes[nid]
            f.write(' %d, %r, %r, %r\n' % (nid, x, y, z))
        for nid in sorted(mid_nodes):
            x, y, z = mid_nodes[nid]
            f.write(' %d, %r, %r, %r\n' % (nid, x, y, z))
        f.write('!ELEMENT, TYPE=342, EGRP=body\n')
        for e in out_elems:
            f.write(' ' + ', '.join(str(v) for v in e) + '\n')
        f.write('!NGROUP, NGRP=fix\n')
        for i in range(0, len(all_fix), 8):
            f.write(' ' + ', '.join(str(v) for v in all_fix[i:i + 8]) + '\n')
        for ln in material:
            f.write(ln + '\n')
        for ln in section:
            f.write(ln + '\n')
        f.write('!END\n')

    print('input  341: %d nodes, %d elems' % (len(nodes), len(elems)))
    print('output 342: %d nodes (+%d mid), %d elems' %
          (len(nodes) + len(mid_nodes), len(mid_nodes), len(out_elems)))
    print('fixed nodes: %d (corners %d + mids %d)' %
          (len(all_fix), len(fix), len(fixed_mid)))
    print('wrote', outp)


if __name__ == '__main__':
    main()
