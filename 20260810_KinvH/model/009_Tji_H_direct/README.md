# 009_Tji_H_direct

## 目的

`model/008_Tji_compare`では、Hを標準機能だけで570回fistr1を再実行して組み立てた
（`post/build_H_tji.py`、484秒）。ここでは`model/005_H_direct`と同じ改造
（`DUMPH=YES`、`patch/frontistr_dumph_341.patch`）を当てたFrontISTRを
Quad4_FEM_Tjiモデル用にビルドし直し、**1回の実行でHを直接出力**する。

## ビルド手順

`docs/05_手順_FrontISTR_DUMPH追加とビルド.md`と同じ手順（今回`/home/kamakiri`は
`$HOME`に置き換えて記載し直した）。

```bash
cd $HOME/src/FrontISTR
git apply .../20260810_KinvH/patch/frontistr_dumph_341.patch

cmake -S . -B build-dumph \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DCMAKE_INSTALL_PREFIX=$HOME/local/frontistr-dumph \
  -DWITH_MPI=OFF -DWITH_OPENMP=ON -DWITH_LAPACK=ON \
  -DWITH_MKL=OFF -DWITH_MUMPS=OFF -DWITH_METIS=OFF \
  -DWITH_NETCDF=OFF -DWITH_REFINER=OFF -DWITH_REVOCAP=OFF \
  -DWITH_TOOLS=OFF -DWITH_DOC=OFF

cmake --build build-dumph -j2
cmake --install build-dumph
# -> $HOME/local/frontistr-dumph/bin/fistr1
```

## 入力ファイル

`model/008_Tji_compare/FistrModel.msh`（570節点、`post/inp_to_fistr_msh.py`で変換したもの）
と同じメッシュを使用。`FistrModel.cnt`は`model/005_H_direct`にならい、
`!SOLVER,...,DUMPH=YES,DUMPTYPE=MM,DUMPEXIT=YES`を指定。材料定数は
`Quad4_FEM_Tji.inp`の実際の値（E=130000000, ν=0.27, density=7.4e-06, CTE=1.2e-05）。

## 結果

| 項目 | 値 |
|---|---|
| 実行時間 | 1.81 s（`/usr/bin/time -v`で計測） |
| 出力 | `H_matrix.mtx`（1710×570, nnz=81552） |

`model/008_Tji_compare`の2つのHと比較（相対差はいずれも数値誤差レベル）:

| 比較対象 | 最大絶対差 | 相対差 |
|---|---|---|
| DUMPH直接出力 vs 標準機能で570回、節点を1つずつ計算(`H_fistr_tji.npz`) | 1.0e-06 | 1.5e-12 |
| DUMPH直接出力 vs Python直接計算(`H_python_tji.npz` / `ThermoSenseAnalyzer_standalone.py`) | 5.3e-07 | 4.5e-13 |

## まとめ

同じQuad4_FEM_Tjiモデルに対し、次の3通りの独立した方法で計算したHがすべて一致した。

1. FrontISTR標準機能を570回実行して節点を1つずつ計算する方法（`model/008_Tji_compare`, 484秒）
2. DUMPHパッチを当てたFrontISTRを1回実行（このフォルダ, 1.81秒）
3. `ThermoSenseAnalyzer_00.py`と同じ数式を移植したPython実装
   （`sample/002_thermalSensitive/Inp_Data/ThermoSenseAnalyzer_standalone.py`, 約0.5秒）

DUMPHパッチにより、Hの取得は570回実行(484秒)から1回実行(1.81秒)へ**約270倍高速化**した。
