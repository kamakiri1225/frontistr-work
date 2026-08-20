# このサンプルとFrontISTR側の実装との比較

`ThermoSenseAnalyzer_00.py`（Quad4シェル要素、CATIA由来のモデル）と、
`model/004_H` 〜 `model/006_KinvH_test`（FrontISTR、四面体一次要素341）を比較した。
メッシュも要素タイプも別物なので数値そのものは比較できないが、
**HとWが行列として構成されているか**という設計面は比較できる。

## H（温度荷重変換行列）

| | 定義 | 形状 |
|---|---|---|
| このサンプル | `make_H()`: `sparse.lil_matrix((DOF_TOTAL, NODES))` | (全自由度) × (節点数) |
| FrontISTR側 | `H_fistr.npz` / `H_matrix.mtx` | `(1275, 425)` = (425節点×3自由度) × (425節点) |

どちらも `f = H T`（節点温度ベクトル T → 節点荷重ベクトル f）の変換行列であり、
1列＝1節点の単位温度応答になっている。行列として一致している。

## W（K⁻¹Hのうち測定点だけを取り出したもの）

| | 定義 | 形状 |
|---|---|---|
| このサンプル | `make_W_xyz_i` / `make_W_xyz_end`: 測定点`tool`と基準点`origin`の変位差を全節点温度について計算し `W_x, W_y, W_z`（各長さNODES）に格納 | 実質 (3) × (節点数) |
| FrontISTR側 | `post/compute_kinvH.py --diff` が出力する `Wdiff_283_100.npy` | `(3, 425)` |

どちらも「K⁻¹Hの全行を求めず、測定に関係する行（3自由度分）だけを取り出す」という
同じ考え方で、実質3×節点数の行列になっている。このサンプルではPython配列を
3本（x,y,z）に分けて持っているだけで、`np.stack([W_x, W_y, W_z])` とすれば
FrontISTR側の `Wdiff` と同じ形状になる。

## 結論（設計面）

HもWも、このサンプルとFrontISTR側の両方で正しく行列として構成されている。
FrontISTR側は数値検証も行っており、`post/compare_H.py` でDUMPH直接出力と
標準機能ベースのHが一致すること、`post/validate_kinvH.py` でK⁻¹Hによる予測変位が
FrontISTRの解と一致することを確認済み（結果は `model/005_H_direct/H_compare_report.txt`
と `model/006_KinvH_test/validate_report.txt` に保存）。

## 数値での比較（同一モデルQuad4_FEM_Tji.inpで実施）

`ThermoSenseAnalyzer_00.py`は`setting/settings.yml`が本リポジトリに無く単体実行できないため、
同じ数式だけを移植してこのモデル（`Quad4_FEM_Tji.inp`、材料定数はinpの実際の値
E=130000000, ν=0.27, density=7.4e-06, **CTE=1.2e-05**）でH・K・Wを計算し、
FrontISTRの計算結果と直接突き合わせた。結果と計算時間の比較は
[`../../model/008_Tji_compare/README.md`](../../model/008_Tji_compare/README.md) を参照。
H・K・Wいずれも相対差1e-8〜1e-12（数値誤差レベル）で一致した。
