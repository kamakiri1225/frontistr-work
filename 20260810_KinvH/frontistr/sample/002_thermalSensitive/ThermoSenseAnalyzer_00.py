import numpy as np
import numpy.linalg as LA
import pathlib
import os

import multiprocessing
from multiprocessing import Value, Array, cpu_count

import gc
import time
import sys

from scipy import sparse
#from scipy.sparse.linalg import dsolve
from scipy.sparse.linalg import splu

import INP_Data_import.Data_import as Dipt

#FC300
YOUNG = 130000.0                                            #ヤング率
POISSON = 0.27                                              #ポアソン比
#LAMBDA = 11.9e-6                                            #線膨張係数（/K）
LAMBDA = 1e-005                                             #線膨張係数　Catiaの数値
NODE_QUAD4 = 4                                              #要素の接点数
COMPONENTS = 6                                              #ひずみと応力の成分数
DOF_NODE = 3                                                #接点自由度
weight = 1.0 / 6.0                                          #積分点の重み係数

data_path = pathlib.Path(__file__).parent.resolve()

# ============================================================
#       ファイルの読み込み
# ============================================================
try:
    data_name = sys.argv&#91;1]                                 # inpファイル
    if not data_name.endswith('.inp'):
        raise ValueError("Error: 入力ファイルは .inp 形式である必要があります。")
except IndexError:
    print("Error: 入力ファイルが指定されていません。引数として「Inp_Data」フォルダにあるモデルファイル（.inp）を指定してください。")
    print("example: python ThermoSenseAnalyzer_00.py model.inp")
    sys.exit(1)
except ValueError as ve:
    print(ve)
    sys.exit(1)

print(data_name)
# ============================================================
#       コア数指定
# ============================================================
print(f"引数の数：{len(sys.argv)}")
try:
    number_of_cpus = cpu_count()  # システムのCPUコア数を取得
    
    # GUIから第二引数としてコア数を取る場合
    if len(sys.argv) == 3:
        print("GUIから実行されました")
        core = int(sys.argv&#91;2]) # GUI引数からコア数設定
    elif len(sys.argv) == 2:
        print("settings/core_settings.ymlからコア数設定が読み込まれました")
        core = Dipt.setting_core(data_path)
    else:
        raise ValueError("Error: 第二引数に 'コア数' を指定してください。")    

    # 入力されたコア数がシステムのCPUコア数を超えていた場合
    if core > number_of_cpus:
        raise ValueError(f"Error: 指定されたコア数 ({core}) はシステムの最大CPU数 ({number_of_cpus}) を超えています。")

except ValueError as ve:
    print(ve)
    sys.exit(1)
except Exception as e:
    print(f"Error occurred while setting core: {e}")
    sys.exit(1)

print(f"Using {core} cores for computation.")

# 初期状態
def initialize():
    #FEMモデル情報取得（Node,Element）
    fem_info = Dipt.data_import_01(data_name,data_path)

    #&#91;0]:node, &#91;1]:element, &#91;2]:fixed, &#91;3]:face_load &#91;4]:face_load_element &#91;5]:foece
    #モジュール定数
    NODES=len(fem_info&#91;0])                                          #全節点数
    ELEMENTS=len(fem_info&#91;1])                                       #全要素数
    DOF_TOTAL = DOF_NODE * NODES                                    #モデル全体の自由度
    DOF_QUAD4 = NODE_QUAD4 * DOF_NODE                               #要素自由度


    #モジュールレベル変数
    #接点のＸ座標配列
    x=sparse.lil_matrix((1, NODES), dtype="float32")
    #接点のＹ座標配列
    y=sparse.lil_matrix((1, NODES), dtype="float32")
    #節点のＺ座標配列
    z=sparse.lil_matrix((1,NODES), dtype="float32")
    #Input Data
    for i in range(NODES):
        x&#91;0,i]=fem_info&#91;0]&#91;i]&#91;1]
        y&#91;0,i]=fem_info&#91;0]&#91;i]&#91;2]
        z&#91;0,i]=fem_info&#91;0]&#91;i]&#91;3]
        
    #要素内節点順配列
    connectivity=sparse.lil_matrix((ELEMENTS, NODE_QUAD4),dtype="int32")      
    #Input Data
    for e in range(ELEMENTS):
        for i in range(NODE_QUAD4):
            connectivity&#91;e,i]=fem_info&#91;1]&#91;e]&#91;i+1]


    Um=np.zeros(DOF_TOTAL,dtype="bool")
    #Fixed_111
    fixed=sparse.lil_matrix((1, len(fem_info&#91;2])),dtype="int32")
    print("check111:",fem_info&#91;2]&#91;0])
    if fem_info&#91;2]&#91;0] != -1:
        for i in range(len(fem_info&#91;2])):
            fixed&#91;0,i]=fem_info&#91;2]&#91;i]
        for i in range(len(fem_info&#91;2])):
            for k in range(DOF_NODE):
                Um&#91;fixed&#91;0,i]*DOF_NODE+k]=True                   #Fixed_XYZ

    #Fixed_001
    fixed=sparse.lil_matrix((1, len(fem_info&#91;5])),dtype="int32")
    print("check001:",fem_info&#91;5]&#91;0])
    if fem_info&#91;5]&#91;0] != -1:
        for i in range(len(fem_info&#91;5])):
            fixed&#91;0,i]=fem_info&#91;5]&#91;i]
        for i in range(len(fem_info&#91;5])):
            Um&#91;fixed&#91;0,i]*DOF_NODE+2]=True                   #Fixed_Z

    #Fixed_010
    fixed=sparse.lil_matrix((1, len(fem_info&#91;6])),dtype="int32")
    print("check010:",fem_info&#91;6]&#91;0])
    if fem_info&#91;6]&#91;0] != -1:
        for i in range(len(fem_info&#91;6])):
            fixed&#91;0,i]=fem_info&#91;6]&#91;i]
        for i in range(len(fem_info&#91;6])):
            Um&#91;fixed&#91;0,i]*DOF_NODE+1]=True                   #Fixed_Y

    #Fixed_011
    fixed=sparse.lil_matrix((1, len(fem_info&#91;7])),dtype="int32")
    print("check011:",fem_info&#91;7]&#91;0])
    if fem_info&#91;7]&#91;0] != -1:
        for i in range(len(fem_info&#91;7])):
            fixed&#91;0,i]=fem_info&#91;7]&#91;i]
        for i in range(len(fem_info&#91;7])):
            Um&#91;fixed&#91;0,i]*DOF_NODE+1]=True                   #Fixed_Y
            Um&#91;fixed&#91;0,i]*DOF_NODE+2]=True                   #Fixed_Z

    #Fixed_100
    fixed=sparse.lil_matrix((1, len(fem_info&#91;8])),dtype="int32")
    print("check100:",fem_info&#91;8]&#91;0])
    if fem_info&#91;8]&#91;0] != -1:
        for i in range(len(fem_info&#91;8])):
            fixed&#91;0,i]=fem_info&#91;8]&#91;i]
        for i in range(len(fem_info&#91;8])):
            Um&#91;fixed&#91;0,i]*DOF_NODE+0]=True                   #Fixed_X

    #Fixed_101
    fixed=sparse.lil_matrix((1, len(fem_info&#91;9])),dtype="int32")
    print("check101:",fem_info&#91;9]&#91;0])
    if fem_info&#91;9]&#91;0] != -1:
        for i in range(len(fem_info&#91;9])):
            fixed&#91;0,i]=fem_info&#91;9]&#91;i]
        for i in range(len(fem_info&#91;9])):
            Um&#91;fixed&#91;0,i]*DOF_NODE+0]=True                   #Fixed_X
            Um&#91;fixed&#91;0,i]*DOF_NODE+2]=True                   #Fixed_Z

    #Fixed_110
    fixed=sparse.lil_matrix((1, len(fem_info&#91;10])),dtype="int32")
    print("check110:",fem_info&#91;10]&#91;0])
    if fem_info&#91;10]&#91;0] != -1:
        for i in range(len(fem_info&#91;10])):
            fixed&#91;0,i]=fem_info&#91;10]&#91;i]
        for i in range(len(fem_info&#91;10])):
            Um&#91;fixed&#91;0,i]*DOF_NODE+0]=True                   #Fixed_X
            Um&#91;fixed&#91;0,i]*DOF_NODE+1]=True                   #Fixed_Y

    #測定点Ａ
    #NODE
    point_a=sparse.lil_matrix((1, len(fem_info&#91;3])),dtype="int32")
    for i in range(len(fem_info&#91;3])):
        point_a&#91;0,i]=fem_info&#91;3]&#91;i]

    #測定点Ｏ
    point_o=sparse.lil_matrix((1, len(fem_info&#91;4])),dtype="int32")
    for i in range(len(fem_info&#91;4])):
        point_o&#91;0,i]=fem_info&#91;4]&#91;i]
    
    return x, y, z, connectivity, NODES, ELEMENTS, DOF_TOTAL, DOF_QUAD4, Um, point_a, point_o
    
    
# Dマトリクス
def make_D():
    coef = YOUNG / (1 - 2*POISSON) / (1 + POISSON)
    D_matrix=np.array(&#91;
        &#91;coef*(1-POISSON), coef*POISSON, coef*POISSON, 0, 0, 0],
        &#91;coef*POISSON, coef*(1-POISSON), coef*POISSON, 0, 0, 0],
        &#91;coef*POISSON, coef*POISSON, coef*(1-POISSON), 0, 0, 0],
        &#91;0, 0, 0, coef*(1-2*POISSON)/2, 0, 0],
        &#91;0, 0, 0, 0, coef*(1-2*POISSON)/2, 0],
        &#91;0, 0, 0, 0, 0, coef*(1-2*POISSON)/2]
        ])
    
    D = sparse.lil_matrix(D_matrix)
    return D

# 線膨張係数（ＣＴＥ）の行列
def make_CTE():
    CTE_T = np.array(&#91;&#91;LAMBDA, LAMBDA, LAMBDA, 0.0, 0.0, 0.0],          #T1
                      &#91;LAMBDA, LAMBDA, LAMBDA, 0.0, 0.0, 0.0],          #T2
                      &#91;LAMBDA, LAMBDA, LAMBDA, 0.0, 0.0, 0.0],          #T3
                      &#91;LAMBDA, LAMBDA, LAMBDA, 0.0, 0.0, 0.0],          #T4
                      ],dtype="float32")
    CTE = (1/4.0)*CTE_T.T                                               # 1/4*(T1+T2+T3+T4)

    return CTE

# Bマトリクス
def make_B():
    B = np.zeros((ELEMENTS, COMPONENTS, DOF_QUAD4),dtype="float32")
    Jmat = np.zeros((ELEMENTS, DOF_NODE, DOF_NODE),dtype="float32")  

    for e in range(ELEMENTS):
        x0, y0, z0 = x&#91;0, connectivity&#91;e,0]], y&#91;0, connectivity&#91;e,0]], z&#91;0, connectivity&#91;e,0]]
        x1, y1, z1 = x&#91;0, connectivity&#91;e,1]], y&#91;0, connectivity&#91;e,1]], z&#91;0, connectivity&#91;e,1]]
        x2, y2, z2 = x&#91;0, connectivity&#91;e,2]], y&#91;0, connectivity&#91;e,2]], z&#91;0, connectivity&#91;e,2]]
        x3, y3, z3 = x&#91;0, connectivity&#91;e,3]], y&#91;0, connectivity&#91;e,3]], z&#91;0, connectivity&#91;e,3]]

        #➀形状関数の正規化座標による偏微分
        # N1=1-a-b-c, N2=a, N3=b, N4=c 
        dN1da = -1.0; dN2da = 1.0; dN3da = 0.0; dN4da = 0.0
        dN1db = -1.0; dN2db = 0.0; dN3db = 1.0; dN4db = 0.0
        dN1dc = -1.0; dN2dc = 0.0; dN3dc = 0.0; dN4dc = 1.0

        #➁座標成分を正規化座標成分で偏微分
        dxda = dN1da*x0 + dN2da*x1 + dN3da*x2 + dN4da*x3
        dyda = dN1da*y0 + dN2da*y1 + dN3da*y2 + dN4da*y3
        dzda = dN1da*z0 + dN2da*z1 + dN3da*z2 + dN4da*z3
        dxdb = dN1db*x0 + dN2db*x1 + dN3db*x2 + dN4db*x3
        dydb = dN1db*y0 + dN2db*y1 + dN3db*y2 + dN4db*y3
        dzdb = dN1db*z0 + dN2db*z1 + dN3db*z2 + dN4db*z3
        dxdc = dN1dc*x0 + dN2dc*x1 + dN3dc*x2 + dN4dc*x3
        dydc = dN1dc*y0 + dN2dc*y1 + dN3dc*y2 + dN4dc*y3
        dzdc = dN1dc*z0 + dN2dc*z1 + dN3dc*z2 + dN4dc*z3

        # ➂ヤコビ行列Jmat
        Jmat&#91;e]=np.array(&#91;
                        &#91;dxda, dyda, dzda],
                        &#91;dxdb, dydb, dzdb],
                        &#91;dxdc, dydc, dzdc]
                        ])
        
        # ∂Ｎｉ／∂ａ、∂Ｎｉ／∂ｂ、∂Ｎｉ／∂ｃ
        dN1dabc = &#91;dN1da, dN1db, dN1dc]; dN2dabc = &#91;dN2da, dN2db, dN2dc]; dN3dabc = &#91;dN3da, dN3db, dN3dc]; dN4dabc = &#91;dN4da, dN4db, dN4dc]
        
        # ∂Ｎｉ／∂ｘ、∂Ｎｉ／∂ｙ、∂Ｎｉ／∂ｚ
        dN1dxyz = LA.solve(Jmat&#91;e], dN1dabc); dN2dxyz = LA.solve(Jmat&#91;e], dN2dabc); dN3dxyz = LA.solve(Jmat&#91;e], dN3dabc); dN4dxyz = LA.solve(Jmat&#91;e], dN4dabc)

        # 要素e番目の行列
        dN1dx = dN1dxyz&#91;0]; dN2dx = dN2dxyz&#91;0]; dN3dx = dN3dxyz&#91;0]; dN4dx = dN4dxyz&#91;0]
        dN1dy = dN1dxyz&#91;1]; dN2dy = dN2dxyz&#91;1]; dN3dy = dN3dxyz&#91;1]; dN4dy = dN4dxyz&#91;1]
        dN1dz = dN1dxyz&#91;2]; dN2dz = dN2dxyz&#91;2]; dN3dz = dN3dxyz&#91;2]; dN4dz = dN4dxyz&#91;2]
        
        B&#91;e] =  np.array(&#91;
                        &#91;dN1dx, 0.0, 0.0, dN2dx, 0.0, 0.0, dN3dx, 0.0, 0.0, dN4dx, 0.0, 0.0],
                        &#91;0.0, dN1dy, 0.0, 0.0, dN2dy, 0.0, 0.0, dN3dy, 0.0, 0.0, dN4dy, 0.0],
                        &#91;0.0, 0.0, dN1dz, 0.0, 0.0, dN2dz, 0.0, 0.0, dN3dz, 0.0, 0.0, dN4dz],
                        &#91;dN1dy, dN1dx, 0.0, dN2dy, dN2dx, 0.0, dN3dy, dN3dx, 0.0, dN4dy, dN4dx, 0.0],
                        &#91;0.0, dN1dz, dN1dy, 0.0, dN2dz, dN2dy, 0.0, dN3dz, dN3dy, 0.0, dN4dz, dN4dy],
                        &#91;dN1dz, 0.0, dN1dx, dN2dz, 0.0, dN2dx, dN3dz, 0.0, dN3dx, dN4dz, 0.0, dN4dx]
                        ])
        
    return B, Jmat

#  要素剛性マトリクス
def make_Ke():
    Ke= np.zeros((ELEMENTS,  DOF_QUAD4, DOF_QUAD4),dtype="float32") 
    for e in range(ELEMENTS):
        Ke&#91;e] = weight*B&#91;e].T @ D @ B&#91;e] * LA.det(Jmat&#91;e])

    return Ke

#要素温度変化荷重行列
def make_He():
    Hqu = np.zeros((NODE_QUAD4, NODE_QUAD4), dtype="float32")
    Huq = np.zeros((NODE_QUAD4, NODE_QUAD4), dtype="float32")
    C_mat = np.zeros((ELEMENTS, COMPONENTS, DOF_QUAD4), dtype="float32")

    #rev
    He = np.zeros((ELEMENTS, DOF_QUAD4, NODE_QUAD4), dtype="float32")

    for e in range(ELEMENTS):
        x0, y0, z0 = x&#91;0, connectivity&#91;e,0]], y&#91;0, connectivity&#91;e,0]], z&#91;0, connectivity&#91;e,0]]
        x1, y1, z1 = x&#91;0, connectivity&#91;e,1]], y&#91;0, connectivity&#91;e,1]], z&#91;0, connectivity&#91;e,1]]
        x2, y2, z2 = x&#91;0, connectivity&#91;e,2]], y&#91;0, connectivity&#91;e,2]], z&#91;0, connectivity&#91;e,2]]
        x3, y3, z3 = x&#91;0, connectivity&#91;e,3]], y&#91;0, connectivity&#91;e,3]], z&#91;0, connectivity&#91;e,3]]

        Huq = np.array(&#91;&#91;1.0, x0, y0, z0],
                        &#91;1.0, x1, y1, z1],
                        &#91;1.0, x2, y2, z2],
                        &#91;1.0, x3, y3, z3]
                       ])
        
        Hqu = LA.inv(Huq)

        C_mat&#91;e] = np.array(&#91;&#91;Hqu&#91;1,0], 0.0, 0.0, Hqu&#91;1,1], 0.0, 0.0, Hqu&#91;1,2], 0.0, 0.0, Hqu&#91;1,3], 0.0, 0.0],
                             &#91;0.0, Hqu&#91;2,0], 0.0, 0.0, Hqu&#91;2,1], 0.0, 0.0, Hqu&#91;2,2], 0.0, 0.0, Hqu&#91;2,3], 0.0],
                             &#91;0.0, 0.0, Hqu&#91;3,0], 0.0, 0.0, Hqu&#91;3,1], 0.0, 0.0, Hqu&#91;3,2], 0.0, 0.0, Hqu&#91;3,3]],
                             &#91;Hqu&#91;2,0], Hqu&#91;1,0], 0.0, Hqu&#91;2,1], Hqu&#91;1,1], 0.0, Hqu&#91;2,2], Hqu&#91;1,2], 0.0, Hqu&#91;2,3], Hqu&#91;1,3], 0.0],
                             &#91;0.0, Hqu&#91;3,0], Hqu&#91;2,0], 0.0, Hqu&#91;3,1], Hqu&#91;2,1], 0.0, Hqu&#91;3,2], Hqu&#91;2,2], 0.0, Hqu&#91;3,3], Hqu&#91;2,3]],
                             &#91;Hqu&#91;3,0], 0.0, Hqu&#91;1,0], Hqu&#91;3,1], 0.0, Hqu&#91;1,1], Hqu&#91;3,2], 0.0, Hqu&#91;1,2], Hqu&#91;3,3], 0.0, Hqu&#91;1,3]]
                            ])
        
        He&#91;e] = weight * C_mat&#91;e].T @ D @ CTE * LA.det(Huq)

    return He

#全体温度変化荷重行列
def make_H():
    #rev
    H = sparse.lil_matrix((DOF_TOTAL, NODES),dtype="float32")

    for e in range(ELEMENTS):
        for r in range(DOF_QUAD4):
            rt = (connectivity&#91;e, r // DOF_NODE])*DOF_NODE + (r%DOF_NODE)
            #rev
            for c in range(NODE_QUAD4):
                #rev
                ct = (connectivity&#91;e, c])
                H&#91;rt,ct] = H&#91;rt,ct] + He&#91;e,r,c]
    return H

# 全体剛性マトリクス
def make_K():
    K= sparse.lil_matrix((DOF_TOTAL, DOF_TOTAL),dtype="float32")

    for e in range(ELEMENTS):
        for r in range(DOF_QUAD4):
            rt = (connectivity&#91;e, r // DOF_NODE])*DOF_NODE + (r%DOF_NODE)
            for c in range(DOF_QUAD4):
                ct = (connectivity&#91;e, c // DOF_NODE])*DOF_NODE + (c%DOF_NODE)
                K&#91;rt,ct] = K&#91;rt,ct] + Ke&#91;e,r,c]
    return K

#境界条件処理
def set_baoudary():
    
    #拘束されている節点
    for r in range(DOF_TOTAL):
        if Um&#91;r] == True:
            K&#91;:,r] = 0.0
            K&#91;r,:] = 0.0
            H&#91;r,:] = 0.0

            K&#91;r,r] = 1.0 #対角成分を１

    return K, H


#測定ポイントに関係する感度情報

def make_W_xyz_0():
    #測定する節点(ゼロスタート)
    node_tool = point_a&#91;0,0]
    node_origin = point_o&#91;0,0]
    tool = np.zeros(3)
    origin = np.zeros(3)

    print("測定:node_tool---",node_tool," node_origin---",node_origin)

    tool&#91;0] = node_tool*DOF_NODE
    tool&#91;1] = node_tool*DOF_NODE+1
    tool&#91;2] = node_tool*DOF_NODE+2

    origin&#91;0] = node_origin*DOF_NODE
    origin&#91;1] = node_origin*DOF_NODE+1
    origin&#91;2] = node_origin*DOF_NODE+2

    K_csc = K.tocsc()
    H_csc = H.tocsc()

    return tool, origin, K_csc, H_csc

def make_W_xyz_i(count_A, ndim_A, p_i, DOF_TOTAL, K_csc, H_csc, tool, origin, array_Ax, array_Ay, array_Az):
    #W = np.zeros((DOF_NODE,NODES), dtype="float32")
    t_x, t_y, t_z = int(tool&#91;0]), int(tool&#91;1]), int(tool&#91;2])
    o_x, o_y, o_z = int(origin&#91;0]), int(origin&#91;1]), int(origin&#91;2])

    lu = splu(K_csc)

    for i in range(ndim_A):
        H1_csc = H_csc&#91;:,p_i*ndim_A+i]
        #H1_csc_T = H1_csc.T
        b = H1_csc.T.toarray()
        #print("b:", b&#91;0])
        x_ans = lu.solve(b&#91;0])
        array_Ax&#91;count_A.value] = x_ans&#91;t_x] - x_ans&#91;o_x]
        array_Ay&#91;count_A.value] = x_ans&#91;t_y] - x_ans&#91;o_y]
        array_Az&#91;count_A.value] = x_ans&#91;t_z] - x_ans&#91;o_z]
        count_A.value += 1

def make_W_xyz_end(count_F, ndim_A, ndim_F, p_i, DOF_TOTAL, NODES, K_csc, H_csc, tool, origin, array_Fx, array_Fy, array_Fz):
    #W_csc = sparse.csc_matrix((DOF_TOTAL,ndim_F//div), dtype="float32")
    t_x, t_y, t_z = int(tool&#91;0]), int(tool&#91;1]), int(tool&#91;2])
    o_x, o_y, o_z = int(origin&#91;0]), int(origin&#91;1]), int(origin&#91;2])

    lu = splu(K_csc)

    for i in range(ndim_F):
        H1_csc = H_csc&#91;:,p_i*ndim_A+i]
        b = H1_csc.T.toarray()
        x_ans = lu.solve(b&#91;0])
        array_Fx&#91;count_F.value] = x_ans&#91;t_x] - x_ans&#91;o_x]
        array_Fy&#91;count_F.value] = x_ans&#91;t_y] - x_ans&#91;o_y]
        array_Fz&#91;count_F.value] = x_ans&#91;t_z] - x_ans&#91;o_z]
        count_F.value += 1


#Paraviewフォーマットに値を出力
def outputvtk():

    # チェックしたいディレクトリの名前
    directory_name = "Results"

    # ディレクトリが存在するかチェック
    if not os.path.exists(f"{data_path}/{directory_name}"):
        # ディレクトリが存在しない場合は作成
        os.makedirs(f"{data_path}/{directory_name}")
        print(f"{directory_name} ディレクトリを作成しました。")
    else:
        # ディレクトリが既に存在する場合
        print(f"{directory_name} ディレクトリは既に存在します。")

    file_name = f"{data_path}/{directory_name}/{data_name.split('.')&#91;0]}.vtk"#"QUAD_4.vtk"
    f_path = pathlib.Path(__file__).parent.resolve() / file_name 

    with open(f_path, mode = "w") as f:
        
        #Header出力
        print("# vtk DataFile Version 2.0",file=f)
        print("Header",file=f)
        print("ASCII",file=f)
        print("DATASET UNSTRUCTURED_GRID",file=f)
        print(" ",file=f)
        
        #節点座標出力
        print("POINTS", NODES, " double",file=f)
        for i in range(NODES):
            print(x&#91;0,i]," ",y&#91;0,i]," ",z&#91;0,i],file=f)
        print(" ",file=f)
        
        #要素構成節点番号出力
        print("CELLS", ELEMENTS, ELEMENTS*5,file=f)
        for i in range(ELEMENTS):
            print(4," ",end="",file=f)
            for j in range(NODE_QUAD4):
                print(connectivity&#91;i,j]," ",end="",file=f)
            print("",file=f)
        print(" ",file=f)
        
        #要素タイプ出力
        print("CELL_TYPES", ELEMENTS,file=f)
        for i in range(ELEMENTS):
            print(10,file=f)
        print(" ",file=f)
        
        #節点応力出力
        print("POINT_DATA", NODES,file=f)
        print(" ",file=f)
        
        #節点変位出力
        print("VECTORS Displacement float",file=f)
        for i in range(NODES):
            print(W_x&#91;i]," ",W_y&#91;i]," ",W_z&#91;i],file=f)
            
        print(" ",file=f)

if __name__ == "__main__":

    number_of_cpus = cpu_count()
    print(f"cpu_count:{number_of_cpus}")

    #計測開始
    t1 = time.time()
    #初期化
    x, y, z, connectivity, NODES, ELEMENTS, DOF_TOTAL, DOF_QUAD4, Um, point_a, point_o =  initialize()

    #Dマトリクス --- ok
    D = make_D()
    print("*** PASS_make_D ***")

    #Bマトリクス --- ok
    B, Jmat = make_B()
    print("*** PASS_make_B ***")

    #CTE（線膨張係数）マトリクス
    CTE = make_CTE()
    print("*** PASS_make_CTE ***")

    #要素温度変化荷重行列
    He = make_He()
    print("*** PASS_make_He ***")

    #全体温度変化荷重行列
    H = make_H()
    with open("H.txt", "w", encoding="utf-8") as f:
        f.write(str(H))
    print("*** PASS_make_H ***")

    #要素剛性行列 --- ok
    Ke = make_Ke()
    print("*** PASS_make_Ke ***")

    #全体剛性行列 --- ok
    K = make_K()
    print("*** PASS_make_K ***")

    del He
    del Ke
    del B
    del CTE
    del Jmat
    gc.collect

    #境界条件処理
    K, H = set_baoudary()
    print("*** PASS_set_boundary_U_F ***")

    t2 = time.time()
    elapsed_time = t2 - t1
    print(f"経過時間：{elapsed_time}")

    #測定ポイントに関係する感度情報

    # 計算のための準備
    tool, origin, K_csc, H_csc = make_W_xyz_0()
    del K, H

    ndim_A = NODES // core
    t_x, t_y, t_z = int(tool&#91;0]), int(tool&#91;1]), int(tool&#91;2])
    o_x, o_y, o_z = int(origin&#91;0]), int(origin&#91;1]), int(origin&#91;2])


    # 共有メモリの作成
    # Valueオブジェクトの生成
    count_List = &#91;]
    for i_ in range(core): 
        count_List.append( Value('i', 0) )

    # Arrayオブジェクトの生成
    array_x_List = &#91;]; array_y_List = &#91;]; array_z_List = &#91;]
    p_List = &#91;]
    for i_ in range(core):
        if i_ != core-1:
            array_x_List.append( Array('f', ndim_A) )
            array_y_List.append( Array('f', ndim_A) )
            array_z_List.append( Array('f', ndim_A) )
            p_List.append( multiprocessing.Process(target=make_W_xyz_i, args=(count_List&#91;i_], ndim_A, i_, DOF_TOTAL, K_csc, H_csc, tool, origin, array_x_List&#91;i_], array_y_List&#91;i_], array_z_List&#91;i_] )) )
        else:
            ndim_F = NODES-(core-1)*ndim_A
            array_x_List.append( Array('f', ndim_F) )
            array_y_List.append( Array('f', ndim_F) )
            array_z_List.append( Array('f', ndim_F) )
            #p_List.append( multiprocessing.Process(target=make_W_xyz_end, args=(count_List&#91;i_], ndim_A, i_, div, DOF_TOTAL, NODES, K_csc, H_csc, tool, origin, array_x_List&#91;i_], array_y_List&#91;i_], array_z_List&#91;i_] ))  )    
            p_List.append( multiprocessing.Process(target=make_W_xyz_end, args=(count_List&#91;i_], ndim_A, ndim_F, i_, DOF_TOTAL, NODES, K_csc, H_csc, tool, origin, array_x_List&#91;i_], array_y_List&#91;i_], array_z_List&#91;i_])) )
    #p.start()
    for i_ in range(core):
        p_List&#91;i_].start()

    #p.join()
    for i_ in range(core):
        p_List&#91;i_].join()  
   
    #共有メモリの統合
    W_x = &#91;]; W_y = &#91;]; W_z = &#91;]

    for i_ in range(core):
        W_x.extend( array_x_List&#91;i_] )
        W_y.extend( array_y_List&#91;i_] )
        W_z.extend( array_z_List&#91;i_] )

    #Vtk出力
    outputvtk()
    
    #計測終了
    t3 = time.time()
    elapsed_time = t3 - t1
    print(f"経過時間：{elapsed_time}")