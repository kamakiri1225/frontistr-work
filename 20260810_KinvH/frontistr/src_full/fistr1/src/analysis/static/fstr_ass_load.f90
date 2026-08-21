!-------------------------------------------------------------------------------
! Copyright (c) 2019 FrontISTR Commons
! This software is released under the MIT License, see LICENSE.txt
!-------------------------------------------------------------------------------
!> \brief  This module provides functions to take into account external load

module m_fstr_ass_load
  use m_fstr
  use m_static_lib
  use m_fstr_precheck
  use m_fstr_elemact
  use mMechGauss
  use mReadTemp
  use mULoad
  use m_fstr_spring
  use m_common_struct
  use m_utilities
  
  implicit none
  
contains
  !
  !======================================================================!
  !> This subroutine assmble following external force into fstrSOLID%GL and hecMAT%B afterwards
  !>  -#  concentrated nodal force
  !>  -#  surface pressure
  !>  -#  volume force
  !>  -#  thermal force

  subroutine fstr_ass_load(cstep, ctime, hecMESH, hecMAT, fstrSOLID, fstrPARAM)
    !======================================================================!
    integer(kind=kint), intent(in)       :: cstep !< current step
    real(kind=kreal), intent(in)         :: ctime  !< target time
    type(hecmwST_matrix), intent(inout)  :: hecMAT !< hecmw matrix
    type(hecmwST_local_mesh), intent(in) :: hecMESH !< hecmw mesh
    type(fstr_solid), intent(inout)      :: fstrSOLID !< fstr_solid
    type(fstr_param), intent(inout)      :: fstrPARAM !< analysis control parameters

    ! Initialize the global load vector
    fstrSOLID%GL(:) = 0.0d0
    fstrSOLID%EFORCE(:) = 0.0d0

    ! Process concentrated nodal forces (CLOAD)
    call process_concentrated_loads(cstep, ctime, hecMESH, fstrSOLID)
    
    ! Process distributed loads (DLOAD) - surface pressure and volume force
    call process_distributed_loads(cstep, ctime, hecMESH, fstrSOLID)
    
    ! Process user-defined loads
    call process_user_loads(cstep, fstrSOLID)
    
    ! Update global load vector
    call hecmw_update_R(hecMESH, fstrSOLID%GL, hecMESH%n_node, hecMESH%n_dof)
    
    ! Update right-hand side vector
    call hecmw_mat_clear_b(hecMAT)
    call update_rhs_vector(hecMESH, hecMAT, fstrSOLID)
    
    ! Process thermal loads (TLOAD)
    call process_thermal_loads(cstep, ctime, hecMESH, hecMAT, fstrSOLID)
    
    ! Process spring forces
    call fstr_Update_NDForce_spring(cstep, hecMESH, fstrSOLID, hecMAT%B)
    
  end subroutine fstr_ass_load

  !======================================================================!
  !> Process concentrated nodal forces (CLOAD)
  !======================================================================!
  subroutine process_concentrated_loads(cstep, ctime, hecMESH, fstrSOLID)
    integer(kind=kint), intent(in)       :: cstep
    real(kind=kreal), intent(in)         :: ctime
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(fstr_solid), intent(inout)      :: fstrSOLID
    
    integer(kind=kint) :: n_rot, rid, n_nodes, idof, ndof
    integer(kind=kint) :: ig0, ig, ityp, iS0, iE0, ik, in, grpid, jj_n_amp
    real(kind=kreal)   :: factor, fval, tval
    real(kind=kreal)   :: normal(3), direc(3), ccoord(3), cdisp(3), cdiff(3)
    real(kind=kreal)   :: vect(60)
    type(tRotInfo)     :: rinfo
    
    ndof = hecMESH%n_dof

    ! Initialize rotation information for torque loads
    n_rot = fstrSOLID%CLOAD_ngrp_rot
    if (n_rot > 0) call fstr_RotInfo_init(n_rot, rinfo)

    ! Process all concentrated loads
    do ig0 = 1, fstrSOLID%CLOAD_ngrp_tot
      grpid = fstrSOLID%CLOAD_ngrp_GRPID(ig0)
      if (.not. fstr_isLoadActive(fstrSOLID, grpid, cstep)) cycle
      jj_n_amp = fstrSOLID%CLOAD_ngrp_amp(ig0)
      if (jj_n_amp <= 0) then  ! Amplitude not defined
        factor = fstrSOLID%FACTOR(2)
      else
        call table_amp(hecMESH, fstrSOLID, cstep, jj_n_amp, ctime, factor)
      endif
      
      if (fstr_isLoadActive(fstrSOLID, grpid, cstep-1)) factor = 1.0d0
      ig = fstrSOLID%CLOAD_ngrp_ID(ig0)
      ityp = fstrSOLID%CLOAD_ngrp_DOF(ig0)
      fval = fstrSOLID%CLOAD_ngrp_val(ig0)
      iS0 = hecMESH%node_group%grp_index(ig-1) + 1
      iE0 = hecMESH%node_group%grp_index(ig)

      if( fstrSOLID%CLOAD_ngrp_rotID(ig0) > 0 ) then ! setup torque load information
        rid = fstrSOLID%CLOAD_ngrp_rotID(ig0)
        if (.not. rinfo%conds(rid)%active) then
          rinfo%conds(rid)%active = .true.
          rinfo%conds(rid)%center_ngrp_id = fstrSOLID%CLOAD_ngrp_centerID(ig0)
          rinfo%conds(rid)%torque_ngrp_id = ig
        endif
        if (ityp > ndof) ityp = ityp - ndof
        rinfo%conds(rid)%vec(ityp) = factor * fval
        cycle
      endif

      do ik = iS0, iE0
        in = hecMESH%node_group%grp_item(ik)
        fstrSOLID%GL(ndof*(in-1)+ityp) = fstrSOLID%GL(ndof*(in-1)+ityp) + factor*fval
      enddo
    enddo

    !Add torque load to fstrSOLID%GL
    do rid = 1, n_rot
      if (.not. rinfo%conds(rid)%active) cycle
      ! Get number of slave nodes
      n_nodes = hecmw_ngrp_get_number(hecMESH, rinfo%conds(rid)%torque_ngrp_id)

      ! Get center node
      ig = rinfo%conds(rid)%center_ngrp_id
      do idof = 1, ndof
        ccoord(idof) = hecmw_ngrp_get_totalvalue(hecMESH, ig, ndof, idof, hecMESH%node)
        cdisp(idof) = hecmw_ngrp_get_totalvalue(hecMESH, ig, ndof, idof, fstrSOLID%unode)
        cdisp(idof) = cdisp(idof) + hecmw_ngrp_get_totalvalue(hecMESH, ig, ndof, idof, fstrSOLID%dunode)
      enddo
      ccoord(1:ndof) = ccoord(1:ndof) + cdisp(1:ndof)

      tval = dsqrt(dot_product(rinfo%conds(rid)%vec(1:ndof), rinfo%conds(rid)%vec(1:ndof)))
      if (tval < 1.d-16) then
        write(*,*) '###ERROR### : norm of torque vector must be > 0.0'
        call hecmw_abort(hecmw_comm_get_comm())
      endif
      normal(1:ndof) = rinfo%conds(rid)%vec(1:ndof) / tval
      tval = tval / dble(n_nodes)

      ig = rinfo%conds(rid)%torque_ngrp_id
      iS0 = hecMESH%node_group%grp_index(ig-1) + 1
      iE0 = hecMESH%node_group%grp_index(ig)
      do ik = iS0, iE0
        in = hecMESH%node_group%grp_item(ik)
        cdiff(1:ndof) = hecMESH%node(ndof*(in-1)+1:ndof*in) + fstrSOLID%unode(ndof*(in-1)+1:ndof*in) &
          & + fstrSOLID%dunode(ndof*(in-1)+1:ndof*in) - ccoord(1:ndof)
        call cross_product(normal,cdiff,vect(1:ndof))
        fval = dot_product(vect(1:ndof), vect(1:ndof))
        if (fval < 1.d-16) then
          write(*,*) '###ERROR### : torque node is at the same position as that of center node in rotational surface.'
          call hecmw_abort(hecmw_comm_get_comm())
        endif
        vect(1:ndof) = (tval/fval) * vect(1:ndof)
        fstrSOLID%GL(ndof*(in-1)+1:ndof*in) = fstrSOLID%GL(ndof*(in-1)+1:ndof*in) + vect(1:ndof)
      enddo
    enddo
    if (n_rot > 0) call fstr_RotInfo_finalize(rinfo)
    
  end subroutine process_concentrated_loads
    !
    ! -------------------------------------------------------------------
    !  DLOAD
    ! -------------------------------------------------------------------
  subroutine process_distributed_loads(cstep, ctime, hecMESH, fstrSOLID)
    integer(kind=kint), intent(in)       :: cstep
    real(kind=kreal), intent(in)         :: ctime
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(fstr_solid), intent(inout)      :: fstrSOLID
    
    integer(kind=kint) :: ndof, ig0, ig, ltype, iS0, iE0, ik, icel, ic_type, nn, is
    integer(kind=kint) :: isect, id, iset, ihead, nsize, grpid, i, j, jj_n_amp
    integer(kind=kint) :: iwk(60), nodLocal(20)
    real(kind=kreal)   :: xx(20), yy(20), zz(20), vect(60), params(0:6)
    real(kind=kreal)   :: factor, rho, thick, pa1
    logical            :: fg_surf
    type(tMaterial), pointer :: material
    
    ndof = hecMESH%n_dof
    
    do ig0 = 1, fstrSOLID%DLOAD_ngrp_tot
      grpid = fstrSOLID%DLOAD_ngrp_GRPID(ig0)
      if (.not. fstr_isLoadActive(fstrSOLID, grpid, cstep)) cycle
      jj_n_amp = fstrSOLID%DLOAD_ngrp_amp(ig0)
      if (jj_n_amp <= 0) then  ! Amplitude not defined
        factor = fstrSOLID%factor(2)
      else
        call table_amp(hecMESH, fstrSOLID, cstep, jj_n_amp, ctime, factor)
      endif
      
      if (fstr_isLoadActive(fstrSOLID, grpid, cstep-1)) factor = 1.0d0
      ig = fstrSOLID%DLOAD_ngrp_ID(ig0)
      ltype = fstrSOLID%DLOAD_ngrp_LID(ig0)
      do i = 0, 6
        params(i) = fstrSOLID%DLOAD_ngrp_params(i, ig0)
      enddo
      ! ----- START & END
      fg_surf = (ltype == 100)
      if( fg_surf ) then                  ! surface group
        iS0 = hecMESH%surf_group%grp_index(ig-1) + 1
        iE0 = hecMESH%surf_group%grp_index(ig)
      else                                ! element group
        iS0 = hecMESH%elem_group%grp_index(ig-1) + 1
        iE0 = hecMESH%elem_group%grp_index(ig)
      endif
      do ik = iS0, iE0
        if( fg_surf ) then                ! surface group
          ltype = hecMESH%surf_group%grp_item(2*ik) * 10
          icel = hecMESH%surf_group%grp_item(2*ik-1)
          ic_type = hecMESH%elem_type(icel)
        else                              ! element group
          icel = hecMESH%elem_group%grp_item(ik)
          ic_type = hecMESH%elem_type(icel)
        endif

        !ELEMENT ACTIVATION
        if( fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE ) cycle

        if (hecmw_is_etype_link(ic_type)) cycle
        if (hecmw_is_etype_patch(ic_type)) cycle
        ! if( ic_type==3422 ) ic_type=342
        nn = hecmw_get_max_node(ic_type)
        ! ----- node ID
        is = hecMESH%elem_node_index(icel-1)
        if (fstrSOLID%DLOAD_follow == 0) then
          do j = 1, nn
            nodLOCAL(j) = hecMESH%elem_node_item (is+j)
            ! ----- nodal coordinate
            xx(j) = hecMESH%node( 3*nodLOCAL(j)-2 )
            yy(j) = hecMESH%node( 3*nodLOCAL(j)-1 )
            zz(j) = hecMESH%node( 3*nodLOCAL(j)   )
            ! ----- create iwk array ***
            do i = 1, ndof
              iwk( ndof*(j-1)+i ) = ndof*( nodLOCAL(j)-1 )+i
            enddo
          enddo
        else
          do j = 1, nn
            nodLOCAL(j) = hecMESH%elem_node_item (is+j)
            ! ----- nodal coordinate
            if (ndof==2) then
              xx(j) = hecMESH%node( 3*nodLOCAL(j)-2 )+fstrSOLID%unode( 2*nodLOCAL(j)-1 )+fstrSOLID%dunode( 2*nodLOCAL(j)-1 )
              yy(j) = hecMESH%node( 3*nodLOCAL(j)-1 )+fstrSOLID%unode( 2*nodLOCAL(j)   )+fstrSOLID%dunode( 2*nodLOCAL(j)   )
            else if (ndof==3) then
              xx(j) = hecMESH%node( 3*nodLOCAL(j)-2 )+fstrSOLID%unode( 3*nodLOCAL(j)-2 )+fstrSOLID%dunode( 3*nodLOCAL(j)-2 )
              yy(j) = hecMESH%node( 3*nodLOCAL(j)-1 )+fstrSOLID%unode( 3*nodLOCAL(j)-1 )+fstrSOLID%dunode( 3*nodLOCAL(j)-1 )
              zz(j) = hecMESH%node( 3*nodLOCAL(j)   )+fstrSOLID%unode( 3*nodLOCAL(j)   )+fstrSOLID%dunode( 3*nodLOCAL(j)   )
            else if (ndof==6) then
              xx(j) = hecMESH%node( 3*nodLOCAL(j)-2 )+fstrSOLID%unode( 6*nodLOCAL(j)-5 )+fstrSOLID%dunode( 6*nodLOCAL(j)-5 )
              yy(j) = hecMESH%node( 3*nodLOCAL(j)-1 )+fstrSOLID%unode( 6*nodLOCAL(j)-4 )+fstrSOLID%dunode( 6*nodLOCAL(j)-4 )
              zz(j) = hecMESH%node( 3*nodLOCAL(j)   )+fstrSOLID%unode( 6*nodLOCAL(j)-3 )+fstrSOLID%dunode( 6*nodLOCAL(j)-3 )
            endif
            ! ----- create iwk array ***
            do i = 1, ndof
              iwk( ndof*(j-1)+i ) = ndof*( nodLOCAL(j)-1 )+i
            enddo
          enddo
        endif
        ! ----- section  ID
        isect = hecMESH%section_ID(icel)
        ! ----- Get Properties
        material => fstrSOLID%elements(icel)%gausses(1)%pMaterial
        rho = material%variables(M_DENSITY)
        call fstr_get_thickness(hecMESH, isect, thick)
        ! ----- Section Data
        if (ndof == 2) then
          id = hecMESH%section%sect_opt(isect)
          if (id == 0) then
            iset = 1
          else if (id == 1) then
            iset = 0
          else if (id == 2) then
            iset = 2
          endif
          pa1 = 1.d0
        endif
        ! ----- Create local stiffness
        if (ic_type==301)then
          ihead = hecMESH%section%sect_R_index(isect-1)
          call DL_C1(ic_type,nn,xx(1:nn),yy(1:nn),zz(1:nn),rho,thick,ltype,params,vect(1:nn*ndof),nsize)

        elseif( ic_type == 241 .or. ic_type == 242 .or. ic_type == 231 .or. ic_type == 232 .or. ic_type == 2322 ) then
          call DL_C2(ic_type,nn,xx(1:nn),yy(1:nn),rho,pa1,ltype,params,vect(1:nn*ndof),nsize,iset)

        else if ( ic_type == 341 .or. ic_type == 351 .or. ic_type == 361 .or.   &
            ic_type == 342 .or. ic_type == 352 .or. ic_type == 362 ) then
          call DL_C3(ic_type,nn,xx(1:nn),yy(1:nn),zz(1:nn),rho,ltype,params,vect(1:nn*ndof),nsize)

        else if ( ic_type == 641 ) then
          ihead = hecMESH%section%sect_R_index(isect-1)
          call DL_Beam_641(ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), rho, ltype, params, &
            hecMESH%section%sect_R_item(ihead+1:), vect(1:nn*ndof), nsize)

        else if( ( ic_type == 741 ) .or. ( ic_type == 743 ) .or. ( ic_type == 731 ) ) then
          call DL_Shell(ic_type, nn, ndof, xx, yy, zz, rho, thick, ltype, params, vect, nsize, fstrSOLID%elements(icel)%gausses)

        else if( ( ic_type==761 ) .or. ( ic_type==781 ) ) then
          call DL_Shell_33(ic_type, nn, ndof, xx, yy, zz, rho, thick, ltype, params, vect, nsize, &
            fstrSOLID%elements(icel)%gausses)

        else
          nsize = 0
          write(*,*)"### WARNING: DLOAD",ic_type

        endif
        ! ----- Add vector
        do j = 1, nsize
          fstrSOLID%GL(iwk(j)) = fstrSOLID%GL(iwk(j)) + factor * vect(j)
        enddo
      enddo
    enddo
    
  end subroutine process_distributed_loads

    ! -----Uload
  subroutine process_user_loads(cstep, fstrSOLID)
    integer(kind=kint), intent(in)  :: cstep
    type(fstr_solid), intent(inout) :: fstrSOLID
    
    real(kind=kreal) :: factor
    
    factor = fstrSOLID%factor(2)
    call uloading(cstep, factor, fstrSOLID%GL)
    
  end subroutine process_user_loads

  !======================================================================!
  !> Update right-hand side vector
  !======================================================================!
  subroutine update_rhs_vector(hecMESH, hecMAT, fstrSOLID)
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(hecmwST_matrix), intent(inout)  :: hecMAT
    type(fstr_solid), intent(inout)      :: fstrSOLID
    
    integer(kind=kint) :: i
    
    do i = 1, hecMESH%n_node * hecMESH%n_dof
      hecMAT%B(i) = fstrSOLID%GL(i) - fstrSOLID%QFORCE(i)
    enddo
    
    do i = 1, hecMAT%NDOF * hecMAT%NP
      !thermal load is not considered
      fstrSOLID%EFORCE(i) = fstrSOLID%GL(i)
    enddo
    
  end subroutine update_rhs_vector

    ! -------------------------------------------------------------------
    !  TLOAD : THERMAL LOAD USING TEMPERATURE
    ! -------------------------------------------------------------------
  subroutine process_thermal_loads(cstep, ctime, hecMESH, hecMAT, fstrSOLID)
    integer(kind=kint), intent(in)       :: cstep
    real(kind=kreal), intent(in)         :: ctime
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(hecmwST_matrix), intent(inout)  :: hecMAT
    type(fstr_solid), intent(inout)      :: fstrSOLID
    
    integer(kind=kint) :: ndof, ig0, ig, iS0, iE0, ik, in, grpid
    integer(kind=kint) :: itype, is, iE, icel, ic_type, nn, isect, cdsys_ID, id, iset
    integer(kind=kint) :: i, j, ihead, tstep, nodLocal(20), iwk(60)
    real(kind=kreal)   :: factor, fval, pa1
    real(kind=kreal)   :: xx(20), yy(20), zz(20), tt(20), tt0(20), coords(3,3), vect(60)
    real(kind=kreal)   :: local_coords(3,3)  ! Local copy for coordinate transformation
    
    ndof = hecMESH%n_dof
    
    if (fstrSOLID%TEMP_ngrp_tot > 0 .or. fstrSOLID%TEMP_irres > 0) then
      do ig0 = 1, fstrSOLID%TEMP_ngrp_tot
        grpid = fstrSOLID%TEMP_ngrp_GRPID(ig0)
        if (.not. fstr_isLoadActive(fstrSOLID, grpid, cstep)) cycle
        factor = fstrSOLID%factor(2)
        if (fstr_isLoadActive(fstrSOLID, grpid, cstep-1)) factor = 1.0d0
        ig = fstrSOLID%TEMP_ngrp_ID(ig0)
        fval = fstrSOLID%TEMP_ngrp_val(ig0)
        iS0 = hecMESH%node_group%grp_index(ig-1) + 1
        iE0 = hecMESH%node_group%grp_index(ig)
        do ik = iS0, iE0
          in = hecMESH%node_group%grp_item(ik)
          pa1 = fstrSOLID%temp_bak(in)
          fstrSOLID%temperature(in) = pa1 + (fval - pa1) * factor
        enddo
      enddo
      
      if (fstrSOLID%TEMP_irres > 0) then
        call read_temperature_result(hecMESH, fstrSOLID%TEMP_irres, fstrSOLID%TEMP_tstep, &
          &  fstrSOLID%TEMP_rtype, fstrSOLID%TEMP_interval, fstrSOLID%TEMP_factor, ctime, &
          &  fstrSOLID%temperature, fstrSOLID%temp_bak)
      endif
    endif

    ! ----- elemact element
    if( fstrSOLID%elemact%ELEMACT_egrp_tot > 0 ) &
      &  call fstr_update_elemact_solid( hecMESH, fstrSOLID, cstep, ctime )

    if( fstrSOLID%TEMP_ngrp_tot > 0 .or. fstrSOLID%TEMP_irres > 0 ) then
      ! ----- element TYPE loop.
      do itype = 1, hecMESH%n_elem_type
        is = hecMESH%elem_type_index(itype-1) + 1
        iE = hecMESH%elem_type_index(itype)
        ic_type = hecMESH%elem_type_item(itype)
        if (hecmw_is_etype_link(ic_type)) cycle
        if (hecmw_is_etype_patch(ic_type)) cycle
        ! ----- Set number of nodes
        nn = hecmw_get_max_node(ic_type)
        
        ! ----- element loop
        do icel = is, iE

          !ELEMENT ACTIVATION
          if( fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE ) cycle

          ! ----- node ID
          is = hecMESH%elem_node_index(icel-1)
          do j = 1, nn
            nodLocal(j) = hecMESH%elem_node_item(is+j)
            ! ----- nodal coordinate
            if (ndof == 2) then
              xx(j) = hecMESH%node(3*nodLocal(j)-2) + fstrSOLID%unode(ndof*nodLocal(j)-1)
              yy(j) = hecMESH%node(3*nodLocal(j)-1) + fstrSOLID%unode(ndof*nodLocal(j))
            else if (ndof == 3) then
              xx(j) = hecMESH%node(3*nodLocal(j)-2) + fstrSOLID%unode(ndof*nodLocal(j)-2)
              yy(j) = hecMESH%node(3*nodLocal(j)-1) + fstrSOLID%unode(ndof*nodLocal(j)-1)
              zz(j) = hecMESH%node(3*nodLocal(j)) + fstrSOLID%unode(ndof*nodLocal(j))
            endif
            tt0(j) = fstrSOLID%last_temp(nodLocal(j))
            tt(j) = fstrSOLID%temperature(nodLocal(j))
            ! ----- create iwk array ***
            do i = 1, ndof
              iwk(ndof*(j-1)+i) = ndof*(nodLocal(j)-1)+i
            enddo
          enddo
          
          ! ----- section  Data
          isect = hecMESH%section_ID(icel)
          cdsys_ID = hecMESH%section%sect_orien_ID(isect)
          call get_coordsys(cdsys_ID, hecMESH, fstrSOLID, coords)
          
          if (ndof == 2) then
            id = hecMESH%section%sect_opt(isect)
            if (id == 0) then
              iset = 1
            else if (id == 1) then
              iset = 0
            else if (id == 2) then
              iset = 2
            endif
            pa1 = 1.0d0
          endif
          
          if (ic_type == 641) then
            isect = hecMESH%section_ID(icel)
            ihead = hecMESH%section%sect_R_index(isect-1)
            
            call TLOAD_Beam_641( ic_type, nn, ndof, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn),    &
              fstrSOLID%elements(icel)%gausses, hecMESH%section%sect_R_item(ihead+1:), &
                               vect(1:nn*ndof))
            
            do j = 1, ndof*nn
              hecMAT%B(iwk(j)) = hecMAT%B(iwk(j)) + vect(j)
            enddo
            cycle
          endif
          
          ! Local copy of coordinate data
          local_coords = coords
          
          ! Calculate thermal load based on element type
          call calculate_thermal_load(ic_type, nn, xx, yy, zz, tt, tt0, isect, ndof, &
                                     hecMESH, fstrSOLID, icel, vect, cdsys_ID, local_coords, &
                                     iset, pa1, iwk, hecMAT%B)
        enddo
      enddo
    endif
    
  end subroutine process_thermal_loads

  !======================================================================!
  !> Calculate thermal load based on element type
  !======================================================================!
  subroutine calculate_thermal_load(ic_type, nn, xx, yy, zz, tt, tt0, isect, ndof, &
                                   hecMESH, fstrSOLID, icel, vect, cdsys_ID, coords, &
                                   iset, pa1, iwk, B)
    integer(kind=kint), intent(in)       :: ic_type, nn, isect, ndof, cdsys_ID, iset
    real(kind=kreal), intent(in)         :: xx(*), yy(*), zz(*), tt(*), tt0(*), pa1
    real(kind=kreal), intent(inout)      :: coords(3,3)  ! Changed INTENT from IN to INOUT
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(fstr_solid), intent(in)         :: fstrSOLID
    integer(kind=kint), intent(in)       :: icel
    real(kind=kreal), intent(out)        :: vect(*)
    integer(kind=kint), intent(in)       :: iwk(*)
    real(kind=kreal), intent(inout)      :: B(*)
    
    integer(kind=kint) :: j, myrank
    
    myrank = 0
    
    ! 2D elements
    if (ic_type == 241 .or. ic_type == 242 .or. ic_type == 231 .or. ic_type == 232) then
      call TLOAD_C2(ic_type, nn, xx(1:nn), yy(1:nn), tt(1:nn), tt0(1:nn), &
                   fstrSOLID%elements(icel)%gausses, pa1, iset, vect(1:nn*2))
    
    else if (ic_type == 361) then
      if (fstrSOLID%sections(isect)%elemopt361 == kel361FI) then
              call TLOAD_C3                                                          &
                ( ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn),       &
                     fstrSOLID%elements(icel)%gausses, vect(1:nn*ndof), cdsys_ID, coords)
      else if (fstrSOLID%sections(isect)%elemopt361 == kel361BBAR) then
              call TLOAD_C3D8Bbar                                                          &
                ( ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn),       &
                           fstrSOLID%elements(icel)%gausses, vect(1:nn*ndof), cdsys_ID, coords)
      else if (fstrSOLID%sections(isect)%elemopt361 == kel361IC) then
              call TLOAD_C3D8IC                                                            &
                ( ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn),       &
                         fstrSOLID%elements(icel)%gausses, vect(1:nn*ndof), cdsys_ID, coords)
      else if (fstrSOLID%sections(isect)%elemopt361 == kel361FBAR) then
              call TLOAD_C3D8Fbar                                                            &
                ( ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn),       &
                           fstrSOLID%elements(icel)%gausses, vect(1:nn*ndof), cdsys_ID, coords)
      endif
    
    else if (ic_type == 341 .or. ic_type == 351 .or. &
             ic_type == 342 .or. ic_type == 352 .or. ic_type == 362) then
            call TLOAD_C3                                                                &
              ( ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn),       &
                   fstrSOLID%elements(icel)%gausses, vect(1:nn*ndof), cdsys_ID, coords)
    
    else if (ic_type == 741 .or. ic_type == 743 .or. ic_type == 731) then
      if (myrank == 0) then
        write(IMSG,*) '*------------------------', &
                     '-------------------*'
        write(IMSG,*) ' Thermal loading option for shell elements', &
                     'not yet available.'
        write(IMSG,*) '*------------------------', &
                     '-------------------*'
        call hecmw_abort(hecmw_comm_get_comm())
      endif
    endif
    
          ! ----- Add vector
    do j = 1, ndof*nn
      B(iwk(j)) = B(iwk(j)) + vect(j)
    enddo

  end subroutine calculate_thermal_load

  !> DUMPW helper: print (to both FSTR.msg and stdout) the required file name
  !> and how to write it, so the user sees it in the log.
  subroutine fstr_sensitivity_points_help()
    write(IMSG,'(A)') ' DUMPW: the file "sensitivity_points.dat" is REQUIRED in the run directory.'
    write(IMSG,'(A)') '        Write ONE line with two global node ids: <Point_A> <Point_O>'
    write(IMSG,'(A)') '        (# or ! start a comment line). Example:'
    write(IMSG,'(A)') '          #Point_A, Point_O'
    write(IMSG,'(A)') '          19 103'
    write(*,'(A)') ' DUMPW: the file "sensitivity_points.dat" is REQUIRED in the run directory.'
    write(*,'(A)') '        Write ONE line with two global node ids: <Point_A> <Point_O>'
    write(*,'(A)') '        (# or ! start a comment line). Example:'
    write(*,'(A)') '          #Point_A, Point_O'
    write(*,'(A)') '          19 103'
  end subroutine fstr_sensitivity_points_help

  !======================================================================!
  !> DUMPW helper: read Point_A / Point_O global node ids from the text file
  !> 'sensitivity_points.dat' (one line: "<Point_A global id> <Point_O global id>")
  !> and convert them to the 6 local degrees of freedom used by the adjoint solve.
  !======================================================================!
  subroutine fstr_sensitivity_read_dofs(hecMESH, dof6, na_local, no_local, ok)
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    integer(kind=kint), intent(out)      :: dof6(6)
    integer(kind=kint), intent(out)      :: na_local, no_local
    logical, intent(out)                 :: ok

    integer(kind=kint), parameter :: iunit = 209
    integer(kind=kint) :: ga, go, i, stat, ios
    character(len=256)  :: line, lt

    ok = .false.
    na_local = 0
    no_local = 0
    dof6(:) = 0
    ga = 0
    go = 0

    open(iunit, file='sensitivity_points.dat', status='old', action='read', iostat=stat)
    if (stat /= 0) then
      write(IMSG,'(A)') ' DUMPW ERROR: cannot find/open "sensitivity_points.dat".'
      write(*,'(A)')    ' DUMPW ERROR: cannot find/open "sensitivity_points.dat".'
      call fstr_sensitivity_points_help()
      return
    endif
    ! read the first non-comment, non-blank line; "#" and "!" start a comment
    stat = -1
    do
      read(iunit, '(A)', iostat=ios) line
      if (ios /= 0) exit
      lt = adjustl(line)
      if (len_trim(lt) == 0) cycle
      if (lt(1:1) == '#' .or. lt(1:1) == '!') cycle
      read(lt, *, iostat=stat) ga, go
      exit
    enddo
    close(iunit)
    if (stat /= 0 .or. ga == 0 .or. go == 0) then
      write(IMSG,'(A)') ' DUMPW ERROR: could not read two node ids from "sensitivity_points.dat".'
      write(*,'(A)')    ' DUMPW ERROR: could not read two node ids from "sensitivity_points.dat".'
      call fstr_sensitivity_points_help()
      return
    endif

    do i = 1, hecMESH%n_node
      if (hecMESH%global_node_ID(i) == ga) na_local = i
      if (hecMESH%global_node_ID(i) == go) no_local = i
    enddo
    if (na_local == 0 .or. no_local == 0) then
      write(IMSG,*) ' DUMPW ERROR: Point_A or Point_O global node id not found in mesh:', ga, go
      write(*,*)    ' DUMPW ERROR: Point_A or Point_O global node id not found in mesh:', ga, go
      call fstr_sensitivity_points_help()
      return
    endif

    dof6(1) = 3*na_local-2; dof6(2) = 3*na_local-1; dof6(3) = 3*na_local
    dof6(4) = 3*no_local-2; dof6(5) = 3*no_local-1; dof6(6) = 3*no_local
    ok = .true.
    write(IMSG,*) 'DUMPW: Point_A global', ga, '-> local', na_local
    write(IMSG,*) 'DUMPW: Point_O global', go, '-> local', no_local
  end subroutine fstr_sensitivity_read_dofs

  !> number of nodes for the tetra types supported by DUMPW (0 = unsupported)
  integer(kind=kint) function fstr_sensitivity_solid_nnode(ic_type) result(nn)
    integer(kind=kint), intent(in) :: ic_type
    select case(ic_type)
      case(341); nn = 4    ! C3D4  : first-order  tetrahedron
      case(342); nn = 10   ! C3D10 : second-order tetrahedron
      case default; nn = 0
    end select
  end function fstr_sensitivity_solid_nnode

  !> heapsort the index array perm(1:n) so that keyv(perm(1..n)) is ascending
  !> (used to sort the H entries by (row, col) before writing H_matrix.mtx)
  subroutine fstr_sensitivity_heapsort(n, keyv, perm)
    integer(kind=kint), intent(in)    :: n
    integer(kind=8),    intent(in)    :: keyv(:)
    integer(kind=kint), intent(inout) :: perm(:)
    integer(kind=kint) :: i, ir, j, l, ip
    integer(kind=8)    :: kq

    if (n < 2) return
    l = n/2 + 1
    ir = n
    do
      if (l > 1) then
        l = l - 1
        ip = perm(l)
      else
        ip = perm(ir)
        perm(ir) = perm(1)
        ir = ir - 1
        if (ir == 1) then
          perm(1) = ip
          return
        endif
      endif
      kq = keyv(ip)
      i = l
      j = l + l
      do while (j <= ir)
        if (j < ir) then
          if (keyv(perm(j)) < keyv(perm(j+1))) j = j + 1
        endif
        if (kq < keyv(perm(j))) then
          perm(i) = perm(j)
          i = j
          j = j + j
        else
          j = ir + 1
        endif
      enddo
      perm(i) = ip
    enddo
  end subroutine fstr_sensitivity_heapsort

  !======================================================================!
  !> DUMPW: for first- and second-order tetrahedra (types 341 / 342),
  !> write H (H_matrix.mtx) and accumulate Wdiff = Z^T H.
  !> Z holds the 6 adjoint solutions (Point_A x/y/z, Point_O x/y/z).
  !> Each element column H_e[:,k] is obtained from the standard TLOAD_C3
  !> routine (which already supports 341/342 via its ic_type/nn arguments),
  !> and is immediately contracted with g_c = Z(:,c) - Z(:,c+3) (c = x,y,z)
  !> to give Wdiff(3, n_node).
  !> The H entries are collected element-by-element (with duplicate (row,col)
  !> from shared nodes), then sorted by (row, col) and duplicate entries are
  !> summed, so H_matrix.mtx is written in a readable, assembled order.
  !======================================================================!
  subroutine fstr_sensitivity_export(hecMESH, fstrSOLID, Z)
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(fstr_solid), intent(inout)      :: fstrSOLID
    real(kind=kreal), intent(in)         :: Z(:,:)   !< (n_node*ndof, 6)

    integer(kind=kint), parameter :: ndof = 3, maxnn = 10
    integer(kind=kint), parameter :: iuw = 210, iuh = 212
    integer(kind=kint) :: icel, is, i, j, k, c, inode, isect, cdsys_ID, ic_type, nn
    integer(kind=kint) :: row, kg, gnode, n_elem_solid, nentry, statw
    integer(kind=kint) :: ne, p, idx, rcur, ccur, nuniq
    integer(kind=kint) :: nodLocal(maxnn)
    integer(kind=kint), allocatable :: irow(:), icol(:), perm(:)
    integer(kind=8),    allocatable :: keyv(:)
    integer(kind=8) :: ncol8
    real(kind=kreal) :: xx(maxnn), yy(maxnn), zz(maxnn), tt(maxnn), tt0(maxnn)
    real(kind=kreal) :: vect(maxnn*ndof), coords(3,3), g(3), vsum
    real(kind=kreal), allocatable :: Wdiff(:,:), hval(:)

    allocate(Wdiff(3, hecMESH%n_node))
    Wdiff(:,:) = 0.0d0
    tt0(:) = 0.0d0

    ! ----- first pass: count solid elements and (raw) H entries -----
    n_elem_solid = 0
    nentry = 0
    do icel = 1, hecMESH%n_elem
      nn = fstr_sensitivity_solid_nnode(hecMESH%elem_type(icel))
      if (nn == 0) cycle
      if (fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE) cycle
      n_elem_solid = n_elem_solid + 1
      nentry = nentry + nn*ndof*nn
    enddo

    allocate(irow(nentry), icol(nentry), hval(nentry), perm(nentry), keyv(nentry))

    ! ----- second pass: element H columns -> collect (row,col,val), accumulate Wdiff -----
    ne = 0
    do icel = 1, hecMESH%n_elem
      ic_type = hecMESH%elem_type(icel)
      nn = fstr_sensitivity_solid_nnode(ic_type)
      if (nn == 0) cycle
      if (fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE) cycle

      is = hecMESH%elem_node_index(icel-1)
      do j = 1, nn
        nodLocal(j) = hecMESH%elem_node_item(is+j)
        inode = nodLocal(j)
        xx(j) = hecMESH%node(3*inode-2)
        yy(j) = hecMESH%node(3*inode-1)
        zz(j) = hecMESH%node(3*inode)
      enddo

      isect = hecMESH%section_ID(icel)
      cdsys_ID = hecMESH%section%sect_orien_ID(isect)
      call get_coordsys(cdsys_ID, hecMESH, fstrSOLID, coords)

      do k = 1, nn
        tt(1:nn) = 0.0d0
        tt(k) = 1.0d0
        call TLOAD_C3(ic_type, nn, xx(1:nn), yy(1:nn), zz(1:nn), tt(1:nn), tt0(1:nn), &
          fstrSOLID%elements(icel)%gausses, vect(1:nn*ndof), cdsys_ID, coords)
        kg = nodLocal(k)
        do j = 1, nn
          do i = 1, ndof
            row = ndof*(nodLocal(j)-1) + i
            ne = ne + 1
            irow(ne) = row
            icol(ne) = kg
            hval(ne) = vect(ndof*(j-1)+i)
            g(1) = Z(row,1) - Z(row,4)
            g(2) = Z(row,2) - Z(row,5)
            g(3) = Z(row,3) - Z(row,6)
            do c = 1, 3
              Wdiff(c,kg) = Wdiff(c,kg) + g(c) * vect(ndof*(j-1)+i)
            enddo
          enddo
        enddo
      enddo
    enddo

    ! ----- sort entries by (row, col) and sum duplicates, then write H_matrix.mtx -----
    ncol8 = int(hecMESH%n_node, 8) + 1_8
    do p = 1, ne
      perm(p) = p
      keyv(p) = int(irow(p), 8) * ncol8 + int(icol(p), 8)
    enddo
    call fstr_sensitivity_heapsort(ne, keyv, perm)

    ! count unique (row,col) pairs (adjacent equal keys after sort)
    nuniq = 0
    do p = 1, ne
      if (p == 1) then
        nuniq = 1
      else if (keyv(perm(p)) /= keyv(perm(p-1))) then
        nuniq = nuniq + 1
      endif
    enddo

    open(iuh, file='H_matrix.mtx', status='replace')
    write(iuh,'(A)') '%%MatrixMarket matrix coordinate real general'
    write(iuh,'(A)') '% Thermal load matrix: f_thermal = H * T  (sorted by row, then column)'
    write(iuh,"(I0,' ',I0,' ',I0)") hecMESH%n_node*ndof, hecMESH%n_node, nuniq
    rcur = -1; ccur = -1; vsum = 0.0d0
    do p = 1, ne
      idx = perm(p)
      if (irow(idx) == rcur .and. icol(idx) == ccur) then
        vsum = vsum + hval(idx)
      else
        if (rcur > 0) write(iuh,"(I0,' ',I0,' ',e20.12e3)") rcur, ccur, vsum
        rcur = irow(idx); ccur = icol(idx); vsum = hval(idx)
      endif
    enddo
    if (rcur > 0) write(iuh,"(I0,' ',I0,' ',e20.12e3)") rcur, ccur, vsum
    close(iuh)
    deallocate(irow, icol, hval, perm, keyv)

    ! ----- VTK (ParaView) -----
    call fstr_sensitivity_write_vtk(hecMESH, fstrSOLID, Wdiff, n_elem_solid)

    ! ----- plain text: global_node_id  Wdiff_x  Wdiff_y  Wdiff_z -----
    open(iuw, file='Wdiff_fistr.txt', status='replace', iostat=statw)
    if (statw == 0) then
      write(iuw,'(A)') '# global_node_id  Wdiff_x  Wdiff_y  Wdiff_z'
      do i = 1, hecMESH%n_node
        gnode = hecMESH%global_node_ID(i)
        write(iuw,"(I0,3(' ',e20.12e3))") gnode, Wdiff(1,i), Wdiff(2,i), Wdiff(3,i)
      enddo
      close(iuw)
    endif

    write(IMSG,*) 'DUMPW: wrote H_matrix.mtx, sensitivity_Wdiff.vtk, Wdiff_fistr.txt; n_node=', &
      hecMESH%n_node, ' n_elem_solid=', n_elem_solid
    deallocate(Wdiff)
  end subroutine fstr_sensitivity_export

  !======================================================================!
  !> DUMPW: write the sensitivity field Wdiff(3, n_node) as a legacy ASCII
  !> VTK unstructured grid, openable directly in ParaView.
  !> First-order tetrahedra (341) are written as VTK_TETRA (type 10);
  !> second-order tetrahedra (342) as VTK_QUADRATIC_TETRA (type 24).
  !> NOTE: inside the solver, hecMESH%elem_node_item for a 342 element is already
  !> in the shape-function node order (nodes 5..10 = mid(1,2),(2,3),(3,1),(1,4),
  !> (2,4),(3,4)), which is exactly the VTK_QUADRATIC_TETRA order, so NO
  !> reordering is needed here (identity). (FrontISTR's own C VTK writer applies
  !> table342 because it reads the raw mesh-file order instead.)
  !======================================================================!
  subroutine fstr_sensitivity_write_vtk(hecMESH, fstrSOLID, Wdiff, n_elem_solid)
    type(hecmwST_local_mesh), intent(in) :: hecMESH
    type(fstr_solid), intent(in)         :: fstrSOLID
    real(kind=kreal), intent(in)         :: Wdiff(:,:)
    integer(kind=kint), intent(in)       :: n_elem_solid

    integer(kind=kint), parameter :: iunit = 211
    integer(kind=kint) :: icel, is, j, i, stat, ic_type, nn, cell_list_size
    integer(kind=kint) :: nodLocal(10)

    open(iunit, file='sensitivity_Wdiff.vtk', status='replace', iostat=stat)
    if (stat /= 0) then
      write(IMSG,*) 'DUMPW: cannot open sensitivity_Wdiff.vtk'
      return
    endif

    write(iunit,'(A)') '# vtk DataFile Version 2.0'
    write(iunit,'(A)') 'Sensitivity Wdiff (Point_A - Point_O per unit nodal temperature)'
    write(iunit,'(A)') 'ASCII'
    write(iunit,'(A)') 'DATASET UNSTRUCTURED_GRID'
    write(iunit,"('POINTS ',I0,' double')") hecMESH%n_node
    do i = 1, hecMESH%n_node
      write(iunit,"(3(e20.12e3,' '))") &
        hecMESH%node(3*i-2), hecMESH%node(3*i-1), hecMESH%node(3*i)
    enddo

    ! total size of the CELLS list = sum over cells of (nn + 1)
    cell_list_size = 0
    do icel = 1, hecMESH%n_elem
      nn = fstr_sensitivity_solid_nnode(hecMESH%elem_type(icel))
      if (nn == 0) cycle
      if (fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE) cycle
      cell_list_size = cell_list_size + (nn + 1)
    enddo

    write(iunit,"('CELLS ',I0,' ',I0)") n_elem_solid, cell_list_size
    do icel = 1, hecMESH%n_elem
      ic_type = hecMESH%elem_type(icel)
      nn = fstr_sensitivity_solid_nnode(ic_type)
      if (nn == 0) cycle
      if (fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE) cycle
      is = hecMESH%elem_node_index(icel-1)
      do j = 1, nn
        nodLocal(j) = hecMESH%elem_node_item(is+j)
      enddo
      if (nn == 4) then
        write(iunit,"(I0,4(' ',I0))") 4, (nodLocal(j)-1, j=1,4)
      else   ! nn == 10 : elem_node_item is already in VTK_QUADRATIC_TETRA order
        write(iunit,"(I0,10(' ',I0))") 10, (nodLocal(j)-1, j=1,10)
      endif
    enddo

    write(iunit,"('CELL_TYPES ',I0)") n_elem_solid
    do icel = 1, hecMESH%n_elem
      nn = fstr_sensitivity_solid_nnode(hecMESH%elem_type(icel))
      if (nn == 0) cycle
      if (fstrSOLID%elements(icel)%elemact_flag == kELACT_INACTIVE) cycle
      if (nn == 4) then
        write(iunit,'(A)') '10'   ! VTK_TETRA
      else
        write(iunit,'(A)') '24'   ! VTK_QUADRATIC_TETRA
      endif
    enddo

    write(iunit,"('POINT_DATA ',I0)") hecMESH%n_node
    write(iunit,'(A)') 'VECTORS Sensitivity double'
    do i = 1, hecMESH%n_node
      write(iunit,"(3(e20.12e3,' '))") Wdiff(1,i), Wdiff(2,i), Wdiff(3,i)
    enddo
    close(iunit)
  end subroutine fstr_sensitivity_write_vtk

end module m_fstr_ass_load
