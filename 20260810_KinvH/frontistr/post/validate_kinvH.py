#!/usr/bin/env python3
"""
validate_kinvH.py — u = W T (W=K^{-1}H) の予測変位を、FrontISTR の熱応力解析の
                    変位と突き合わせて検証する。

検証ケース: model/006_KinvH_test （全425節点に 100 度、端面 fix 固定）
  ・予測 : u_pred = W T,  W = model/004_H/KinvH.npy, T = 全節点100
  ・正解 : FrontISTR が解いた変位 model/006_KinvH_test/FistrModel.res.0.1
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W_NPY = os.path.join(ROOT, 'model', '004_H', 'KinvH.npy')
RES = os.path.join(ROOT, 'model', '006_KinvH_test', 'FistrModel.res.0.1')


def read_res_disp(path, nnode):
    """fstrresult の DISPLACEMENT(先頭3成分/節点) を読み、長さ 3*nnode で返す。"""
    lines = open(path, encoding='utf-8', errors='ignore').read().split('\n')
    start = next(k for k, l in enumerate(lines) if l.strip() == 'NodalMISES') + 1
    u = np.zeros(3 * nnode)
    i = start
    while i < len(lines):
        s = lines[i].strip()
        if s.isdigit() and len(s.split()) == 1:
            nid = int(s)
            nums = []
            j = i + 1
            while j < len(lines) and len(nums) < 10:
                nums += [float(x) for x in lines[j].split()]
                j += 1
            u[3 * (nid - 1):3 * (nid - 1) + 3] = nums[:3]
            i = j
        else:
            i += 1
    return u


def main():
    W = np.load(W_NPY)
    nnode = W.shape[1]
    T = np.full(nnode, 100.0)          # 検証ケースと同じ全節点100度
    u_pred = W @ T
    u_fistr = read_res_disp(RES, nnode)

    d = u_pred - u_fistr
    rel = np.linalg.norm(d) / np.linalg.norm(u_fistr)
    print(f'相対誤差 ||u_pred - u_fistr|| / ||u_fistr|| = {rel:.3e}')
    print(f'最大絶対差 = {np.abs(d).max():.3e} mm')
    for nid in (283, 100):
        b = 3 * (nid - 1)
        print(f'節点{nid}: 予測={u_pred[b:b+3]}  FrontISTR={u_fistr[b:b+3]}')


if __name__ == '__main__':
    main()
