from optkit.types import Vector, Matrix, Range, ok_enums as enums
from optkit.utils import ndarray_pointer, make_cvector, make_cmatrix
from optkit.pyutils import istypedtuple
from optkit.libs import oklib
from optkit.defs import DIMCHECK_FLAG, TYPECHECK_FLAG
# from toolz import *

# in-place operations

# TODO: gpu version
# TODO: wrap in class---takes lib as init argument
# TODO: change functions to templates with handle, lib
# TODO: partial evaluation/currying with handle (or None) and lib
# TODO: operator overloading?


def copy(orig, dest, python=False):
	if isinstance(orig, Vector) and isinstance(dest, Vector):
		oklib.__vector_memcpy_vv(dest.c,orig.c)
	elif isinstance(orig, Matrix) and isinstance(dest, Matrix):
		oklib.__matrix_memcpy_mm(dest.c,orig.c)
	else:
		print("optkit.ops.copy(dest, orig) defined"
			  "only when arguments are jointly of"
			  "type opkit.Vector or opkit.Matrix")	

def view(x, *range_, **viewtype):

	input_err = str("Error: optkit.ops.view: "
		"invalid view specification.\n"
		"Valid argument & keyword argument combinations:"
		"(`optkit.Vector`, `tuple(int,int)`)\n"
		"(`optkit.Matrix`, diag=1)\n"
		"(`optkit.Matrix`, `int`, [no keyword args, views row])\n"		
		"(`optkit.Matrix`, `int`, row=1)\n"
		"(`optkit.Matrix`, `int`, col=1)\n"
		"(`optkit.Matrix`, `tuple(int,int)`, `tuple(int,int)`)\n"
		"Provided: x:{}\n args:{}\n kwargs:{}".format(
			type(x),
			[type(r) for r in range_],
			["{}={}".format(k,viewtype[k]) for k in viewtype.keys()]))


	if not isinstance(x, (Vector,Matrix)):
		print("Error: optkit.ops.view(x) only defined"
			  "for argument of type optkit.Vector or"
			  "optkit.Matrix.")

	elif isinstance(x, Vector) and \
		 len(range_) == 1 and \
		 istypedtuple(range_,2,int):

		rng = Range(x.size, *range_)
		pyview = x.py[rng.idx1:rng.idx2]
		cview = make_cvector()
		oklib.__vector_subvector(cview, x.c, rng.idx1, rng.elements)
		return Vector(pyview, cview)
	elif isinstance(x, Matrix) and \
		 len(range_) == 2 and  \
		 istypedtuple(range_,2,tuple):

		if not istypedtuple(range_[0],2,int) and \
			   istypedtuple(range_[1],2,int):

			print input_err
			return None

		rng1 = Range(x.size1, *range_[0])
		rng2 = Range(x.size2, *range_[1])		
		pyview = x.py[rng1.idx1:rng1.idx2,rng2.idx1:rng2.idx2]
		cview = make_cmatrix()
		oklib.__matrix_submatrix(cview,x.c, 
								 rng1.idx1, rng2.idx1, 
								 rng1.elements, rng2.elements)		
		return Matrix(pyview, cview)
	elif isinstance(x,Matrix) and len(range_) == 1:
		idx = range_[0]
		cview=make_cvector()
		if 'col' in viewtype:
			col = Range(x.size2, idx).idx1
			oklib.__matrix_column(cview, x.c, col)
			pyview = x.py[:,col]
		else:
			row = Range(x.size1,idx).idx1
			oklib.__matrix_row(cview, x.c, row)
			pyview = x.py[row,:]
			if not 'row' in viewtype:
				print("keyword argument `row=1`, `col=1` or `diag=1` "
				  "not provided, assuming row view")
		return Vector(pyview,cview)			
	elif 'diag' in viewtype:
		cview=make_cvector()
		oklib.__matrix_diagonal(cview, x.c)
		pyview = x.py.diagonal()
		return Vector(pyview, cview, sync_required=1)
	else: 
		print input_err
		return None


def add(const_x,y, python=False):
	if isinstance(const_x, Vector) and isinstance(y, Vector):
		if y.size != const_x.size: 
			print ("Error: optkit.ops.add---"
				   "incompatible Vector dimensions\n"
				   "const_x: {}, y: {}".format(const_x.size, y.size))
		else:
			oklib.__vector_add(y.c, const_x.c);
	elif isinstance(const_x, (int,float)) and isinstance(y, Vector):
		oklib.__vector_add_constant(y.c, const_x)
	else:
		print("optkit.ops.add(x,y) defined for : \n"
			  "\t(optkit.Vector, optkit.Vector) \n"
			  "\t(int/float, optkit.Vector) ")

def sub(const_x,y, python=False):
	if isinstance(const_x, Vector) and isinstance(y, Vector):
		if y.size != const_x.size: 
			print ("Error: optkit.ops.sub---"
				   "incompatible Vector dimensions\n"
				   "const_x: {}, y: {}".format(const_x.size, y.size))
		else:
			oklib.__vector_sub(y.c, const_x.c);
	elif isinstance(const_x, (int,float)) and isinstance(y, Vector):
		oklib.__vector_add_constant(y.c, -const_x)
	else:
		print("optkit.ops.sub(x,y) defined for : \n"
			  "\t(optkit.Vector, optkit.Vector) \n"
			  "\t(int/float, optkit.Vector) ")

def mul(const_x,y, python=False):
	if isinstance(const_x, Vector) and isinstance(y, Vector):
		if y.size != const_x.size: 
			print ("Error: optkit.ops.mul---"
				   "incompatible Vector dimensions\n"
				   "const_x: {}, y: {}".format(const_x.size, y.size))
		else:
			oklib.__vector_mul(y.c, const_x.c);
	elif isinstance(const_x, (int,float)) and isinstance(y, Vector):
		oklib.__vector_scale(y.c, const_x);
	elif isinstance(const_x, (int,float)) and isinstance(y, Matrix):
		oklib.__matrix_scale(y.c, const_x);		
	else:
		print("optkit.ops.mul(x,y) defined for : \n"
			  "\t(optkit.Vector, optkit.Vector) \n"
			  "\t(int/float, optkit.Vector) \n"
			  "\t(int/float, optkit.Matrix)")

def div(const_x,y, python=False):
	if isinstance(const_x, Vector) and isinstance(y, Vector):
		if y.size != const_x.size: 
			print ("Error: optkit.ops.div---"
				   "incompatible Vector dimensions\n"
				   "const_x: {}, y: {}".format(const_x.size, y.size))
		else:
			oklib.__vector_div(y.c, const_x.c);
	elif isinstance(const_x, (int,float)) and isinstance(y, Vector):
		oklib.__vector_scale(y.c, 1./const_x);		
	elif isinstance(const_x, (int,float)) and isinstance(y, Matrix):
		oklib.__matrix_scale(y.c, 1./const_x);		
	else:
		print("optkit.ops.div(x,y) defined for : \n"
			  "\t(optkit.Vector, optkit.Vector) \n"
			  "\t(int/float, optkit.Vector) \n"
			  "\t(int/float, optkit.Matrix)")

def dot(x,y, python=False, 
		typecheck=TYPECHECK_FLAG, dimcheck=DIMCHECK_FLAG):
	if typecheck and not \
		   (isinstance(x, Vector) and 
			isinstance(y, Vector)):
		print("optkit.ops.div(x,y) defined for : \n"
			  "\t(optkit.Vector, optkit.Vector)")
	else:
		if dimcheck and y.size != x.size: 
			print ("Error: optkit.ops.dot---"
				   "incompatible Vector dimensions\n"
				   "x: {}, y: {}".format(x.size, y.size))
		else:
			return oklib.__blas_dot(x.c,y.c)

def asum(x, python=False, typecheck=True):
	if typecheck and not isinstance(x, Vector):
		print("optkit.ops.div(x) defined for optkit.Vector")
	else:
		return oklib.__blas_asum(x.c)

def nrm2(x, python=False, typecheck=True):
	if typecheck and not isinstance(x, Vector):
		print("optkit.ops.div(x) defined for optkit.Vector")
	else:
		return oklib.__blas_nrm2(x.c)

def axpy(alpha, const_x, y, python=False, 
			typecheck=TYPECHECK_FLAG, dimcheck=DIMCHECK_FLAG):
	if typecheck and not \
			(isinstance(alpha, (int,float)) and
			 isinstance(const_x, Vector) and
			 isinstance(y, Vector)):
		print ("optkit.ops.axpy(alpha, x, y) defined for: \n"
			   "\t(int/float, optkit.Vector, optkit.Vector)")
	else:
		if dimcheck and const_x.size != y.size:
			print ("Error: optkit.ops.axpy---"
				   "incompatible dimensions for y+=alpha x\n"
				   "x: {}, y: {}".format(const_x.size, y.size))
		else:
			oklib.__blas_axpy(alpha, const_x.c, y.c)			

def gemv(tA, alpha, A, x, beta, y, 
			typecheck=TYPECHECK_FLAG, dimcheck=DIMCHECK_FLAG):
	if typecheck and not \
	 	   (isinstance(alpha, (int,float)) and
			isinstance(A, Matrix) and  
			isinstance(x, Vector) and
			isinstance(beta, (int,float)) and
			isinstance(y, Vector)):
		print("optkit.ops.div(alpha, A, x, beta, y) defined for : \n"
			  "\t(int/float, optkit.Matrix, optkit.Matrix," 
			  " int/float, optkit.Matrix)")
	else:
		if dimcheck:
			input_dim = A.size1 if tA=='T' else A.size2
			output_dim = A.size2 if tA=='T' else A.size1
			tsym = "^T" if tA=='T' else ""
			if  tA == 'T':
				dim_in = A.size1
				dim_out = A.size2
				tsym = "^T"
			else:
				dim_in = A.size2
				dim_out = A.size1
				tsym = ""
			if (x.size!= dim_in or y.size != dim_out): 
				print ("Error: optkit.ops.gemv---"
				   "incompatible dimensions for y=A{} * x\n"
				   "A: {},{}\n x: {}, y: {}".format(tsym,
				   	A.size1, A.size2, x.size, y.size))
				return 

		At = enums.CblasTrans if tA =='T' else enums.CblasNoTrans			
		oklib.__blas_gemv(At, alpha, A.c, x.c, beta, y.c)


def gemm(tA, tB, alpha, A, B, beta, C, 
			typecheck=TYPECHECK_FLAG, dimcheck=DIMCHECK_FLAG):
	if typecheck and not \
	       (isinstance(alpha, (int,float)) and
			isinstance(A, Matrix) and  
			isinstance(B, Matrix) and
			isinstance(beta, (int,float)) and
			isinstance(C, Matrix)): 
		print("optkit.ops.gemm(alpha, A, B, beta, y) defined for : \n"
			  "\t(int/float, optkit.Matrix, optkit.Matrix,"
			  " int/float, optkit.Matrix)")
	else:
		if dimcheck:
			outer_dim_L = A.size2 if tA=='T' else A.size1
			inner_dim_L = A.size1 if tA=='T' else A.size2
			inner_dim_R = B.size2 if tB=='T' else B.size1
			outer_dim_R = B.size1 if tB=='T' else B.size2
			tsymA = "^T" if tA=='T' else ""
			tsymB = "^T" if tB=='T' else ""


			if (C.size1 != outer_dim_L or \
						 inner_dim_L != inner_dim_R or \
						 C.size2 != outer_dim_R): 
				print ("Error: optkit.ops.gemm---"
				   "incompatible dimensions for C=A{} * B{}\n"
				   "A: {}x{}\nB: {}x{}\nC: {}x{}".format(
				   	tsymA, tsymB, A.size1, A.size2, B.size1, 
				   	B.size2, C.size1, C.size2))
				return
		
		At = enums.CblasTrans if tA =='T' else enums.CblasNoTrans
		Bt = enums.CblasTrans if tB =='T' else enums.CblasNoTrans
		print "ALPHA:", alpha
		print "BETA:", beta

		oklib.__blas_gemm(At, Bt, alpha, A.c, B.c, beta, C.c)

	
def cholesky_factor(A, python=False, dimcheck=DIMCHECK_FLAG):
	if not isinstance(A, Matrix):
		print("optkit.ops.cholesky_factor(A) defined"
		      "only when argument is of"
			  "type opkit.Matrix")
	else:
		if dimcheck and A.size1 != A.size2:
			print ("Error: optkit.ops.cholesky_factor(A)"
				   "only defined for square matrices A"
				   "A: {}x{}".format(A.size1, A.size2))
		oklib.__linalg_cholesky_decomp(A.c)

def cholesky_solve(L, x, python=False, 
					typecheck=TYPECHECK_FLAG,
					dimcheck=DIMCHECK_FLAG):
	if typecheck:
		if not isinstance(L, Matrix):
			print("optkit.ops.cholesky_solve(L, x) defined"
				  "only when first argument is of"
				  "type opkit.Matrix")
			return
		elif not isinstance(x, Vector):
			print("optkit.ops.cholesky_solve(L, x) defined"
				  "only when second argument is of"
				  "type opkit.Vector")
			return

	if dimcheck and (x.size != L.size2 or x.size != L.size2): 
		print ("Error: optkit.ops.cholesky_solve---"
			   "incompatible dimensions for x:=inv(L) * x\n"
			   "L: {}x{}\nx: {}".format(L.size1, L.size2, x.size))
		return

	oklib.__linalg_cholesky_svx(L.c,x.c)



"""
	keyword args: python_to_C (default=False), sets copy direction
"""
def sync(*vars, **py2c):
	python_to_C = "python_to_C" in py2c

	for x in vars:
		if not isinstance(x, (Vector,Matrix)):
			print("optkit.ops.sync undefined for "
				  "types other than:\n optkit.Vector "
				  "\n optkit.Matrix")	
		else:
			if not x.sync_required: return
			if isinstance(x,Vector):
				if python_to_C:
					oklib.__vector_memcpy_va(x.c, ndarray_pointer(x.py))
				else:
					oklib.__vector_memcpy_av(ndarray_pointer(x.py), x.c)
			else:
				if python_to_C:
					oklib.__vector_memcpy_ma(x.c, ndarray_pointer(x.py))
				else:
					oklib.__vector_memcpy_am(ndarray_pointer(x.py), x.c)

def print_var(x, python=False):
	if not isinstance(x, (Vector,Matrix)):
		print("optkit.ops.print_var undefined for "
			   "types other than: \n optkit.Vector"
				"\n optkit.Matrix")
	else:
		if python:
			if x.sync_required: sync(x)
			print x.py
		elif isinstance(x, Vector):
			oklib.__vector_print(x.c)
		else:
			oklib.__matrix_print(x.c)


