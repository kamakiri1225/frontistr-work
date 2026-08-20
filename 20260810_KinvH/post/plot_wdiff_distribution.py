#!/usr/bin/env python3
"""
plot_wdiff_distribution.py — 熱感度 |Wdiff| の分布を、Python版とFrontISTR版
    （009 DUMPH+Pythonアジョイント / 011 DUMPW一次 / 012 DUMPW二次）で
    横並びに比較する1枚のPNGを作る。

docs/11 に貼ってあるParaViewの絵（T字ブラケットを斜め上から見た3D等角ビュー、
jetカラー）に見た目を合わせるため、3D座標を等角投影で2Dに落として散布図で描く
（この環境はmatplotlibのAxes3Dが使えないので投影を自前で計算する）。色は |Wdiff| の
大きさ（ParaViewと同じ線形スケール）。ラベルは日本語フォント無しでも化けない英語。

使い方（リポジトリの 20260810_KinvH/ で実行）:
  python3 post/plot_wdiff_distribution.py
  # -> docs/img/dumpw_wdiff_python_009_011_012.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import Normalize
from matplotlib import cm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POINT_A, POINT_O = 19, 103

# ParaView と同じ色域（docs/11 の legend に合わせる）
VMIN, VMAX = 1.4e-7, 4.7e-4
# 視点（ParaView の斜め上ビューに近づけた方位角・仰角）
AZIM, ELEV = -60.0, 20.0


def read_msh_nodes(path):
    lines = open(path).read().splitlines()
    nodes = {}
    i = 0
    while i < len(lines) and not lines[i].strip().upper().startswith('!NODE'):
        i += 1
    i += 1
    while i < len(lines) and not lines[i].strip().startswith('!'):
        p = lines[i].split(',')
        nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        i += 1
    return nodes, sorted(nodes)


def wdiff_from_npy(path, sorted_ids):
    w = np.load(path)
    return {nid: w[:, j] for j, nid in enumerate(sorted_ids)}


def wdiff_from_txt(path):
    d = {}
    for l in open(path):
        l = l.strip()
        if not l or l[0] == '#':
            continue
        p = l.split()
        d[int(p[0])] = np.array(list(map(float, p[1:4])))
    return d


def project(xyz, azim, elev):
    """3D点群を等角投影で2Dスクリーン座標(su,sv)と奥行きdepthに落とす。"""
    a = np.radians(azim); e = np.radians(elev)
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    xr = X * np.cos(a) + Y * np.sin(a)
    yr = -X * np.sin(a) + Y * np.cos(a)
    su = xr
    sv = Z * np.cos(e) - yr * np.sin(e)
    depth = Z * np.sin(e) + yr * np.cos(e)   # 大きいほど手前
    return su, sv, depth


def draw_panel(ax, nodes, ids, w, vmax, title):
    """1パネルに |Wdiff| の塗り分けコンターを描く（vmax は色スケールの上限）。"""
    cmap = cm.get_cmap('jet')
    norm = Normalize(vmin=VMIN, vmax=vmax)
    levels = np.linspace(VMIN, vmax, 25)
    xyz = np.array([nodes[n] for n in ids])
    mag = np.array([np.linalg.norm(w[n]) for n in ids])
    su, sv, depth = project(xyz, AZIM, ELEV)
    # 投影した点でドロネー三角形分割 -> 塗り分けコンター。T字の凹みを橋渡しする
    # 細長い三角形は辺が長いのでマスクして除く。
    tri = mtri.Triangulation(su, sv)
    t = tri.triangles
    d01 = np.hypot(su[t[:, 0]] - su[t[:, 1]], sv[t[:, 0]] - sv[t[:, 1]])
    d12 = np.hypot(su[t[:, 1]] - su[t[:, 2]], sv[t[:, 1]] - sv[t[:, 2]])
    d20 = np.hypot(su[t[:, 2]] - su[t[:, 0]], sv[t[:, 2]] - sv[t[:, 0]])
    maxedge = np.maximum(np.maximum(d01, d12), d20)
    tri.set_mask(maxedge > 2.5 * np.median(maxedge))
    ax.tricontourf(tri, mag, levels=levels, cmap=cmap, norm=norm, extend='max')
    for nid, mk in [(POINT_A, '^'), (POINT_O, 's')]:
        if nid in nodes:
            pu, pv, _ = project(np.array([nodes[nid]]), AZIM, ELEV)
            ax.scatter(pu, pv, facecolors='none', edgecolors='k', marker=mk,
                       s=140, linewidths=1.8, zorder=6,
                       label=('Point_A(19)' if mk == '^' else 'Point_O(103)'))
    ax.set_title(title, fontsize=9)
    ax.set_aspect('equal'); ax.axis('off')
    ax.legend(loc='lower right', fontsize=7, framealpha=0.9)
    return norm, cmap


def add_colorbar(fig, axes, norm, cmap, vmax):
    sm = cm.ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
    cb = fig.colorbar(sm, ax=axes, shrink=0.7, pad=0.01)
    cb.set_label('|Wdiff|  (thermal sensitivity magnitude)')
    cb.formatter.set_powerlimits((0, 0)); cb.update_ticks()


def main():
    mesh341 = os.path.join(ROOT, 'model/011_Tji_DUMPW/FistrModel.msh')
    mesh342 = os.path.join(ROOT, 'model/012_Tji_DUMPW_342/FistrModel.msh')
    nodes341, ids341 = read_msh_nodes(mesh341)
    nodes342, ids342 = read_msh_nodes(mesh342)
    w_py = wdiff_from_npy(os.path.join(ROOT, 'model/008_Tji_compare/Wdiff_python_tji.npy'), ids341)
    w009 = wdiff_from_npy(os.path.join(ROOT, 'model/009_Tji_H_direct/Wdiff_fistr_tji.npy'), ids341)
    w011 = wdiff_from_txt(os.path.join(ROOT, 'model/011_Tji_DUMPW/Wdiff_fistr.txt'))
    w012 = wdiff_from_txt(os.path.join(ROOT, 'model/012_Tji_DUMPW_342/Wdiff_fistr.txt'))

    # --- 図1: Python / 009 / 011 / 012 を同じ色スケール(VMAX)で ---
    panels = [('Python (pure-Python H)', nodes341, ids341, w_py),
              ('FrontISTR 009 (DUMPH + Python adjoint, 341)', nodes341, ids341, w009),
              ('FrontISTR 011 (DUMPW internal, 341)', nodes341, ids341, w011),
              ('FrontISTR 012 (DUMPW internal, 342)', nodes342, ids342, w012)]
    fig, axes = plt.subplots(1, 4, figsize=(20, 6.2))
    for ax, (title, nodes, ids, w) in zip(axes, panels):
        norm, cmap = draw_panel(ax, nodes, ids, w, VMAX, title)
    add_colorbar(fig, axes, norm, cmap, VMAX)
    fig.suptitle('Thermal sensitivity |Wdiff| : Python vs FrontISTR (009 / 011 / 012)   '
                 '[same color scale, max=4.7e-4 ; isometric view]', fontsize=12)
    out1 = os.path.join(ROOT, 'docs/img/dumpw_wdiff_python_009_011_012.png')
    fig.savefig(out1, dpi=120, bbox_inches='tight'); print('saved', out1)

    # --- 図2: 342だけ、色スケール上限を 4.7e-4（左）と その0.5倍=2.35e-4（右）で比較 ---
    fig2, axes2 = plt.subplots(1, 2, figsize=(11, 6.2))
    n1, c1 = draw_panel(axes2[0], nodes342, ids342, w012, VMAX,
                        'FrontISTR 012 (342)  contour max = 4.7e-4  (same as fig.1)')
    add_colorbar(fig2, axes2[0], n1, c1, VMAX)
    n2, c2 = draw_panel(axes2[1], nodes342, ids342, w012, 0.5 * VMAX,
                        'FrontISTR 012 (342)  contour max = 2.35e-4  (0.5x)')
    add_colorbar(fig2, axes2[1], n2, c2, 0.5 * VMAX)
    fig2.suptitle('2nd-order (342): contour max 4.7e-4 vs half (0.5x) 2.35e-4', fontsize=12)
    out2 = os.path.join(ROOT, 'docs/img/dumpw_wdiff_342_halfscale.png')
    fig2.savefig(out2, dpi=120, bbox_inches='tight'); print('saved', out2)


if __name__ == '__main__':
    main()
