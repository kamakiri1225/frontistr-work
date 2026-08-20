# 引き継ぎメモ: FrontISTRの温度荷重行列H出力

更新日: 2026-08-11

## ユーザーの現在の依頼

- Pythonによる後処理は後日扱う。
- まずFrontISTR標準キーワードでHを直接出力できるか調べる。
- 標準機能になければ、ソースを変更してコンパイルする。
- 変更ファイル、フォルダ構成、ビルドコマンド、物理的な処理、TeX数式を含む分かりやすい手順を残す。

## 確定したこと

- 標準の `!SOLVER,DUMPTYPE=...` はKとRHSを出力する機能で、H直接出力ではない。
- 温度荷重は全体Hを作らず、要素熱荷重を `hecMAT%B` へ直接加算している。
- 標準キーワードだけで全体Hを1回で直接出力する機能はない。
- ソース変更が必要。

根拠は `docs/03_温度荷重行列H_FrontISTR標準機能調査.md` に記載。

## 実装済みの試作

- 新キーワード: `!SOLVER,...,DUMPH=YES`
- 出力: `H_matrix.mtx`
- 対象: 四面体一次要素341、3自由度、単一領域、線形・温度非依存材料
- パッチ: `patch/frontistr_dumph_341.patch`
- 実行用入力: `model/005_H_direct`
- 詳細手順: `docs/05_手順_FrontISTR_DUMPH追加とビルド.md`

2026-08-11 01:01（JST）に `model/005_H_direct` で改造版FrontISTRを
再実行し、`H_matrix.mtx`、K、RHS、ログを永続保存した。
フォルダ内の確認方法は `model/005_H_direct/README.md` に記載している。

検証用のソースコピーでコンパイルに成功した。

```text
[100%] Built target fistr1
```

425節点・1403要素モデルで、直接出力したHの第2列と節点2単位温度時の標準RHSが完全一致した。

```text
H shape       = (1275, 425)
max abs diff  = 0.0
relative diff = 0.0
```

## 重要な現在状態

- `$HOME/src/FrontISTR` 本体は未変更。
- 通常版 `$HOME/local/frontistr/bin/fistr1` も未変更。
- 試作とコンパイルは `/tmp` のソースコピーで実施した。
- 計算入力と出力は `model/005_H_direct` に保存済み。
- 永続的に残る成果物は、プロジェクト内のパッチ、入力、ドキュメント。

## 次に行うこと

FrontISTR本体へパッチを適用し、通常版と別の場所へインストールする。

```bash
cd $HOME/src/FrontISTR
git apply --check \
  /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/patch/frontistr_dumph_341.patch
git apply \
  /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/patch/frontistr_dumph_341.patch
```

その後、`docs/05_手順_FrontISTR_DUMPH追加とビルド.md` の第6章に従い、`build-dumph` でビルドして `$HOME/local/frontistr-dumph` へインストールする。

## Python列抽出実験について

`model/004_H/build_H.py` は、標準RHSを節点ごとに集める代替実験であり、現在の主作業ではない。250/425列で停止しており、次の途中ファイルが残っている。

```text
model/004_H/H_fistr.partial.npz
model/004_H/H_fistr.progress
```

削除はしていない。Python後処理を再開するときの参考として扱う。
