import numpy as np
import numpy.linalg as LA
import pandas as pd
import pathlib
#import Data_import_lib.Data_import as di
import Data_import_lib

#from pyevtk.hl import pointsToVTK
import gc
#import dask
#import dask.array as da

import time

from scipy import sparse
from scipy.sparse.linalg import inv


#FC300
#THICKNESS = 0.1                                             #要素の厚さ
YOUNG = 130000.0                                            #ヤング率(MPa)
POISSON = 0.27                                               #ポアソン比
LAMBDA = 11.9                                               #線膨張係数（/K）

NODE_TRIA3 = 4                                              #要素の接点数
COMPONENTS = 6                                              #ひずみと応力の成分数
DOF_NODE = 3                                                #接点自由度
weight = 1.0 / 6.0                                          #積分点の重み係数


#荷重条件
Fx = -100.0                                                    #荷重（X方向）
Fy = 0.0                                                    #荷重（Y方向）
Fz = 0.0                                                    #荷重（Z方向）
BX = 0.0                                                    #物体力（X方向）
BY = 0.0                                                    #物体力（Y方向）
BZ = 0.0                                                    #物体力（Z方向）
face_px = 0.0                                               #表面力（X方向）
face_py = 1.0                                               #表面力（Y方向）
face_pz = 0.0                                               #表面力（Ｚ方向）

inpfileName = "Quad4_FEM_00.inp"                            #inpファイル名

# 初期状態
def initialize():
    #FEMモデル情報取得（Node,Element）
    fem_info= Data_import_lib.Data_import.data_import(inpfileName)
    
    #[0]:node, [1]:element, [2]:fixed, [3]:face_load [4]:face_load_element [5]:foece
    #モジュール定数
    NODES=len(fem_info[0])                                          #全節点数
    ELEMENTS=len(fem_info[1])                                       #全要素数
    DOF_TOTAL = DOF_NODE * NODES                                    #モデル全体の自由度
    DOF_TRIA3 = NODE_TRIA3 * DOF_NODE                               #要素自由度
    
    #モジュールレベル変数
    #x=np.zeros((NODES),dtype="float32")                                               #接点のＸ座標配列
    x=sparse.lil_matrix((1, NODES), dtype="float32")
    #y=np.zeros((NODES),dtype="float32")                                               #接点のＹ座標配列
    y=sparse.lil_matrix((1, NODES), dtype="float32")
    #z=np.zeros((NODES),dtype="float32")                                               #節点のＺ座標配列
    z=sparse.lil_matrix((1,NODES), dtype="float32")
    #Input Data
    for i in range(NODES):
        x[0,i]=fem_info[0][i][1]
        y[0,i]=fem_info[0][i][2]
        z[0,i]=fem_info[0][i][3]
        #print("NODE:",i,"x:",x[0,i],"y:",y[0,i]) #--- ok
        
    #要素内節点順配列
    #connectivity=np.zeros((ELEMENTS,NODE_TRIA3),dtype="int32")
    connectivity=sparse.lil_matrix((ELEMENTS, NODE_TRIA3),dtype="int32")      
    #Input Data
    for e in range(ELEMENTS):
        for i in range(NODE_TRIA3):
            connectivity[e,i]=fem_info[1][e][i+1]
        #print("ELEMENT:",e,"POINT(",connectivity[e],")") #--- ok
    
    #拘束点（X＝Y＝0とする）
    #fixed=np.zeros(len(fem_info[2]),dtype="int32")
    fixed=sparse.lil_matrix((1, len(fem_info[2])),dtype="int32")
    for i in range(len(fem_info[2])):
        fixed[0,i]=fem_info[2][i]
        #print("***fixed***:",fixed[0,i])

    #U=np.zeros(DOF_TOTAL,dtype="int32")
    U = sparse.lil_matrix((1, DOF_TOTAL), dtype="int32")
    Um=np.zeros(DOF_TOTAL,dtype="bool")
    for i in range(len(fem_info[2])):
        #for j in range(len(fem_info[2][1])):
        for k in range(DOF_NODE):
            Um[fixed[0,i]*DOF_NODE+k]=True                   #拘束されているｘ、ｙ、ｚをＴｒｕｅとする（全体行列系に）
            #print(f"***fixed_NODE:{fixed[0,i]*DOF_NODE+k}***:",fixed[0,i])
    
    #外力_1(１節点のみ)
    #force=np.zeros(len(fem_info[5]),dtype="int32")
    force=sparse.lil_matrix((1, len(fem_info[3])),dtype="int32")
    for i in range(len(fem_info[3])):
        force[0,i]=fem_info[3][i]
        print("***force***:",force[0,i])
    
    #表面力
    #face_load=np.zeros(len(fem_info[3]),dtype="int32")
    face_load=sparse.lil_matrix((1, len(fem_info[4])),dtype="int32")
    for i in range(len(fem_info[4])):
        face_load[0,i]=fem_info[4][i]
        #print("***face_load***:",face_load[0,i])

    

    #Face_ELEMENT
    #face_load_element=np.zeros(len(fem_info[4]),dtype="int32")
    face_load_element=sparse.lil_matrix((1, len(fem_info[5])),dtype="int32")
    for i in range(len(fem_info[5])):
        face_load[0,i]=fem_info[5][i]
        #print("***face_load_element***:",face_load_element[0,i])

    return x, y, z, connectivity, NODES, ELEMENTS, DOF_TOTAL, DOF_TRIA3, U, Um, force, face_load, face_load_element
    
    
# Dマトリクス
def make_D():
    #D=np.zeros((COMPONENTS, COMPONENTS),dtype="float32")
    #coef = YOUNG / (1 - 2*POISSON) / (1 + POISSON)
    #D=np.array([
    #            [coef*(1-POISSON), coef*POISSON, coef*POISSON, 0, 0, 0],
    #            [coef*POISSON, coef*(1-POISSON), coef*POISSON, 0, 0, 0],
    #            [coef*POISSON, coef*POISSON, coef*(1-POISSON), 0, 0, 0],
    #            [0, 0, 0, coef*(1-2*POISSON)/2, 0, 0],
    #            [0, 0, 0, 0, coef*(1-2*POISSON)/2, 0],
    #            [0, 0, 0, 0, 0, coef*(1-2*POISSON)/2]
    #])

    coef = YOUNG / (1.0 - 2.0*POISSON) / (1.0 + POISSON)
    D_matrix=([
        [coef*(1.0-POISSON), coef*POISSON, coef*POISSON, 0.0, 0.0, 0.0],
        [coef*POISSON, coef*(1.0-POISSON), coef*POISSON, 0.0, 0.0, 0.0],
        [coef*POISSON, coef*POISSON, coef*(1.0-POISSON), 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, coef*(1.0-2.0*POISSON)/2.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, coef*(1.0-2.0*POISSON)/2.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, coef*(1.0-2.0*POISSON)/2.0]
        ])
    
    D = sparse.lil_matrix(D_matrix)
    return D

# Bマトリクス
def make_B():
    B = np.zeros((ELEMENTS, COMPONENTS, DOF_TRIA3),dtype="float32")
    Jmat = np.zeros((ELEMENTS, DOF_NODE, DOF_NODE),dtype="float32")  

    for e in range(ELEMENTS):
        x0, y0, z0 = x[0, connectivity[e,0]], y[0, connectivity[e,0]], z[0, connectivity[e,0]]
        x1, y1, z1 = x[0, connectivity[e,1]], y[0, connectivity[e,1]], z[0, connectivity[e,1]]
        x2, y2, z2 = x[0, connectivity[e,2]], y[0, connectivity[e,2]], z[0, connectivity[e,2]]
        x3, y3, z3 = x[0, connectivity[e,3]], y[0, connectivity[e,3]], z[0, connectivity[e,3]]
        #print(f"x0:{x0}, y0:{y0}, z0:{z0}")

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
        Jmat[e]=np.array([
                        [dxda, dyda, dzda],
                        [dxdb, dydb, dzdb],
                        [dxdc, dydc, dzdc]
                        ])
        
        # ∂Ｎｉ／∂ａ、∂Ｎｉ／∂ｂ、∂Ｎｉ／∂ｃ
        dN1dabc = [dN1da, dN1db, dN1dc]; dN2dabc = [dN2da, dN2db, dN2dc]; dN3dabc = [dN3da, dN3db, dN3dc]; dN4dabc = [dN4da, dN4db, dN4dc]
        
        # ∂Ｎｉ／∂ｘ、∂Ｎｉ／∂ｙ、∂Ｎｉ／∂ｚ
        dN1dxyz = LA.solve(Jmat[e], dN1dabc); dN2dxyz = LA.solve(Jmat[e], dN2dabc); dN3dxyz = LA.solve(Jmat[e], dN3dabc); dN4dxyz = LA.solve(Jmat[e], dN4dabc)

        # 要素e番目の行列
        dN1dx = dN1dxyz[0]; dN2dx = dN2dxyz[0]; dN3dx = dN3dxyz[0]; dN4dx = dN4dxyz[0]
        dN1dy = dN1dxyz[1]; dN2dy = dN2dxyz[1]; dN3dy = dN3dxyz[1]; dN4dy = dN4dxyz[1]
        dN1dz = dN1dxyz[2]; dN2dz = dN2dxyz[2]; dN3dz = dN3dxyz[2]; dN4dz = dN4dxyz[2]
        
        B[e] =  np.array([
                        [dN1dx, 0.0, 0.0, dN2dx, 0.0, 0.0, dN3dx, 0.0, 0.0, dN4dx, 0.0, 0.0],
                        [0.0, dN1dy, 0.0, 0.0, dN2dy, 0.0, 0.0, dN3dy, 0.0, 0.0, dN4dy, 0.0],
                        [0.0, 0.0, dN1dz, 0.0, 0.0, dN2dz, 0.0, 0.0, dN3dz, 0.0, 0.0, dN4dz],
                        [0.0, dN1dz, dN1dy, 0.0, dN2dz, dN2dy, 0.0, dN3dz, dN3dy, 0.0, dN4dz, dN4dy],
                        [dN1dz, 0.0, dN1dx, dN2dz, 0.0, dN2dx, dN3dz, 0.0, dN3dx, dN4dz, 0.0, dN4dx],
                        [dN1dy, dN1dx, 0.0, dN2dy, dN2dx, 0.0, dN3dy, dN3dx, 0.0, dN4dy, dN4dx, 0.0]
                        ])
        # print("Pass:", e)
        
    """
    print("==============  Bマトリクス ========================")
    for e in range(ELEMENTS):
        print(f"======= 要素{e}番目==========")
        print(f"         B[{e}] = {B[e]}")
    """
    return B, Jmat
    #return B, volume_elements
    
#  要素剛性マトリクス
def make_Ke():
    Ke= np.zeros((ELEMENTS,  DOF_TRIA3, DOF_TRIA3),dtype="float32") 
    for e in range(ELEMENTS):
        Ke[e] = weight*B[e].T @ D @ B[e] * LA.det(Jmat[e])
        #print(Ke[e])
    
    return Ke

# 全体剛性マトリクス
def make_K():
    #K= np.zeros((DOF_TOTAL, DOF_TOTAL),dtype="float32")
    K= sparse.lil_matrix((DOF_TOTAL, DOF_TOTAL),dtype="float32")
    print(id(Ke))
    for e in range(ELEMENTS):
        for r in range(DOF_TRIA3):
            rt = ((connectivity[e, r // DOF_NODE]+1)*DOF_NODE-((r+1)%DOF_NODE))-1
            #print("rt:",rt)
            for c in range(DOF_TRIA3):
                ct = ((connectivity[e, c // DOF_NODE]+1)*DOF_NODE-((c+1)%DOF_NODE))-1
                K[rt,ct] = K[rt,ct] + Ke[e,r,c]

    return K
    

#荷重
def calc_force_tria3():
    #F=np.zeros(DOF_TOTAL,dtype="float32")
    F=sparse.lil_matrix((1, DOF_TOTAL),dtype="float32")

    #for i in range(DOF_TOTAL):
    #    F[0, i] = 0.0

    #note: forceは１点としている
    F[0, force[0,0]*DOF_NODE] += Fx    
    F[0, force[0,0]*DOF_NODE+1] += Fy
    F[0, force[0,0]*DOF_NODE+2] += Fz

    return F


#物体力 *** 未完成　***
def calc_body_force_tria3(U):
    for e in range(ELEMENTS):        
        for m in range(NODE_TRIA3):
            n = connectivity[e, m]
            F[n * 2] = F[n * 2] + THICKNESS* area_elements[e]/ 3* BX
            F[(n * 2)+1] = F[(n * 2)+1] + THICKNESS* area_elements[e]/ 3* BY

    return F


#表面力　***　未完成　***
def calc_surface_force_tria3():
    #表面力が作用している辺を調べる・・・節点が含まれない条件で辺を検知
    #print(face_load_element)
    for i, e in enumerate(face_load_element):
        if not connectivity[e,0] in face_load:
            na = connectivity[e, 1]
            nb = connectivity[e, 2]
            print("e:",e,"edge2")
        if not connectivity[e,1] in face_load:
            na = connectivity[e, 2]
            nb = connectivity[e, 0]
            print("e:",e,"edge3")
        if not connectivity[e,2] in face_load:
            na = connectivity[e, 0]
            nb = connectivity[e, 1]
            print("e:",e,"edge1")
        
        xa = x[na]; ya = y[na]
        xb = x[nb]; yb = y[nb]
        edge_length = np.sqrt((xa - xb) * (xa - xb) + (ya - yb) * (ya - yb))
        fx = face_px * edge_length / 2
        fy = face_py * edge_length / 2
        
        F[na * 2] = F[na * 2] + fx
        F[(na * 2)+1] = F[(na * 2)+1] + fy
        F[nb * 2] = F[nb * 2] + fx
        F[(nb * 2)+1] = F[(nb * 2)+1] + fy
        
    return F

#境界条件処理
def set_baoudary_U_F():
    
    # 全体行列をコピー
    #Kc = sparse.lil_matrix.copy(K)

    for r in range(DOF_TOTAL):
        if Um[r] == True:
            for rr in range(DOF_TOTAL): # 変位拘束が存在する行の成分を０にする
                if rr != r:
                    F[0, rr] -= K[rr,r]*U[0, r]                    
            for rr in range(DOF_TOTAL):
                K[rr,r] = 0.0
            for cc in range(DOF_TOTAL): # 変位拘束が存在する列の成分を０にする
                K[r,cc] = 0.0

            K[r,r] = 1.0 #対角成分を１

            #F[r] = U[r]
            F[0, r] = U[0, r]

    return U, F ,K

#逆行列を求める（ＣＳＣ形式）
def to_csc():
    K_csc = K.tocsc()
    F_csc = F.tocsc()
    Inv_K_csc = inv(K_csc)    
    FT_csc = F_csc.T

    del K_csc
    del F_csc
    gc.collect

    return Inv_K_csc, FT_csc

#逆行列で計算
def solve():

    #K_csc = K.tocsc()
    #F_csc = F.tocsc()

    #Ua=inv(K_csc)@F_csc.T
    Ua=Inv_K_csc@FT_csc

    #Ua = LA.inv(Kc) @ F
    
    
    return Ua

#Paraviewフォーマットに値を出力
def outputvtk():
    file_name = f"{inpfileName[-4:]}_TRIA_3.vtk"
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
            print(x[0,i]," ",y[0,i]," ",z[0,i],file=f)
        print(" ",file=f)
        
        #要素構成節点番号出力
        print("CELLS", ELEMENTS, ELEMENTS*5,file=f)
        for i in range(ELEMENTS):
            print(4," ",end="",file=f)
            for j in range(NODE_TRIA3):
                print(connectivity[i,j]," ",end="",file=f)
            print("",file=f)
        print(" ",file=f)
        
        #要素タイプ出力
        print("CELL_TYPES", ELEMENTS,file=f)
        for i in range(ELEMENTS):
            print(10,file=f)
        print(" ",file=f)
        
        #節点応力出力
        print("POINT_DATA", NODES,file=f)
        #print("SCALARS Sx float 1",file=f)
        #print("LOOKUP_TABLE default",file=f)
        #for i in range(NODES):
        #    print(stress_node[i,0],file=f)
        print(" ",file=f)
        
        #節点変位出力
        print("VECTORS Displacement float",file=f)
        for i in range(NODES):
            print(Ua[i*DOF_NODE,0]," ",Ua[i*DOF_NODE+1,0]," ",Ua[i*DOF_NODE+2,0],file=f)
        print(" ",file=f)




if __name__ == "__main__":
    #計測開始
    t1 = time.time()
    #初期化
    x, y, z, connectivity, NODES, ELEMENTS, DOF_TOTAL, DOF_TRIA3, U, Um, force, face_load, face_load_element=  initialize()
    #print("conectivity: ", connectivity[0])

    #Dマトリクス --- ok
    D = make_D()
    print("*** PASS_make_D ***")

    #Bマトリクス --- ok
    B, Jmat = make_B()
    print("*** PASS_make_B ***")

    #要素剛性行列 --- ok
    Ke = make_Ke()
    print(id(Ke))
    print("*** make_Ke ***")


    #全体剛性行列 --- ok
    K = make_K()
    print("*** PASS_make_K ***")

    # === K比較用ドライバ 追加分 ===
    # 生K（境界条件適用前）を保存。tocsr()でコピーされるので後段の in-place 変更に影響されない
    from scipy import sparse as _sp
    _sp.save_npz("K_python_raw.npz", K.tocsr())
    print("*** saved K_python_raw.npz ***")

    #荷重（set_baoudary_U_F が F を使うため必要）
    F = calc_force_tria3()
    print("*** PASS_calc_force_tria3 ***")

    #境界条件処理 → K は BC適用後になる
    U, F, K = set_baoudary_U_F()
    print("*** PASS_set_boundary_U_F ***")

    # BC適用後K を保存（FrontISTR K_bc.csr と比較する対象）
    _sp.save_npz("K_python_bc.npz", K.tocsr())
    print("*** saved K_python_bc.npz ***")
    # 重い to_csc/solve/outputvtk はスキップ（K比較には不要）

    #計測終了
    t2 = time.time()

    elapsed_time = t2 - t1
    print(f"経過時間：{elapsed_time}")


