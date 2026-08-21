# frontistr/patch/modified_src — カスタマイズした FrontISTR ソース（実ファイル）

DUMPW 改造で**実際に書き換えた FrontISTR のソースファイル**（フルの中身）をここに置いてある。
差分だけなら `../frontistr_dumpw_tet.patch`（`git apply` 用）を、実ファイルを見たい/使いたい場合は
こちらを参照。

- **ベースバージョン**：**FrontISTR 5.9**（`VERSION` ファイル = `Version 5.9 (2026/03/20)`、
  master のコミット `7f48eae0`）。
- 元のソースツリーでの位置は、ここでの相対パスと同じ（`fistr1/src/...`）。

> **重要**：コピー方式 (B) は「フルの実ファイルで上書きする」ので、**上書き先のクリーンな
> FrontISTR が同じ 5.9（`7f48eae0`）であること**が前提。別バージョンに上書きすると他の変更まで
> 巻き戻してしまう。バージョンが違う場合はパッチ方式 (A)（`git apply`）を使うか、まず 5.9 を
> 用意すること。

| ファイル | 役割（DUMPW での変更点） |
|---|---|
| `fistr1/src/common/fstr_ctrl_common.f90` | `!SOLVER` の新キーワード `DUMPW`（NO/YES）読み取り |
| `fistr1/src/common/fstr_setup.f90` | `DUMPW` を `svIarray(37)` に格納する配線 |
| `fistr1/src/lib/m_fstr.F90` | `Iarray(37)` の既定値 0 |
| `fistr1/src/analysis/static/fstr_solve_NonLinear.f90` | 変位 solve 直後に `fstr_dump_sensitivity`（アジョイント6本 solve の司令塔） |
| `fistr1/src/analysis/static/fstr_ass_load.f90` | `fstr_sensitivity_read_dofs` / `_solid_nnode` / `_export`（H組立） / `_write_vtk` / `_heapsort` を追加 |

## 使い方（どちらでも同じ結果）

```bash
# (A) パッチを当てる（推奨）
cd $HOME/src/FrontISTR              # クリーンな FrontISTR 5.9
git apply /path/to/frontistr/patch/frontistr_dumpw_tet.patch

# (B) ここのファイルで上書きする（cp -r は「マージ」。フォルダごと消えたりしない）
cp -r frontistr/patch/modified_src/fistr1 $HOME/src/FrontISTR/
```

> **`cp -r fistr1 …/` はフォルダを丸ごと置き換えない**。`cp -r` は**マージ**で、
> `modified_src/fistr1` に入っている**上表の5ファイルだけ**を同じ位置で上書きし、
> 元の `fistr1/` の他のファイルはそのまま残る（削除もされない）。心配なら次のように
> **ファイルを1つずつ**コピーしても同じ（こちらの方が「どれを上書きするか」が明確）：

```bash
D=$HOME/src/FrontISTR                    # 上書き先（クリーンな 5.9）
S=frontistr/patch/modified_src
cp $S/fistr1/src/analysis/static/fstr_ass_load.f90        $D/fistr1/src/analysis/static/
cp $S/fistr1/src/analysis/static/fstr_solve_NonLinear.f90 $D/fistr1/src/analysis/static/
cp $S/fistr1/src/common/fstr_ctrl_common.f90              $D/fistr1/src/common/
cp $S/fistr1/src/common/fstr_setup.f90                    $D/fistr1/src/common/
cp $S/fistr1/src/lib/m_fstr.F90                           $D/fistr1/src/lib/
```

ビルド手順は `frontistr/docs/13`・`frontistr/docs/14` を参照。
