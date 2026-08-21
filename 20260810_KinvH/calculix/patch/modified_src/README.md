# calculix/patch/modified_src — カスタマイズした CalculiX ソース（実ファイル）

DUMPKH 改造で**実際に書き換えた CalculiX のソース**（フルの中身）。差分だけなら
`../ccx_2.21_dumpkh.patch` を、実ファイルを見たい/使いたい場合はこちらを参照。

- **ベース**：CalculiX **ccx 2.21**（`http://www.dhondt.de/ccx_2.21.src.tar.bz2`）。
- 元のソースツリーでの位置は、ここでの相対パスと同じ（`ccx_2.21/src/...`）。

| ファイル | 変更点 |
|---|---|
| `ccx_2.21/src/linstatic.c` | 線形静解析ドライバ。`CCX_DUMPKH=1` のとき、剛性組み立て直後に **K.mtx・H.mtx・nactdof.txt・Wdiff_ccx.txt・sensitivity_Wdiff_ccx.vtk** を出して停止する処理を追加（K そのまま出力／C3D4 の H を自前計算／SPOOLES でアジョイント W／VTK 出力）。`sensitivity_points.dat` が無ければエラー停止。 |
| `ccx_2.21/src/Makefile` | 今の gcc/gfortran・システム ARPACK 向けのビルドフラグ変更（`-fallow-argument-mismatch`、`CC=gcc`、ARPACK を `libarpack.so.2` に、リンク前提の修正）。SPOOLES ビルドと合わせて `calculix/docs/01` の第1章参照。 |

## 使い方（どちらでも同じ結果）

```bash
# (A) パッチを当てる（推奨）
cd $HOME/src/calculix_build/CalculiX/ccx_2.21/src   # 展開したクリーンな ccx 2.21
git apply /path/to/calculix/patch/ccx_2.21_dumpkh.patch   # linstatic.c の差分

# (B) ここのファイルで上書きする
cp calculix/patch/modified_src/ccx_2.21/src/linstatic.c $HOME/src/calculix_build/CalculiX/ccx_2.21/src/
cp calculix/patch/modified_src/ccx_2.21/src/Makefile    $HOME/src/calculix_build/CalculiX/ccx_2.21/src/
```

導入（SPOOLES ビルド含む）・実行・結果は `calculix/docs/01` を参照。
