
CFLAGS = -Wall -O2  -I ../../../SPOOLES.2.2 -DARCH="Linux" -DSPOOLES -DARPACK -DMATRIXSTORAGE -DNETWORKOUT
FFLAGS = -Wall -O2 -fallow-argument-mismatch

CC=gcc
FC=gfortran

.c.o :
	$(CC) $(CFLAGS) -c $<
.f.o :
	$(FC) $(FFLAGS) -c $<

include Makefile.inc

SCCXMAIN = ccx_2.21.c

OCCXF = $(SCCXF:.f=.o)
OCCXC = $(SCCXC:.c=.o)
OCCXMAIN = $(SCCXMAIN:.c=.o)

DIR=../../../SPOOLES.2.2

LIBS = \
       $(DIR)/spooles.a \
       /lib/x86_64-linux-gnu/libarpack.so.2 -llapack -lblas \
       -lpthread -lm -lc

ccx_2.21: $(OCCXMAIN) ccx_2.21.a $(DIR)/spooles.a
	./date.pl; $(CC) $(CFLAGS) -c ccx_2.21.c; $(FC)  -Wall -O2 -o $@ $(OCCXMAIN) ccx_2.21.a $(LIBS) -fopenmp

ccx_2.21.a: $(OCCXF) $(OCCXC)
	ar vr $@ $?
