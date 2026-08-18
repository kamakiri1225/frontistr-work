#!/usr/bin/env python3
"""
write_sensitivity_vtk.py — W(=K^-1H)から取り出した測定点間の感度行列Wdiff（3×節点数）を、
                            ParaViewで開けるVTK(legacy, ASCII)として書き出す。

Wdiffの列jは「節点jに単位温度を与えたときの、Point_A-Point_O間相対変位の変化量」であり、
変位そのものではないが、outputvtk()（ThermoSenseAnalyzer_00.py）にならって
節点ベクトル場として可視化する（フィールド名は Sensitivity とし、Displacementとは呼ばない）。

使い方:
  python3 write_sensitivity_vtk.py --wdiff model/008_Tji_compare/Wdiff_python_tji.npy \
      --out model/008_Tji_compare/Wdiff_python_tji.vtk
  python3 write_sensitivity_vtk.py --wdiff model/008_Tji_compare/Wdiff_fistr_tji.npy \
      --out model/008_Tji_compare/Wdiff_fistr_tji.vtk
"""
import argparse
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from inp_to_fistr_msh import parse_inp, INP  # noqa: E402


def write_vtk(path, nodes, node_ids, elements, elem_ids, vec_field, field_name='Sensitivity'):
    nid_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    with open(path, 'w', encoding='ascii') as f:
        f.write('# vtk DataFile Version 2.0\n')
        f.write(f'{field_name} (Wdiff: Point_A - Point_O per unit nodal temperature)\n')
        f.write('ASCII\n')
        f.write('DATASET UNSTRUCTURED_GRID\n')
        f.write(f'POINTS {len(node_ids)} double\n')
        for nid in node_ids:
            x, y, z = nodes[nid]
            f.write(f'{x} {y} {z}\n')
        f.write(f'CELLS {len(elem_ids)} {len(elem_ids) * 5}\n')
        for eid in elem_ids:
            conn = [nid_to_idx[n] for n in elements[eid]]
            f.write('4 ' + ' '.join(str(c) for c in conn) + '\n')
        f.write(f'CELL_TYPES {len(elem_ids)}\n')
        for _ in elem_ids:
            f.write('10\n')  # VTK_TETRA
        f.write(f'POINT_DATA {len(node_ids)}\n')
        f.write(f'VECTORS {field_name} double\n')
        for i in range(len(node_ids)):
            vx, vy, vz = vec_field[0, i], vec_field[1, i], vec_field[2, i]
            f.write(f'{vx} {vy} {vz}\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wdiff', required=True, help='Wdiff .npy (shape (3, n_node))')
    ap.add_argument('--out', required=True, help='output .vtk path')
    ap.add_argument('--field-name', default='Sensitivity')
    ap.add_argument('--mesh-npz', default=None,
                     help='リファインメッシュなど、元のQuad4_FEM_Tji.inpと節点数が'
                          '異なる場合に指定する（refine_tji_mesh.pyが作るmesh_fine.npzなど）')
    args = ap.parse_args()

    if args.mesh_npz:
        data = np.load(args.mesh_npz, allow_pickle=True)
        node_ids = [int(n) for n in data['node_ids']]
        elem_ids = [int(e) for e in data['elem_ids']]
        nodes = {int(n): tuple(c) for n, c in zip(data['node_ids'], data['coords'])}
        elements = {int(e): [int(v) for v in row] for e, row in zip(data['elem_ids'], data['conn'])}
    else:
        model = parse_inp(INP)
        node_ids = sorted(model['nodes'])
        elem_ids = sorted(model['elements'])
        nodes = model['nodes']
        elements = model['elements']

    Wdiff = np.load(args.wdiff)
    if Wdiff.shape[1] != len(node_ids):
        raise ValueError(f'Wdiff columns {Wdiff.shape[1]} != n_node {len(node_ids)}')

    write_vtk(args.out, nodes, node_ids, elements, elem_ids, Wdiff, args.field_name)
    print(f'wrote {args.out}  (field={args.field_name}, n_node={len(node_ids)})')


if __name__ == '__main__':
    main()
