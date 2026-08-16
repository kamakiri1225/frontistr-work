# 005_H_direct

## このフォルダの目的

改造版FrontISTRの `DUMPH=YES` を使い、温度荷重行列Hを
`H_matrix.mtx` へ直接出力した計算フォルダである。

2026-08-11 01:01（JST）に、このフォルダ内で実際にFrontISTRを実行した。

## 実行したコマンド

検証用に `/tmp` でビルドした改造版FrontISTRを使用した。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/005_H_direct
/tmp/frontistr-hsrc.1Rzr0X/build-h/fistr1/fistr1 > run_dumph.log 2>&1
```

実行は終了コード0で完了した。

`/tmp` の実行ファイルは検証用であり、恒久的なインストール先ではない。
再現するときは `docs/05_手順_FrontISTR_DUMPH追加とビルド.md` に従い、
改造版を `/home/kamakiri/local/frontistr-dumph` へインストールする。

## 入力ファイル

| ファイル | 内容 |
|---|---|
| `FistrModel.msh` | 425節点、1403個の四面体一次要素341からなるメッシュ |
| `FistrModel.cnt` | 材料、線膨張係数、節点2の単位温度、`DUMPH=YES` の設定 |
| `hecmw_ctrl.dat` | メッシュと解析制御ファイルの対応 |

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `H_matrix.mtx` | 改造版が直接出力した温度荷重行列H。大きさは1275×425 |
| `dump_matrix_1_0.mm` | 全体剛性行列K |
| `dump_matrix_1_0.rhs` | 節点2に単位温度を与えた温度荷重RHS |
| `run_dumph.log` | FrontISTRの標準出力と実行情報 |
| `FSTR.msg` | `DUMPH: wrote H_matrix.mtx` を含むメッセージ |

このフォルダの `H_matrix.mtx` 第2列と `dump_matrix_1_0.rhs` は、
最大絶対差0、相対差0で一致した。

## EasyISTRで確認するもの

EasyISTRでは `FistrModel.msh` を読み、次の内容を確認できる。

- 節点と四面体一次要素341の形状
- 節点グループ `fix` と `force`
- 要素グループ `body`
- 材料 `FC300`

解析条件の実体は `FistrModel.cnt` にある。

- `!TEMPERATURE 2,1.0`
- `!ELASTIC`
- `!EXPANSION_COEFF`
- `!SOLVER,...,DUMPH=YES`

`DUMPH` は今回追加した独自キーワードなので、未改造のEasyISTRの画面には
専用項目がない。EasyISTRでメッシュを確認し、`DUMPH=YES` は
`FistrModel.cnt` をテキストとして確認する。

EasyISTRから制御ファイルを再出力すると、未知の `DUMPH=YES` が削除される
可能性があるため、元の `FistrModel.cnt` を残しておく。

## ParaViewで確認するもの

形状確認用として、同じメッシュから作成した次のVTUを保存している。

```text
vtkMeshData/elementGrp_body.vtu
vtkMeshData/edgeElementGrp_body.vtu
```

ParaViewでは `vtkMeshData/elementGrp_body.vtu` を開くと、要素形状を確認できる。

このVTUの作成元と `005_H_direct/FistrModel.msh` は同一メッシュであり、
メッシュファイルのSHA-256が一致することを確認している。

`H_matrix.mtx` はMatrix Market形式の行列であり、ParaViewで直接開く
変位・応力結果ではない。また、この計算は `DUMPEXIT=YES` で行列出力後に
終了しているため、変位や応力のVTU結果は作成していない。
