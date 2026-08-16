# 作業ログ：FrontISTRで K・H を出力し K⁻¹H を計算する

> 記事化用の作業記録。時系列でメモを残す。（開始 2026-08-10）

## 0. ゴール

- 全体剛性行列 **K**（n_dof × n_dof）を出力
- 温度荷重変換行列 **H**（n_dof × n_node、`f_thermal = H·T`）を出力
- **K⁻¹H**（節点温度 → 節点変位）を後処理で計算
- 関係式：`u = K⁻¹ f = (K⁻¹H) T`

## 1. 環境・方針の確認

- WSLのFrontISTRを使用。ソース `~/src/FrontISTR`、ビルド `build-codex`（CMake, gfortran, RELEASE, MPI/MKL/MUMPS=OFF, LAPACK=ON）、install `~/local/frontistr`。
- 単一ドメイン（MPI無効）＝ローカル行列がそのままグローバル行列。並列組み立ての考慮不要。
- 通常実行を壊さないよう、出力は **環境変数 `FSTR_EXPORT_KH=1` でゲート**する opt-in 方式。
- 構成：
  - 標準fistr1 … K確認用（既存の行列ダンプ機構）
  - 改造fistr1 … K・H出力用
  - 後処理（Python/scipy）… K⁻¹H 計算

## 2. ソース調査で分かったこと

- **行列ダンプ機構**：`hecmw1/src/solver/matrix/hecmw_matrix_dump.f90`
  - `hecmw_mat_dump` が K を MatrixMarket / CSR / BSR で、RHS も出力。
  - DIRECT ソルバー（`hecmw_solver_direct.f90`）から呼ばれる。
  - ただし本バージョンは制御カード（.cnt）から有効化するパスが無く、既定OFF。
- **温度荷重の計算**：`fistr1/src/analysis/static/fstr_ass_load.f90`
  - `fstr_ass_load` → `process_thermal_loads` → 要素ループ → `calculate_thermal_load` → `TLOAD_C3`（3D solid）。
- **要素温度荷重 `TLOAD_C3`**（`fistr1/src/lib/static_LIB_3d.f90`）：
  - 積分点で `TEMPC = Σ N_j T_j`、`EPSTH(1:3)=α(TEMPC−Tref)`、`SGM=D·EPSTH`、`VECT += Bᵀ SGM wg`。
  - 節点温度 T_j で線形化 → 要素H：`H_e[:,j] = Σ_gauss (Bᵀ D a) N_j wg`, `a=α[1,1,1,0,0,0]ᵀ`。
  - サイズ (nn·3)×nn。線形性の前提：α温度非依存・等方・T0=Tref。

## 3. 実施したこと

- 作業フォルダ `20260810_KinvH/{model,patch,post,docs}` を作成。
- `docs/06_DESIGN.md` に設計をまとめた。
- `post/kinvh.py` を作成（K,H の MatrixMarket を読み、LU分解を再利用して X=K⁻¹H を列ごとに解く）。
  - **self-test 合格**：合成SPD行列で `||X−X_ref||/||X_ref|| = 3.7e-16`、`||KX−H||/||H|| = 4.4e-16`。
- ビルド確認：`build-codex` で `make` が通ることを確認（改造後の再ビルドが可能）。
- VS Code：ソースを WSL リモートで開く方法に切り替え（`code /home/kamakiri/src/FrontISTR`）。

## 4. 設計上の論点（境界条件の扱い）

K⁻¹H を FrontISTR の変位解と一致させるには、境界条件（拘束自由度）の扱いをそろえる必要がある。

- 方針：**BC適用前の生の K と H**（要素組み立て直後、AddBC前）＋**拘束自由度リスト**を出力し、
  後処理で拘束自由度を消去（縮約）して `K_ff u_f = (H T)_f` を解く。
- これにより「解いている物理」を透明にでき、記事でも説明しやすい。
- 別案：BC適用後の K と、同じBCを施した H を出す（fistr1側でBC複製が必要で複雑）。→ 不採用。

## 4.5 リファレンス実装（sample/001_3DFEM）

- ユーザー提供の自作3次元1次要素FEM（Python, takun-physics.net記事一式）を `sample/001_3DFEM` に解凍。
  - `004_3次元四面体１次要素.ipynb`（四面体1次＝FrontISTRの341と同じ）
  - `Quad4_structual/Quad4_main.py`（`make_D/make_B/make_Ke/make_K/境界条件/solve`）。温度荷重Hは未実装。
- 使い道：**FrontISTR出力の K・H・K⁻¹H を、この自作FEMで独立に検算する**リファレンス。
  - まず K を突き合わせ。次に同規約で `make_H = ∫BᵀDαN dV` を足して H を突き合わせ。

## 5. 次のステップ（TODO）

- [x] 検証用の熱膨張モデルを作成（`model/003_Htest`）
- [x] `!SOLVER,DUMPH=YES` と要素タイプ341のH出力を試作
- [x] 検証用コピーで再ビルドし、Hと標準RHSの一致を確認
- [ ] FrontISTR本体へ `patch/frontistr_dumph_341.patch` を適用・インストール
- [ ] Python後処理を行う段階で、BC縮約後のK⁻¹HとFrontISTR変位を比較

## 6. K比較の結果（Quad4_FEM_00, C3D4/341, mm-ton-s）

FrontISTR と 自作Python(`Quad4_main.py`) の全体剛性行列 K を比較 → **一致**。

- モデル：425節点・1403要素・FC300（E=130000 MPa, ν=0.27）、mm-ton-s系。
- FrontISTR：`!SOLVER ... DUMPTYPE=CSR, DUMPEXIT=NO` で K（BC適用後, 1275×1275）をダンプ。
  - `DUMPEXIT=NO` なら K も 変位も1回で出る（`DUMPEXIT=YES`はKだけで即終了）。
  - K は「BC適用後」（ソルバー入口でダンプ＝AddBC後）。生Kが要る時は !BOUNDARY を外して実行。
- Python：`Kexport.py`（`Quad4_main.py`のコピーに保存2行を追加）で `make_K`→`K_python_raw.npz`、
  `set_baoudary_U_F`→`K_python_bc.npz` を出力。
- **自由度の並びの違い**（重要）：
  - FrontISTR：節点n → (x,y,z) = (3(n-1), +1, +2) … 自然順
  - Python：節点g → (3g=**y**, 3g+1=**x**, 3g+2=z) … `make_K`の添字式で **x,y が入替**
  - 節点順は両者 inp順で一致。→ 「節点内 x↔y 入替」の置換で整列。
- **比較結果**：整列後 `||Kf−Kp||/||Kf|| = 2.3e-7`（max|K|=6.34e6, max diff 2.95）。
  - 残差はちょうど **Python側 float32** の精度。→ 実質同一行列。
  - 変位も一致（|u|max: FrontISTR 1.118e-2 mm ≈ Python 1.107e-2 mm、差~1%はfloat32）。
- 後処理：`post/read_fistr_matrix.py`（CSR/MM読込）、`post/compare_K.py`（整列＋比較）。

## メモ（記事の切り口候補）

- 「FrontISTRのソースを読む：温度荷重はどこで計算されているか（TLOAD_C3）」
- 「剛性行列と温度荷重変換行列を取り出す」
- 「K⁻¹H で “温度→変位” の感度行列をつくる」
- 境界条件の縮約の話（なぜ生Kは特異か、拘束をどう入れるか）

## 7. 2026-08-11 温度荷重行列Hの標準出力機能を再調査

### 現在の依頼

- PythonによるHの後処理は後日行う。
- まず、全体剛性行列Kと同様に入力キーワードだけでHを直接出力できるか調べる。
- 標準機能にない場合は、FrontISTRのソースへ出力機能を追加して再コンパイルする。
- Claude Codeへ戻す可能性があるため、調査根拠と次の作業をログに残す。

### 調査結果

- 使用中のFrontISTRはコミット `7f48eae0`。
- `!SOLVER` の `DUMPTYPE` が受け付ける値は `NONE`、`MM`、`CSR`、`BSR` のみ。
- `DUMPTYPE` は係数行列Kと右辺 `hecMAT%B` を出力する。
- 温度荷重は `fstr_ass_load.f90` で要素ベクトルとして計算され、`hecMAT%B` へ直接加算される。
- FrontISTR内部では全体Hを組み立てていない。
- したがって、標準キーワードで得られるのはHではなく、指定温度Tに対する `H T`（RHS）だけ。
- Hを1回の解析で直接出力するには、ソース変更と再コンパイルが必要。

詳細は `docs/03_温度荷重行列H_FrontISTR標準機能調査.md` に記載。

### 方針の修正

- `model/004_H/build_H.py` による全節点ループは、標準機能だけでHを復元できることを確認する代替実験。
- これは今回求めている「FrontISTRによるHの直接出力」ではないため、主作業から外す。
- 2026-08-11の実行は250/425列で停止。途中結果は `model/004_H/H_fistr.partial.npz`、進捗は `H_fistr.progress` に保存されている。

### 次の作業

- [x] 標準入力キーワードにH直接出力がないことをソースで確認
- [x] KダンプとRHSダンプの処理を確認
- [x] Hが内部で全体行列として保持されないことを確認
- [x] `!SOLVER,DUMPH=YES` の入力処理を設計・追加（検証用ソースコピー）
- [x] 要素タイプ341の要素Hを全体Hへ組み立てる処理を追加
- [x] Matrix Market形式の `H_matrix.mtx` 出力を追加
- [x] FrontISTRを再コンパイル（検証用コピー、ビルド成功）
- [x] `H T` と既存の温度荷重RHSが一致することを検証

### 実装・検証結果

- 検証済みパッチ: `patch/frontistr_dumph_341.patch`
- 実行用入力: `model/005_H_direct`（`DUMPH=YES` 設定済み）
- 永続計算フォルダ: `model/005_H_direct`（2026-08-11 01:01 JSTに再実行）
- 保存済み出力: `H_matrix.mtx`、`dump_matrix_1_0.mm`、`.rhs`、`run_dumph.log`
- ParaView形状確認: `model/005_H_direct/vtkMeshData/elementGrp_body.vtu`
- ビルド結果: `[100%] Built target fistr1`
- 入力キーワード: `!SOLVER,...,DUMPH=YES`
- 出力: `H_matrix.mtx`
- 対象: 要素タイプ341、単一領域、線形・温度非依存材料
- 検証モデル: 425節点、1403要素、Hは1275×425
- `H[:,2]` と節点2単位温度時の標準RHSは最大差0、相対差0
- 一様温度時の合力は各方向とも約 `1e-10` 以下
- 詳細手順: `docs/05_手順_FrontISTR_DUMPH追加とビルド.md`

### ソースへの反映状況

- `/home/kamakiri/src/FrontISTR` 本体にはまだパッチを適用していない。
- 検証は `/tmp` のソースコピーで実施し、通常版FrontISTRを変更していない。
- 本体へ反映するときは、手順書の `git apply --check` から実施する。
- Claude Codeなどへの短い引き継ぎは `docs/08_HANDOFF.md` を参照する。
