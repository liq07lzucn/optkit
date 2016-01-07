import numpy as np
from traceback import format_exc
from numpy.linalg import norm
from optkit.utils.proxutils import func_eval_python, prox_eval_python
from optkit.utils.pyutils import println, pretty_print, printvoid, var_assert
from optkit.tests.defs import gen_test_defs

def blocksplitting_test(errors, m=None, n=None, A_in=None,
	VERBOSE_TEST=True, gpu=False, floatbits=64):

	try:
		from optkit.api import backend, set_backend

		if not backend.__LIBGUARD_ON__:
			set_backend(GPU=gpu, double=floatbits == 64)

		from optkit.api import Vector, Matrix, FunctionVector, \
			linsys, DirectProjector, pogs
		TEST_EPS, RAND_ARR, MAT_ORDER = gen_test_defs(backend)

		ProblemVariables = pogs.types.ProblemVariables
		SolverMatrix = pogs.types.SolverMatrix
		SolverState = pogs.types.SolverState
		SolverSettings = pogs.types.SolverSettings
		SolverInfo = pogs.types.SolverInfo
		OutputVariables = pogs.types.OutputVariables
		Objectives = pogs.types.Objectives
		Residuals = pogs.types.Residuals
		Tolerances = pogs.types.Tolerances
		AdaptiveRhoParameters = pogs.types.AdaptiveRhoParameters

		if m is None: m=30
		if n is None: n=20
		if isinstance(A_in,np.ndarray):
			if len(A_in.shape)==2:
				(m,n)=A_in.shape
			else:
				A_in=None

		print '(m = {}, n = {})'.format(m, n)

		PRINT = println if VERBOSE_TEST else printvoid
		PPRINT = pretty_print if VERBOSE_TEST else printvoid
		PRINTVAR = print_var if VERBOSE_TEST else printvoid

		if isinstance(A_in,np.ndarray):
			A = Matrix(A_in.astype(backend.lowtypes.FLOAT_CAST))
		else:
			A = Matrix(RAND_ARR(m,n))
		f = FunctionVector(m, h='Abs', b=1)
		g = FunctionVector(n, h='IndGe0')
		A_orig = np.copy(A.py)

		options = {}
		solver_state = None

		settings = SolverSettings(**options)
		info = SolverInfo()
		output = OutputVariables(m,n)

		A = SolverMatrix(A)
		z = ProblemVariables(m,n)
		d = z.de.y
		e = z.de.x

		assert var_assert(A,d,e,f,g,z,settings,info,output,selfchecking=True)
		assert A.shape == (m,n)
		assert A.shape == z.blocksizes
		assert d.size == m
		assert e.size == n
		assert output.x.size == n
		assert output.y.size == m

		PPRINT("PROBLEM SETUP METHODS", '=')

		PPRINT("INPUT/OUTPUT")

		PRINT("\nPROBLEM DATA")
		PRINT("A object: ", A)
		PRINT("A matrix: ", A.mat)

		PRINT("\FUNCTION VECTORS")
		PRINT("f: ", f)
		PRINT("g: ", g)

		PRINT("\nPROBLEM VARIABLES")
		PRINT("z: ", z)

		PRINT("\nEQUILIBRATION VARIABLES")
		PRINT("d: ", d)
		PRINT("e: ", e)

		PRINT("\nSOLVER STRUCTS")
		PRINT("settings: ", settings)
		PRINT("info: ", info)

		PRINT("\nOUTPUT VARIABLES")
		PRINT(output)

		PPRINT("PRECONDITION, PROJECTOR, PROX OPERATOR")

		PRINT("\nEQUILIBRATE")
		if not A.equilibrated: pogs.utils.equilibrate(A, d, e)
		A.sync()
		linsys['sync'](d, e)

		PRINT("A: ", A)
		PRINT("d: ", d)
		PRINT("e: ", e)

		xrand = RAND_ARR(n)
		Ax = A.mat.py.dot(xrand)
		DAEx = d.py * A_orig.dot(e.py * xrand)
		assert all(np.abs(Ax - DAEx) <= TEST_EPS)

		PRINT("\nPROJECTOR")
		Proj = DirectProjector(A.mat, normalize=True)	
		A.normalized=True	
		A.sync()
		PRINT("ProjA: ", Proj)
		assert var_assert(Proj,type=DirectProjector)

		PRINT("\nNORMALIZE A, Proj, d, e")
		PRINT("BEFORE:")
		PRINT("A object: ", A)
		PRINT("A matrix: ", A.mat)
		PRINT("d: ", d)
		PRINT("e: ", e)

		norm_de_before = norm(d.py) * norm(e.py)
		pogs.utils.normalize_system(A, d, e, normA=Proj.normA)
		A.sync()
		linsys['sync'](d, e)
		norm_de_after = norm(d.py) * norm(e.py)

		xrand = RAND_ARR(n)
		Ax = A.mat.py.dot(xrand)
		DAEx = d.py * A_orig.dot(e.py * xrand)
		assert all(np.abs(Ax - DAEx) <= TEST_EPS)

		# ||A||_2 == 1
		assert abs(norm(A.mat.py) / (A.mat.mindim**0.5) - 1) <= TEST_EPS

		# ||d||*||e|| / ||1/sqrt(norm_A) * d||*||1/sqrt(norm_A) * e|| == norm_A
		assert abs(norm_de_before/norm_de_after - Proj.normA) <= TEST_EPS

		PRINT("AFTER:")
		PRINT("A object: ", A)
		PRINT("A matrix: ", A.mat)
		PRINT("d: ", d)
		PRINT("e: ", e)

		PRINT("\nSCALE f, g")
		PRINT("BEFORE")
		PRINT("f: ", f)
		PRINT("g: ", g)
		
		fobj = f.tolist()
		gobj = g.tolist()

		fa_ = np.array([ff.a for ff in fobj])
		fd_ = np.array([ff.d for ff in fobj])
		fe_ = np.array([ff.e for ff in fobj])
		ga_ = np.array([gg.a for gg in gobj])
		gd_ = np.array([gg.d for gg in gobj])
		ge_ = np.array([gg.e for gg in gobj])
		d_  = np.copy(d.py)
		e_  = np.copy(e.py)

		pogs.utils.scale_functions(f,g,d,e)
		f.pull()

		fobj = f.tolist()
		gobj = g.tolist()
		fa_scal = np.array([ff.a for ff in fobj])
		fd_scal = np.array([ff.d for ff in fobj])
		fe_scal = np.array([ff.e for ff in fobj])
		ga_scal = np.array([gg.a for gg in gobj])
		gd_scal = np.array([gg.d for gg in gobj])
		ge_scal = np.array([gg.e for gg in gobj])

		assert np.max(np.abs((fa_ / d_ - fa_scal))) <= TEST_EPS
		assert np.max(np.abs((fe_ / d_ - fd_scal))) <= TEST_EPS
		assert np.max(np.abs((fe_ / d_ - fe_scal))) <= TEST_EPS
		assert np.max(np.abs((ga_ * e_ - ga_scal))) <= TEST_EPS
		assert np.max(np.abs((gd_ * e_ - gd_scal))) <= TEST_EPS
		assert np.max(np.abs((ge_ * e_ - ge_scal))) <= TEST_EPS

		PRINT("AFTER")
		PRINT("f: ", f)
		PRINT("g: ", g)

		PPRINT("SCALED SYSTEM: PROJECTION TEST")

		x = Vector(RAND_ARR(n))
		y = Vector(RAND_ARR(m))
		x_out = Vector(n)
		y_out = Vector(m)
		var_assert(x,y,x_out,y_out,type=Vector)

		PRINT("RANDOM (x,y)")
		PRINT("||x||_2, {} \t ||y||_2: {}".format(norm(x.py), norm(y.py)))
		PRINT("||Ax-y||_2:")
		PRINT(norm(y.py-A.mat.py.dot(x.py)))

		Proj(x,y,x_out,y_out)
		linsys['sync'](x, y, x_out, y_out)

		PRINT("PROJECT:")
		PRINT("||x||_2, {} \t ||y||_2: {}".format(norm(x_out.py), norm(y_out.py)))
		PRINT("||Ax-y||_2:")
		res = norm(y_out.py - A.mat.py.dot(x_out.py))
		assert res <= TEST_EPS
		PRINT(res)

		PRINT("\nPROXIMAL OPERATOR")
		Prox = pogs.utils.prox_eval(f,g)		
		PRINT("Prox: ", Prox)

		PPRINT("\nVARIABLE MANIPULATION AND STORAGE")

		PRINT("\nVARIABLE INITIALIZATION (i.e., WARM START)")
		pogs.utils.initialize_variables(A.mat, settings.rho, z, x.py, y.py)
		z.sync()

		PRINT("z primal", z.primal.vec)
		PRINT("z dual", z.dual.vec)

		res_p = norm(A.mat.py.dot(z.primal.x.py) - z.primal.y.py)
		res_d = norm(A.mat.py.T.dot(z.dual.y.py) + z.dual.x.py)
		PRINT("primal feasibility at step k=0: ", res_p)
		PRINT("dual feasibility at step k=0: ", res_p)
		
		assert np.max(np.abs((z.primal.x.py - (x.py / z.de.x.py)))) <= 0.
		assert np.max(np.abs((z.dual.y.py + (y.py / z.de.y.py) / settings.rho))) <= TEST_EPS
		assert res_p <= TEST_EPS
		assert res_d <= TEST_EPS

		PRINT("\nVARIABLE UNSCALING")
		pogs.utils.unscale_output(settings.rho, z, output)		
		PRINT("output vars:", output)
		assert np.max(np.abs((z.primal12.x.py * e_ - output.x))) <= TEST_EPS
		assert np.max(np.abs((z.primal12.y.py / d_ - output.y))) <= TEST_EPS
		assert np.max(np.abs((-settings.rho * z.dual12.x.py / e_ - output.mu))) <= TEST_EPS
		assert np.max(np.abs((-settings.rho * z.dual12.y.py * d_ - output.nu))) <= TEST_EPS

		PRINT("\nVARIABLE STORAGE")
		solver_state=SolverState(A,Proj,z)
		assert var_assert(solver_state)
		PRINT(solver_state)

		PPRINT("PROBLEM SOLVE METHODS", '=')

		PPRINT("ACCESS SETTINGS",'.')
		PRINT("rho: ", settings.rho)
		PRINT("alpha: ", settings.alpha)
		PRINT("abs tol: ", settings.abstol)
		PRINT("rel tol: ", settings.reltol)
		PRINT("adpative rho: ", settings.adaptive)
		PRINT("max iter: ", settings.maxiter)

		PPRINT("MAKE OBJECTIVES, RESIDUALS, TOLERANCES", '.')
		obj = Objectives()
		res = Residuals()
		eps = Tolerances(m,n, atol=settings.abstol, rtol=settings.reltol)
		assert var_assert(obj,res,eps)
		PRINT("Objectives: ", obj)
		PRINT("Residuals: ", res)
		PRINT("Tolerances: ", eps)

		PPRINT("MAKE ADAPTIVE RHO PARAMETERS", '.')
		rhopar = AdaptiveRhoParameters()
		assert var_assert(rhopar)
		PRINT("a.r. params: ", rhopar)

		PPRINT("ITERATE: z_prev = z^k", '.')
		z.prev.copy_from(z.primal)
		linsys['sync'](z.prev.vec, z.primal.vec)
		PRINT(z.prev)
		PRINT(z.primal)
		assert all(z.primal.vec.py-z.prev.vec.py==0)

		PPRINT("PROX EVALUAION", '.')
		PRINT("BEFORE:")
		PRINT(z.primal12)
		
		xarg_ = z.primal.x.py - z.dual.x.py
		yarg_ = z.primal.y.py - z.dual.y.py

		xout_ = prox_eval_python(g.tolist(), settings.rho, xarg_)
		yout_ = prox_eval_python(f.tolist(), settings.rho, yarg_)

		Prox(settings.rho,z)
		z.sync()

		assert np.max(np.abs(z.primal12.x.py-xout_)) <= TEST_EPS
		assert np.max(np.abs(z.primal12.y.py-yout_)) <= TEST_EPS

		PRINT("AFTER")
		PRINT(z.primal12)

		PPRINT("PROJECTION", '.')
		PRINT("BEFORE:")
		PRINT(z.primal)

		pogs.utils.project_primal(Proj, z, alpha=settings.alpha)
		z.sync()
		assert norm(A.mat.py.dot(z.primal.x.py)-z.primal.y.py) <= TEST_EPS
		assert norm(A.mat.py.T.dot(z.dual.y.py)+z.dual.x.py) <= TEST_EPS

		PRINT("AFTER")
		PRINT(z.primal)

		PPRINT("DUAL UPDATE", '.')
		PRINT("BEFORE:")
		PRINT("Z_TILDE")
		PRINT(z.dual)
		PRINT("Z_TILDE_1/2")
		PRINT(z.dual12)
		
		z_ = np.copy(z.prev.vec.py)
		z1_= np.copy(z.primal.vec.py)
		z12_ = np.copy(z.primal12.vec.py)
		zt_ = np.copy(z.dual.vec.py)
		zt1_ = zt_+(settings.alpha*z12_+(1-settings.alpha)*z_)-z1_
		zt12_ = z12_-z_+zt_
		pogs.utils.update_dual(z,alpha=settings.alpha)
		z.sync()
		assert all(np.abs(z.dual.vec.py-zt1_) <= TEST_EPS)
		assert all(np.abs(z.dual12.vec.py-zt12_) <= TEST_EPS)

		PRINT("AFTER")
		PRINT("Z_TILDE")
		PRINT(z.dual)
		PRINT("Z_TILDE_1/2")
		PRINT(z.dual12 )


		PPRINT("CHECK CONVERGENCE:", '.')
		converged = pogs.utils.check_convergence(A,f,g,
			settings.rho,z,obj,res,eps,gapstop=settings.gapstop)	
		
		obj_py = func_eval_python(g.tolist(), z.primal12.x.py)
		obj_py += func_eval_python(f.tolist(), z.primal12.y.py)
		obj_gap_py = np.dot(z.primal12.vec.py, z.dual12.vec.py)
		obj_dua_py = obj_py-abs(obj_gap_py)

		assert abs(obj.p - obj_py) <= TEST_EPS
		assert abs(obj.d - obj_dua_py) <= TEST_EPS 
		assert abs(obj.gap - abs(obj_gap_py)) <= TEST_EPS

		assert abs(eps.p - (eps.atolm+eps.reltol*norm(z.primal.y.py))) <= TEST_EPS
		assert abs(eps.d - (eps.atoln+eps.reltol*norm(z.dual.x.py))) <= TEST_EPS
		assert abs(eps.gap - (eps.atolmn+eps.reltol*obj_py)) <= TEST_EPS

		res_p = norm(z.primal.vec.py - z.primal12.vec.py)
		res_d = norm(z.primal.vec.py - z.prev.vec.py)
		if res_d < eps.d and res_p < eps.p:
			res_p = norm(A.mat.py.dot(z.primal12.x.py) - \
								z.primal12.y.py)
			if res_p < eps.p:
				res_d = norm(A.mat.py.dot(z.dual12.y.py) + \
								z.dual12.x.py)

		assert abs(res.p - res_p) <= TEST_EPS
		assert abs(res.d - res_d) <= TEST_EPS
		assert abs(res.gap - abs(obj_gap_py)) <= TEST_EPS
		
		cvg_py = norm(A.mat.py.dot(z.primal12.x.py) - \
								z.primal12.y.py) <= eps.p and \
				norm(A.mat.py.dot(z.dual12.y.py) + \
								z.dual12.x.py) <= eps.d
		assert cvg_py == converged

		PRINT("Converged? ", converged )
		
		PPRINT("ITERATION INFO:", '.')
		PRINT(pogs.utils.header_string())
		PRINT(pogs.utils.iter_string(1, res, eps, obj))

		PPRINT("ADAPT RHO", '.')
		PRINT("Adaptive rho requested?", settings.adaptive)
		PRINT("rho before:", settings.rho)
		PRINT("Z_TILDE before:", z.dual)
		z_before = np.copy(z.dual.vec.py)
		rho_before = settings.rho
		if settings.adaptive:
			pogs.utils.adapt_rho(z, rhopar, 0, settings, res, eps)
			z.sync()
		z_after = np.copy(z.dual.vec.py)
		rho_after = settings.rho
		assert all(z_after / z_before - rho_before / rho_after <= TEST_EPS) or \
				all(z_after / z_before - rho_before / rho_after <= TEST_EPS)
		PRINT("rho after:", settings.rho)
		PRINT("Z_TILDE after:", z.dual)

		PPRINT("UPDATE INFO", '.')
		PRINT("info before: ", info)
		info.update(rho=settings.rho, obj=obj.p, 
			converged=converged, err=0, k=0)
		assert info.rho == settings.rho
		assert info.obj == obj.p
		assert info.converged == converged
		assert info.err == 0
		assert info.k == 0
		PRINT("info after: ", info )

		PPRINT("POGS INNER LOOP ROUTINE")
		settings.maxiter = 2000
		PRINT(settings)
		pogs.admm_loop(A.mat, Proj, Prox, z,settings, info, 
			pogs.utils.check_convergence(A.mat, f, g)) 	
		assert info.converged or info.k == settings.maxiter
		PRINT(info)

		PPRINT("POGS ROUTINE")

		A_copy = np.copy(A.mat.py)
		info_, output_, solver = pogs(A.mat, f, g,
			maxiter=settings.maxiter, reltol=settings.reltol)
		assert var_assert(solver, type=SolverState)
		assert var_assert(info_, type=SolverInfo)
		assert var_assert(output_, type=OutputVariables)
		assert info_.converged or info_.k == settings.maxiter

		res_p = norm(A_copy.dot(output_.x) - output_.y)
		res_d = norm(A_copy.T.dot(output_.nu) + output_.mu)

		if info_.converged:
			assert res_p / norm(output_.y) <= 10 * settings.reltol
			assert res_d / norm(output_.mu) <= 10 * settings.reltol or \
			norm(output_.mu) <= 10 * settings.reltol

		return True

	except:
		errors.append(format_exc())
		return False

def test_blocksplitting(errors, *args, **kwargs):
	print "BLOCK SPLITTING METHODS TESTING\n\n\n\n"
	verbose = '--verbose' in args
	(m,n)=kwargs['shape'] if 'shape' in kwargs else (None,None)
	A = np.load(kwargs['file']) if 'file' in kwargs else None
	floatbits = 32 if 'float' in args else 64

	success = blocksplitting_test(errors, m=m, n=n, A_in=A, 
		VERBOSE_TEST=verbose, gpu='gpu' in args, floatbits=floatbits)
	
	if isinstance(A, np.ndarray): A = A.T

	success &= blocksplitting_test(errors, m=n, n=m, A_in=A, 
			VERBOSE_TEST=verbose, gpu='gpu' in args, floatbits=floatbits)

	if success:
		print "...passed"
	else:
		print "...failed"
	return success

