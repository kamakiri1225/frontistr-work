# サンプルの場所と使う順番

このフォルダの `001_3DFEM` は、FrontISTRから取り出した全体剛性行列Kの比較に使った自作Python FEMである。

FrontISTRの実行サンプルは `sample` ではなく、入力ファイルと計算結果をまとめて確認できるように `model` の下へ保存している。

## 1. Kの標準出力を確認する

```text
../model/001_K
```

FrontISTR標準の `DUMPTYPE=CSR` による全体剛性行列Kの出力サンプル。

## 2. Hの1列とRHSの関係を確認する

```text
../model/003_Htest
```

節点2だけに温度1を与え、FrontISTR標準機能が出力するRHSをHの第2列として取り出したサンプル。

## 3. 標準機能だけでH全体を作る

```text
../model/004_H
```

425節点へ順番に単位温度を与え、FrontISTRを425回実行してHを組み立てたサンプル。`H_fistr.npz` と `H_fistr.mtx` が計算結果である。

## 4. DUMPHでHを1回で直接出力する

```text
../model/005_H_direct
```

今回の主サンプル。改造版FrontISTRの `DUMPH=YES` を使った入力、出力された `H_matrix.mtx`、実行ログ、EasyISTRとParaViewで確認するためのファイルが入っている。最初にこのフォルダの `README.md` を読む。

改造に使うパッチは次にある。

```text
../patch/frontistr_dumph_341.patch
```

## 5. K⁻¹Hの変位をFrontISTRと比較する

```text
../model/006_KinvH_test
```

一様な温度変化を与えたFrontISTRの変位結果。`post/compute_kinvH.py` で計算した $\boldsymbol K^{-1}\boldsymbol H$ による変位と、`post/validate_kinvH.py` で比較する。

## 解説の読む順番

1. `../docs/09_ブログ_FrontISTRでKとHを取り出してKinvHを求める.md`
2. `../docs/04_手順_温度荷重行列H_FrontISTR.md`
3. `../docs/05_手順_FrontISTR_DUMPH追加とビルド.md`

`09` は全体の流れを説明したブログ用原稿、`04` はHの物理と検証の詳細、`05` はFrontISTRのソース改造とコンパイル手順である。
