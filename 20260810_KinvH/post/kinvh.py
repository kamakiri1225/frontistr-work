#!/usr/bin/env python3
"""
kinvh.py — FrontISTR が出力した全体剛性行列 K と温度荷重変換行列 H から
           K^{-1} H （節点温度 -> 節点変位 の変換行列）を計算する。

前提:
  K : n_dof x n_dof   （MatrixMarket coordinate 形式, K.mtx）
  H : n_dof x n_node  （MatrixMarket coordinate 形式, H.mtx）
  関係式:  f = H T,   K u = f   =>   u = (K^{-1} H) T

出力:
  X = K^{-1} H  （n_dof x n_node）を .mtx / .npy で保存。
  温度ベクトル T が与えられれば u = X T も計算する。

使い方:
  python3 kinvh.py --K K.mtx --H H.mtx --out KinvH
  python3 kinvh.py --K K.mtx --H H.mtx --out KinvH --temp T.txt   # u = X T も出力
  python3 kinvh.py --selftest                                     # 自己テスト
"""
import argparse
import sys
import numpy as np
from scipy.io import mmread, mmwrite
from scipy.sparse import csc_matrix, issparse
from scipy.sparse.linalg import spsolve, factorized


def compute_kinv_h(K, H):
    """X = K^{-1} H を列ごとに解いて返す（dense: n_dof x n_node）。"""
    K = csc_matrix(K)
    n = K.shape[0]
    if K.shape[1] != n:
        raise ValueError(f"K must be square, got {K.shape}")
    if H.shape[0] != n:
        raise ValueError(f"H rows ({H.shape[0]}) != K size ({n})")

    Hd = H.toarray() if issparse(H) else np.asarray(H, dtype=float)

    # K を1度だけ LU 分解して全列に再利用（列数が多いほど有利）
    solve = factorized(K)          # SuperLU
    m = Hd.shape[1]
    X = np.empty((n, m), dtype=float)
    for j in range(m):
        X[:, j] = solve(Hd[:, j])
    return X


def residual_report(K, H, X):
    """K X - H の残差を報告（解の妥当性チェック）。"""
    K = csc_matrix(K)
    Hd = H.toarray() if issparse(H) else np.asarray(H, dtype=float)
    R = K.dot(X) - Hd
    num = np.linalg.norm(R)
    den = np.linalg.norm(Hd) or 1.0
    return num, num / den


def selftest():
    """合成 SPD 行列 K とランダム H で K X = H を検証。"""
    rng = np.random.default_rng(0)
    n, m = 60, 5
    A = rng.standard_normal((n, n))
    K = A @ A.T + n * np.eye(n)     # 対称正定
    H = rng.standard_normal((n, m))

    Ks = csc_matrix(K)
    X = compute_kinv_h(Ks, H)

    # 参照解（dense solve）と比較
    X_ref = np.linalg.solve(K, H)
    err = np.linalg.norm(X - X_ref) / np.linalg.norm(X_ref)
    absn, reln = residual_report(Ks, H, X)

    print(f"[selftest] n={n}, n_rhs={m}")
    print(f"[selftest] ||X - X_ref|| / ||X_ref|| = {err:.3e}")
    print(f"[selftest] ||K X - H||   (abs)       = {absn:.3e}")
    print(f"[selftest] ||K X - H|| / ||H|| (rel) = {reln:.3e}")
    ok = err < 1e-8 and reln < 1e-8
    print(f"[selftest] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="Compute X = K^{-1} H from FrontISTR dumps")
    p.add_argument("--K", help="K matrix (MatrixMarket .mtx)")
    p.add_argument("--H", help="H matrix (MatrixMarket .mtx)")
    p.add_argument("--out", default="KinvH", help="output basename (default: KinvH)")
    p.add_argument("--temp", help="nodal temperature vector T (text, 1 value/line) -> u = X T")
    p.add_argument("--selftest", action="store_true", help="run synthetic self-test and exit")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.K or not args.H:
        p.error("--K and --H are required (or use --selftest)")

    K = mmread(args.K)
    H = mmread(args.H)
    print(f"loaded K: {K.shape}, H: {H.shape}")

    X = compute_kinv_h(K, H)
    absn, reln = residual_report(K, H, X)
    print(f"residual ||K X - H|| = {absn:.3e}  (rel {reln:.3e})")

    np.save(f"{args.out}.npy", X)
    mmwrite(f"{args.out}.mtx", csc_matrix(X))
    print(f"saved {args.out}.npy and {args.out}.mtx  (shape {X.shape})")

    if args.temp:
        T = np.loadtxt(args.temp).reshape(-1)
        if T.shape[0] != X.shape[1]:
            raise ValueError(f"temperature length {T.shape[0]} != H columns {X.shape[1]}")
        u = X @ T
        np.savetxt(f"{args.out}_u.txt", u)
        print(f"saved {args.out}_u.txt  (u = X T, len {u.shape[0]})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
