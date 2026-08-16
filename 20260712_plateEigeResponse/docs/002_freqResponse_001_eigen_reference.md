# 002_freqResponse が 001_eigen の固有値解析結果を参照する仕組み

## 結論

`002_freqResponse` は、`001_eigen` フォルダをFrontISTRが自動認識しているわけではありません。

`002_freqResponse` 内の入力ファイルに、`../001_eigen/...` という相対パスを明示しているため、001の固有値解析結果を使って周波数応答解析をしています。

重要な参照先は次の3つです。

| 参照元ファイル | 指定 | 参照しているもの |
|---|---|---|
| `002_freqResponse/hecmw_ctrl.dat` | `../001_eigen/FistrModel.msh` | 001で使ったメッシュ |
| `002_freqResponse/hecmw_ctrl.dat` | `../001_eigen/FistrModel.res` | 001で出力した固有ベクトル |
| `002_freqResponse/FistrModel.cnt` | `../001_eigen/0.log` | 001で出力した固有値・固有振動数 |

そのため、002で固有値解析を再実行しているのではなく、001の結果を読み込んで周波数応答だけを計算しています。

## `hecmw_ctrl.dat` で参照しているもの

`hecmw_ctrl.dat` は、FrontISTRに「どのメッシュ、どの制御ファイル、どの結果ファイルを使うか」を渡すグローバル制御ファイルです。

現在の `002_freqResponse/hecmw_ctrl.dat` では、メッシュを001側から読んでいます。

```text
!MESH, NAME=fstrMSH, TYPE=HECMW-ENTIRE
../001_eigen/FistrModel.msh
```

周波数応答解析は、固有値解析と同じ節点・要素・節点グループを前提にする必要があります。そこで、002側にメッシュをコピーせず、001で使った `FistrModel.msh` を直接参照しています。

同じファイル内で、固有ベクトルも001側から読んでいます。

```text
!RESULT,NAME=result-in,IO=IN
../001_eigen/FistrModel.res
```

ここで指定している `FistrModel.res` は、実体としては次のような001側の固有値解析結果群です。

```text
../001_eigen/FistrModel.res.0.1
../001_eigen/FistrModel.res.0.2
...
../001_eigen/FistrModel.res.0.20
```

つまり、周波数応答解析で使うモード形状（固有ベクトル）は、001の固有値解析で作った結果を使っています。

## `FistrModel.cnt` で参照しているもの

`FistrModel.cnt` は解析条件の本体です。周波数応答解析では、`!SOLUTION,TYPE=DYNAMIC` と `!DYNAMIC` で周波数応答を指定しています。

001の固有値解析結果を読む指定は、次の `!EIGENREAD` です。

```text
!EIGENREAD
 ../001_eigen/0.log
 1, 20
```

この指定の意味は次の通りです。

- `../001_eigen/0.log` から固有値・固有振動数を読む
- 読み込むモード範囲は1〜20モード

`0.log` には固有値解析で得られた固有振動数が記録されています。周波数応答解析では、この固有振動数と `hecmw_ctrl.dat` から読んだ固有ベクトルを使って、指定した周波数範囲の応答を計算します。

## 002で再計算しているもの

002で再計算しているのは、固有値解析ではなく周波数応答解析です。

現在の `FistrModel.cnt` では、周波数範囲を次のように指定しています。

```text
!DYNAMIC
 11, 2
 100, 1000, 90, 1000.0
```

これは、100〜1000Hzの範囲を90ステップで計算する指定です。1次固有振動数が約536Hzなので、その近傍の共振ピークを見るための設定です。

再計算後のピークは次の通りです。

```text
peak 540 Hz 1.0928165931497870e-02
```

## 002にあった `.res` や `.pvtu` の意味

以前の002では、次の指定が入っていました。

```text
!WRITE,RESULT
!WRITE,VISUAL
```

また、末尾にVTK出力用の設定もありました。

```text
!VISUAL,method=PSR
!surface_num=1
!surface 1
!output_type=VTK
```

このため、002側に次のようなファイルが出ていました。

```text
FistrModel.res.0.1 ... FistrModel.res.0.90
FistrModel_dyna.res.0.1 ... FistrModel_dyna.res.0.10
FistrModel.vis_psf.0001.pvtu ...
```

これらは002で固有値解析を再実行した結果ではありません。周波数応答解析の各周波数点や可視化用の出力です。

コンプライアンス曲線だけが目的なら、これらは不要です。現在は `!WRITE,RESULT` と `!WRITE,VISUAL` を外しているため、002の再計算では `.res`、`.pvtu`、`.vtu` は出力されません。

必要な主な結果は `002_freqResponse/0.log` です。

## 現在の最小出力構成

現在の002は、次の方針にしています。

- 001のメッシュを読む: `../001_eigen/FistrModel.msh`
- 001の固有ベクトルを読む: `../001_eigen/FistrModel.res`
- 001の固有値ログを読む: `../001_eigen/0.log`
- 002では周波数応答のモニタ結果を `0.log` に出す
- 002では各周波数点の `.res` や可視化用 `.pvtu/.vtu` は出さない

この構成なら、001の固有値解析結果を再利用しつつ、002側の出力をコンプライアンス曲線作成に必要な最小限へ絞れます。
