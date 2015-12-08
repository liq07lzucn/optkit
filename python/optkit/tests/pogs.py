from optkit import Matrix, FunctionVector, pogs
from optkit.types import ok_function_enums
from optkit.blocksplitting.types import *
from optkit.utils.pyutils import println,printvoid,var_assert
from optkit.tests.defs import HLINE, TEST_EPS
import numpy as np
from operator import add
from numpy.linalg import norm

def pogs_test(m=300,n=200,A_in=None, VERBOSE_TEST=True):
	if m is None: m=300
	if n is None: n=200
	if isinstance(A_in,np.ndarray):
		if len(A_in.shape)==2:
			(m,n)=A_in.shape
		else:
			A_in=None

	PRINT=println if VERBOSE_TEST else printvoid
	verbose=2 if VERBOSE_TEST else 0

	mat_kind = "SKINNY MATRIX" if m >= n else "FAT MATRIX"
	PRINT(HLINE, HLINE, HLINE)
	PRINT(mat_kind)
	PRINT("m: {}, n: {}".format(m,n))

	A = Matrix(np.random.rand(m,n)) if A_in is None else Matrix(A_in) 
	A_copy = np.copy(A.py)
	maxiter=2000
	reltol=1e-3

	for FUNCKEY in ok_function_enums.enum_dict.keys():
		print FUNCKEY

		f = FunctionVector(m, h=FUNCKEY, b=1)
		g = FunctionVector(n, h='IndGe0')
		info, output, solver_state = pogs(A,f,g,
			reltol=reltol,maxiter=maxiter,verbose=verbose)

		assert var_assert(solver_state,type=SolverState)
		assert var_assert(info,type=SolverInfo)
		assert var_assert(output, type=OutputVariables)
		assert info.converged or info.k==maxiter

		A_ = solver_state.A.mat.py 
		d = solver_state.z.de.y.py
		e = solver_state.z.de.x.py
		xrand = np.random.rand(n)
		assert np.max(np.abs(d*A_copy.dot(e*xrand)-A_.dot(xrand)))

		res_p = np.linalg.norm(A_copy.dot(output.x)-output.y)
		res_d = np.linalg.norm(A_copy.T.dot(output.nu)+output.mu)

		if FUNCKEY not in  ('Logistic','Exp'):
			assert not info.converged or res_p <= TEST_EPS or res_p/np.linalg.norm(output.y) <= 10*reltol
		assert not info.converged or res_d <= TEST_EPS or res_d/np.linalg.norm(output.mu) <= 10*reltol


		PRINT(HLINE)
		PRINT("PRIMAL & DUAL FEASIBILITY")
		PRINT("||Ax-y||: ", res_p)
		PRINT("||A'nu+mu||: ", res_d)

		PRINT(HLINE, HLINE)
		PRINT("INFO:")
		PRINT(info)
		
		PRINT(HLINE, HLINE)
		PRINT("OUTPUT:")
		PRINT(output)

		PRINT(HLINE, HLINE)
		PRINT("SOLVER STATE:")
		PRINT(solver_state)



def test_pogs(*args, **kwargs):
	print "POGS CALL TESTING\n\n\n\n"
	verbose = '--verbose' in args
	(m,n)=kwargs['shape'] if 'shape' in kwargs else (None,None)
	A = np.load(kwargs['file']) if 'file' in kwargs else None

	pogs_test(m=m,n=n,A_in=A,VERBOSE_TEST=verbose)
	if isinstance(A,np.ndarray): A=A.T
	pogs_test(m=n,n=m,A_in=A,VERBOSE_TEST=verbose)
	print "...passed"
	return True


