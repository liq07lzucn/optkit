from optkit.compat import *

import os
import numpy as np
import ctypes as ct
import collections

from optkit.utils import proxutils
from optkit.tests.C.base import OptkitCTestCase
import optkit.tests.C.base_layer as okctest


ALPHA_DEFAULT = 1.7
RHO_DEFAULT = 1.
MAXITER_DEFAULT = 2000
ABSTOL_DEFAULT = 1e-4
RELTOL_DEFAULT = 1e-3
ADAPTIVE_DEFAULT = 1
GAPSTOP_DEFAULT = 0
WARMSTART_DEFAULT = 0
VERBOSE_DEFAULT = 2
SUPPRESS_DEFAULT = 0
RESUME_DEFAULT = 0

class PogsBaseTestContext(object):
    def __init__(self, libctx, m, n, obj='Abs'):
        lib = libctx.lib
        self._libctx = libctx
        self._f = okctest.CFunctionVectorContext(lib, m)
        self._g = okctest.CFunctionVectorContext(lib, n)
        self._objstring = obj
        self.params = collections.namedtuple(
                'TestParams',
                'shape z output info setings res tol obj f f_py g g_py')
        self.params.shape = (m, n)
        self.params.z = PogsVariablesLocal(m, n, lib.pyfloat)
        self.params.output = PogsOutputLocal(lib, m, n)
        self.params.info = lib.pogs_info()
        self.params.settings = settings = lib.pogs_settings()
        okctest.assert_noerr( lib.pogs_set_default_settings(settings) )
        self.params.settings.verbose = int(okctest.VERBOSE_TEST)
        self.params.res = lib.pogs_residuals()
        self.params.tol = lib.pogs_tolerances()
        self.params.obj = lib.pogs_objective_values()

    def __enter__(self):
        m, n = self.params.shape
        lib = self.lib = self._libctx.__enter__()
        self.f = self._f.__enter__()
        self.g = self._g.__enter__()
        f, f_py, f_ptr = self.f.cptr, self.f.py, self.f.pyptr
        g, g_py, g_ptr = self.g.cptr, self.g.py, self.g.pyptr

        h = lib.function_enums.dict[self._objstring]
        asymm = 1 + int('Asymm' in self._objstring)
        for i in xrange(m):
            f_py[i] = lib.function(h, 1, 1, 1, 0, 0, asymm)
        for j in xrange(n):
            g_py[j] = lib.function(
                    lib.function_enums.IndGe0, 1, 0, 1, 0, 0, 1)
        okctest.assert_noerr( lib.function_vector_memcpy_va(f, f_ptr) )
        okctest.assert_noerr( lib.function_vector_memcpy_va(g, g_ptr) )
        self.params.f = f
        self.params.g = g
        self.params.f_py = f_py
        self.params.g_py = g_py
        return self

    def __exit__(self, *exc):
        self._f.__exit__(*exc)
        self._g.__exit__(*exc)
        self._libctx.__exit__(*exc)

class PogsVariablesLocal():
    def __init__(self, m, n, pytype):
        self.m = m
        self.n = n
        self.z = np.zeros(m + n).astype(pytype)
        self.z12 = np.zeros(m + n).astype(pytype)
        self.zt = np.zeros(m + n).astype(pytype)
        self.zt12 = np.zeros(m + n).astype(pytype)
        self.prev = np.zeros(m + n).astype(pytype)
        self.d = np.zeros(m).astype(pytype)
        self.e = np.zeros(n).astype(pytype)

    @property
    def x(self):
        return self.z[self.m:]

    @property
    def y(self):
        return self.z[:self.m]

    @property
    def x12(self):
        return self.z12[self.m:]

    @property
    def y12(self):
        return self.z12[:self.m]

    @property
    def xt(self):
        return self.zt[self.m:]

    @property
    def yt(self):
        return self.zt[:self.m]

    @property
    def xt12(self):
        return self.zt12[self.m:]

    @property
    def yt12(self):
        return self.zt12[:self.m]

class PogsOutputLocal():
    def __init__(self, lib, m, n):
        self.x = np.zeros(n).astype(lib.pyfloat)
        self.y = np.zeros(m).astype(lib.pyfloat)
        self.mu = np.zeros(n).astype(lib.pyfloat)
        self.nu = np.zeros(m).astype(lib.pyfloat)
        self.ptr = lib.pogs_output(self.x.ctypes.data_as(lib.ok_float_p),
                                   self.y.ctypes.data_as(lib.ok_float_p),
                                   self.mu.ctypes.data_as(lib.ok_float_p),
                                   self.nu.ctypes.data_as(lib.ok_float_p))

def load_to_local(lib, py_vector, c_vector):
    okctest.assert_noerr( lib.vector_memcpy_av(
            py_vector.ctypes.data_as(lib.ok_float_p), c_vector, 1) )

def load_all_local(lib, py_vars, solver):
    if not isinstance(py_vars, PogsVariablesLocal):
        raise TypeError('argument "py_vars" must be of type {}'.format(
                        PogsVariablesLocal))
    elif 'pogs_solver_p' not in lib.__dict__:
        raise ValueError('argument "lib" must contain field named '
                         '"pogs_solver_p"')
    elif not isinstance(solver, lib.pogs_solver_p):
        raise TypeError('argument "solver" must be of type {}'.format(
                        lib.pogs_solver_p))

    z = solver.contents.z
    W = solver.contents.W
    load_to_local(lib, py_vars.z, z.contents.primal.contents.vec)
    load_to_local(lib, py_vars.z12, z.contents.primal12.contents.vec)
    load_to_local(lib, py_vars.zt, z.contents.dual.contents.vec)
    load_to_local(lib, py_vars.zt12, z.contents.dual12.contents.vec)
    load_to_local(lib, py_vars.prev, z.contents.prev.contents.vec)
    load_to_local(lib, py_vars.d, W.contents.d)
    load_to_local(lib, py_vars.e, W.contents.e)

class EquilibratedMatrix(object):
    def __init__(self, d, A, e):
        self.dot = lambda x: d * A.dot(e * x)
        self.shape = A.shape
        self.transpose = lambda: EquilibratedMatrix(e, A.T, d)
    @property
    def T(self):
        return self.transpose()

class OptkitCPogsTestCase(OptkitCTestCase):
    def assert_default_settings(self, lib):
        settings = lib.pogs_settings()

        TOL = 1e-3
        self.assertCall( lib.pogs_set_default_settings(settings) )
        self.assertScalarEqual(settings.alpha, ALPHA_DEFAULT, TOL )
        self.assertScalarEqual(settings.rho, RHO_DEFAULT, TOL )
        self.assertScalarEqual(settings.abstol, ABSTOL_DEFAULT, TOL )
        self.assertScalarEqual(settings.reltol, RELTOL_DEFAULT, TOL )
        self.assertScalarEqual(settings.maxiter, MAXITER_DEFAULT,
                                     TOL )
        self.assertScalarEqual(settings.verbose, VERBOSE_DEFAULT,
                                     TOL )
        self.assertScalarEqual(settings.suppress, SUPPRESS_DEFAULT,
                                     TOL )
        self.assertScalarEqual(settings.adaptiverho,
                                     ADAPTIVE_DEFAULT, TOL )
        self.assertScalarEqual(settings.gapstop, GAPSTOP_DEFAULT, TOL )
        self.assertScalarEqual(settings.warmstart, WARMSTART_DEFAULT,
                                     TOL )
        self.assertScalarEqual(settings.resume, RESUME_DEFAULT, TOL )

    def assert_pogs_scaling(self, lib, solver, test_params):
        f, f_py = test_params.f, test_params.f_py
        g, g_py = test_params.g, test_params.g_py
        local_vars = test_params.z
        m, n = test_params.shape

        def fv_list2arrays(function_vector_list):
            fv = function_vector_list
            fvh = np.array([fv_.h for fv_ in fv])
            fva = np.array([fv_.a for fv_ in fv])
            fvb = np.array([fv_.b for fv_ in fv])
            fvc = np.array([fv_.c for fv_ in fv])
            fvd = np.array([fv_.d for fv_ in fv])
            fve = np.array([fv_.e for fv_ in fv])
            return fvh, fva, fvb, fvc, fvd, fve

        # record original function vector parameters
        f_list = [lib.function(*f_) for f_ in f_py]
        g_list = [lib.function(*f_) for f_ in g_py]
        f_h0, f_a0, f_b0, f_c0, f_d0, f_e0 = fv_list2arrays(f_list)
        g_h0, g_a0, g_b0, g_c0, g_d0, g_e0 = fv_list2arrays(g_list)

        # copy function vector
        f_py_ptr = f_py.ctypes.data_as(lib.function_p)
        g_py_ptr = g_py.ctypes.data_as(lib.function_p)
        self.assertCall( lib.function_vector_memcpy_va(f, f_py_ptr) )
        self.assertCall( lib.function_vector_memcpy_va(g, g_py_ptr) )

        # scale function vector
        self.assertCall( lib.pogs_scale_objectives(
                solver.contents.f, solver.contents.g,
                solver.contents.W.contents.d,
                solver.contents.W.contents.e, f, g) )

        # retrieve scaled function vector parameters
        self.assertCall( lib.function_vector_memcpy_av(f_py_ptr,
                                                       solver.contents.f) )
        self.assertCall( lib.function_vector_memcpy_av(g_py_ptr,
                                                       solver.contents.g) )
        f_list = [lib.function(*f_) for f_ in f_py]
        g_list = [lib.function(*f_) for f_ in g_py]
        f_h1, f_a1, f_b1, f_c1, f_d1, f_e1 = fv_list2arrays(f_list)
        g_h1, g_a1, g_b1, g_c1, g_d1, g_e1 = fv_list2arrays(g_list)

        # retrieve scaling
        load_all_local(lib, local_vars, solver)

        # scaled vars
        self.assertVecEqual( f_a0, local_vars.d * f_a1, self.ATOLM, self.RTOL )
        self.assertVecEqual( f_d0, local_vars.d * f_d1, self.ATOLM, self.RTOL )
        self.assertVecEqual( f_e0, local_vars.d * f_e1, self.ATOLM, self.RTOL )
        self.assertVecEqual( g_a0 * local_vars.e, g_a1, self.ATOLN, self.RTOL )
        self.assertVecEqual( g_d0 * local_vars.e, g_d1, self.ATOLN, self.RTOL )
        self.assertVecEqual( g_e0 * local_vars.e, g_e1, self.ATOLN, self.RTOL )

        # unchanged vars
        self.assertVecEqual( f_h0, f_h1, self.ATOLM, self.RTOL )
        self.assertVecEqual( f_b0, f_b1, self.ATOLM, self.RTOL )
        self.assertVecEqual( f_c0, f_c1, self.ATOLM, self.RTOL )
        self.assertVecEqual( g_h0, g_h1, self.ATOLN, self.RTOL )
        self.assertVecEqual( g_b0, g_b1, self.ATOLN, self.RTOL )
        self.assertVecEqual( g_c0, g_c1, self.ATOLN, self.RTOL )

    def build_A_equil(self, lib, solver_work, A_orig):
        m, n = A_orig.shape
        d_local = np.zeros(m).astype(lib.pyfloat)
        e_local = np.zeros(n).astype(lib.pyfloat)
        load_to_local(lib, d_local, solver_work.contents.d)
        load_to_local(lib, e_local, solver_work.contents.e)
        return EquilibratedMatrix(d_local, A_orig, e_local,)

    def assert_equilibrate_matrix(self, lib, solver_work, A_orig):
        m, n = A_orig.shape
        d_local = np.zeros(m).astype(lib.pyfloat)
        e_local = np.zeros(n).astype(lib.pyfloat)
        load_to_local(lib, d_local, solver_work.contents.d)
        load_to_local(lib, e_local, solver_work.contents.e)

        x, x_py, x_ptr = self.register_vector(lib, n, 'x', random=True)
        y, y_py, y_ptr = self.register_vector(lib, m, 'y')

        if lib.py_pogs_impl == 'dense':
            A = solver_work.contents.A
            hdl = solver_work.contents.linalg_handle
            tr = lib.enums.CblasNoTrans
            self.assertCall( lib.blas_gemv(hdl, tr, 1, A, x, 0, y) )
        elif lib.py_pogs_impl == 'abstract':
            opA = solver_work.contents.A
            self.assertCall( opA.contents.apply(opA.contents.data, x, y) )
        else:
            raise ValueError('UNKNOWN POGS IMPLEMENTATION')

        load_to_local(lib, y_py, y)

        DAEX = d_local * A_orig.dot(e_local * x_py)
        self.assertVecEqual( y_py, DAEX, self.ATOLM, self.RTOL )
        self.free_vars('x', 'y')

    def assert_apply_matrix(self, lib, work, A_equil):
        m, n = A_equil.shape
        x, x_py, _ = self.register_vector(lib, n, 'x', random=True)
        y, y_py, _ = self.register_vector(lib, m, 'y', random=True)
        alpha = np.random.random()
        beta = np.random.random()

        if lib.py_pogs_impl == 'dense':
            self.assertCall( lib.pogs_dense_apply_matrix(
                    work, alpha, x, beta, y) )
        elif lib.py_pogs_impl == 'abstract':
            self.assertCall( lib.pogs_abstract_apply_matrix(
                    work, alpha, x, beta, y) )
        else:
            raise ValueError('UNKNOWN POGS IMPLEMENTATION')

        AXPY = alpha * A_equil.dot(x_py) + beta * y_py
        load_to_local(lib, y_py, y)
        self.assertVecEqual( y_py, AXPY, self.ATOLM, self.RTOL )

        self.free_vars('x', 'y')

    def assert_apply_adjoint(self, lib, work, A_equil):
        m, n = A_equil.shape
        x, x_py, _ = self.register_vector(lib, n, 'x', random=True)
        y, y_py, _ = self.register_vector(lib, m, 'y', random=True)
        alpha = np.random.random()
        beta = np.random.random()

        if lib.py_pogs_impl == 'dense':
            self.assertCall( lib.pogs_dense_apply_adjoint(
                    work, alpha, y, beta, x) )
        elif lib.py_pogs_impl == 'abstract':
            self.assertCall( lib.pogs_abstract_apply_adjoint(
                    work, alpha, y, beta, x) )
        else:
            raise ValueError('UNKNOWN POGS IMPLEMENTATION')

        ATYPX = alpha * A_equil.T.dot(y_py) + beta * x_py
        load_to_local(lib, x_py, x)
        self.assertVecEqual( x_py, ATYPX, self.ATOLN, self.RTOL )

        self.free_vars('x', 'y')

    def assert_project_graph(self, lib, work, A_equil):
        m, n = A_equil.shape
        DIGITS = 7 - 2 * lib.FLOAT
        RTOL = 10**(-DIGITS)
        ATOLM = RTOL * m**0.5

        x_in, _, _ = self.register_vector(lib, n, 'x_in', random=True)
        y_in, _, _ = self.register_vector(lib, m, 'y_in', random=True)
        x_out, x_out_py, _ = self.register_vector(lib, n, 'x_out')
        y_out, y_out_py, _ = self.register_vector(lib, m, 'y_out')

        if lib.py_pogs_impl == 'dense':
            self.assertCall( lib.pogs_dense_project_graph(
                    work, x_in, y_in, x_out, y_out, RTOL) )
        elif lib.py_pogs_impl == 'abstract':
            self.assertCall( lib.pogs_abstract_project_graph(
                    work, x_in, y_in, x_out, y_out, RTOL) )
        else:
            raise ValueError('UNKNOWN POGS IMPLEMENTATION')

        load_to_local(lib, x_out_py, x_out)
        load_to_local(lib, y_out_py, y_out)
        AX = A_equil.dot(x_out_py)
        self.assertVecEqual( y_out_py, AX, ATOLM, RTOL )

        self.free_vars('x_in', 'y_in', 'x_out', 'y_out')

    def assert_pogs_primal_update(self, lib, solver, local_vars):
        """primal update test

            set

                z^k = z^{k-1}

            check

                z^k == z^{k-1}

            holds elementwise
        """
        self.assertCall( lib.pogs_primal_update(solver.contents.z) )
        load_all_local(lib, local_vars, solver)
        self.assertVecEqual( local_vars.z, local_vars.prev, self.ATOLMN, self.RTOL )

    def assert_pogs_prox(self, lib, solver, test_params):
        """proximal operator application test

            set

                x^{k+1/2} = prox_{g, rho}(x^k - xt^k)
                y^{k+1/2} = prox_{f, rho}(y^k - yt^k)

            in C and Python, check that results agree
        """
        f, f_py = test_params.f, test_params.f_py
        g, g_py = test_params.g, test_params.g_py
        local_vars = test_params.z
        z = solver.contents.z
        rho = test_params.settings.rho

        hdl = solver.contents.linalg_handle
        load_all_local(lib, local_vars, solver)

        self.assertCall( lib.pogs_prox(hdl, f, g, z, rho) )
        load_all_local(lib, local_vars, solver)

        f_list = [lib.function(*f_) for f_ in f_py]
        g_list = [lib.function(*f_) for f_ in g_py]
        for i in xrange(len(f_py)):
            f_list[i].a *= local_vars.d[i]
            f_list[i].d *= local_vars.d[i]
            f_list[i].e *= local_vars.d[i]
        for j in xrange(len(g_py)):
            g_list[j].a /= local_vars.e[j]
            g_list[j].d /= local_vars.e[j]
            g_list[j].e /= local_vars.e[j]

        x_arg = local_vars.x - local_vars.xt
        y_arg = local_vars.y - local_vars.yt
        x_out = proxutils.prox_eval_python(g_list, rho, x_arg)
        y_out = proxutils.prox_eval_python(f_list, rho, y_arg)
        self.assertVecEqual( local_vars.x12, x_out, self.ATOLN, self.RTOL )
        self.assertVecEqual( local_vars.y12, y_out, self.ATOLM, self.RTOL )

    def assert_pogs_project_graph(self, lib, solver, A_equil, local_vars):
        """primal projection test
            set
                (x^{k+1}, y^{k+1}) = proj_{y=Ax}(x^{k+1/2}, y^{k+1/2})
            check that
                y^{k+1} == A * x^{k+1}
            holds to numerical tolerance
        """
        self.assertCall( lib.pogs_project_graph(
                solver.contents.W, solver.contents.z,
                solver.contents.settings.contents.alpha, self.RTOL) )

        load_all_local(lib, local_vars, solver)
        self.assertVecEqual(
                A_equil.dot(local_vars.x), local_vars.y, self.ATOLM, self.RTOL)

    def assert_pogs_dual_update(self, lib, solver, local_vars):
        """dual update test

            set

                zt^{k+1/2} = z^{k+1/2} - z^{k} + zt^{k}
                zt^{k+1} = zt^{k} - z^{k+1} + alpha * z^{k+1/2} +
                                              (1-alpha) * z^k

            in C and Python, check that results agree
        """
        blas_handle = solver.contents.linalg_handle
        z = solver.contents.z

        load_all_local(lib, local_vars, solver)
        alpha = solver.contents.settings.contents.alpha
        zt12_py = local_vars.z12 - local_vars.prev + local_vars.zt
        zt_py = local_vars.zt - local_vars.z + (
                    alpha * local_vars.z12 + (1-alpha) * local_vars.prev)

        self.assertCall( lib.pogs_dual_update(blas_handle, z, alpha) )
        load_all_local(lib, local_vars, solver)
        self.assertVecEqual( local_vars.zt12, zt12_py, self.ATOLMN, self.RTOL )
        self.assertVecEqual( local_vars.zt, zt_py, self.ATOLMN, self.RTOL )


    def assert_pogs_adapt_rho(self, lib, solver, test_params):
        """adaptive rho test

            rho is rescaled
            dual variable is rescaled accordingly

            the following equality should hold elementwise:

                rho_before * zt_before == rho_after * zt_after

            (here zt, or z tilde, is the dual variable)
        """
        residuals = test_params.res
        tolerances = test_params.tol
        local_vars = test_params.z

        rho_p = lib.ok_float_p()
        rho_p.contents = lib.ok_float(solver.contents.rho)

        z = solver.contents.z
        settings = solver.contents.settings

        if settings.contents.adaptiverho:
            rho_params = lib.adapt_params(1.05, 0, 0, 1)
            zt_before = local_vars.zt
            rho_before = solver.contents.rho
            self.assertCall( lib.pogs_adapt_rho(
                    z, rho_p, rho_params, solver.contents.settings, residuals,
                    tolerances, 1) )
            load_all_local(lib, local_vars, solver)
            zt_after = local_vars.zt
            rho_after = rho_p.contents
            self.assertVecEqual(
                    rho_after * zt_after, rho_before * zt_before, self.ATOLMN,
                    self.RTOL )

    def assert_pogs_check_convergence(self, lib, solver, A_equil, test_params):
        """convergence test

            (1) set

                obj_primal = f(y^{k+1/2}) + g(x^{k+1/2})
                obj_gap = <z^{k+1/2}, zt^{k+1/2}>
                obj_dual = obj_primal - obj_gap

                tol_primal = abstol * sqrt(m) + reltol * ||y^{k+1/2}||
                tol_dual = abstol * sqrt(n) + reltol * ||xt^{k+1/2}||

                res_primal = ||Ax^{k+1/2} - y^{k+1/2}||
                res_dual = ||A'yt^{k+1/2} + xt^{k+1/2}||

            in C and Python, check that these quantities agree

            (2) calculate solver convergence,

                    res_primal <= tol_primal
                    res_dual <= tol_dual,

                in C and Python, check that the results agree
        """
        f, f_py = test_params.f, test_params.f_py
        g, g_py = test_params.g, test_params.g_py
        residuals = test_params.res
        tolerances = test_params.tol
        objectives = test_params.obj
        local_vars = test_params.z

        f_list = [lib.function(*f_) for f_ in f_py]
        g_list = [lib.function(*g_) for g_ in g_py]

        converged = np.zeros(1, dtype=int)
        cvg_ptr = converged.ctypes.data_as(ct.POINTER(ct.c_int))

        self.assertCall( lib.pogs_check_convergence(
                solver, objectives, residuals, tolerances, cvg_ptr) );

        load_all_local(lib, local_vars, solver)
        obj_py = proxutils.func_eval_python(g_list, local_vars.x12)
        obj_py += proxutils.func_eval_python(f_list, local_vars.y12)
        obj_gap_py = abs(local_vars.z12.dot(local_vars.zt12))
        obj_dua_py = obj_py - obj_gap_py

        tol_primal = tolerances.atolm + (
                tolerances.reltol * np.linalg.norm(local_vars.y12))
        tol_dual = tolerances.atoln + (
                tolerances.reltol * np.linalg.norm(local_vars.xt12))

        self.assertScalarEqual( objectives.gap, obj_gap_py, self.RTOL )
        self.assertScalarEqual( tolerances.primal, tol_primal, self.RTOL )
        self.assertScalarEqual( tolerances.dual, tol_dual, self.RTOL )

        Ax = A_equil.dot(local_vars.x12)
        ATnu = A_equil.T.dot(local_vars.yt12)
        res_primal = np.linalg.norm(Ax - local_vars.y12)
        res_dual = np.linalg.norm(ATnu + local_vars.xt12)

        self.assertScalarEqual( residuals.primal, res_primal, self.RTOL )
        self.assertScalarEqual( residuals.dual, res_dual, self.RTOL )
        self.assertScalarEqual( residuals.gap, abs(obj_gap_py), self.RTOL )

        converged_py = res_primal <= tolerances.primal and \
                       res_dual <= tolerances.dual

        self.assertEqual( converged, converged_py )

    def assert_pogs_unscaling(self, lib, output, solver, local_vars):
        """pogs unscaling test

            solver variables are unscaled and copied to output.

            the following equalities should hold elementwise:

                x^{k+1/2} * e - x_out == 0
                y^{k+1/2} / d - y_out == 0
                -rho * xt^{k+1/2} / e - mu_out == 0
                -rho * yt^{k+1/2} * d - nu_out == 0
        """
        if not isinstance(solver, lib.pogs_solver_p):
            raise TypeError('argument "solver" must be of type {}'.format(
                            lib.pogs_solver_p))

        if not isinstance(output, PogsOutputLocal):
            raise TypeError('argument "output" must be of type {}'.format(
                            PogsOutputLocal))

        if not isinstance(local_vars, PogsVariablesLocal):
            raise TypeError('argument "local_vars" must be of type {}'.format(
                            PogsVariablesLocal))

        rho = solver.contents.rho
        suppress = solver.contents.settings.contents.suppress
        load_all_local(lib, local_vars, solver)

        if 'pogs_matrix_p' in lib.__dict__:
            solver_work = solver.contents.M
        elif 'pogs_work_p' in lib.__dict__:
            solver_work = solver.contents.W
        else:
            raise ValueError('argument "lib" must contain a field named'
                             '"pogs_matrix_p" or "pogs_work_p"')

        self.assertCall( lib.pogs_unscale_output(
                output.ptr, solver.contents.z, solver_work.contents.d,
                solver_work.contents.e, rho, suppress) )

        self.assertVecEqual(
                local_vars.x12 * local_vars.e, output.x,
                self.ATOLN, self.RTOL )
        self.assertVecEqual(
                local_vars.y12, local_vars.d * output.y,
                self.ATOLM, self.RTOL )
        self.assertVecEqual(
                -rho * local_vars.xt12, local_vars.e * output.mu,
                self.ATOLN, self.RTOL )
        self.assertVecEqual(
                -rho * local_vars.yt12 * local_vars.d, output.nu,
                self.ATOLM, self.RTOL )

    def assert_pogs_convergence(self, lib, A_orig, settings, output):
        RFP = repeat_factor_primal = 2.**(okctest.TEST_ITERATE)
        RFD = repeat_factor_dual = 3.**(okctest.TEST_ITERATE)

        m, n = self.shape
        rtol = settings.reltol
        atolm = settings.abstol * (m**0.5)
        atoln = settings.abstol * (n**0.5)

        P = 10 * 1.5**int(lib.FLOAT) * 1.5**int(lib.GPU);
        D = 20 * 1.5**int(lib.FLOAT) * 1.5**int(lib.GPU);

        Ax = A_orig.dot(output.x)
        ATnu = A_orig.T.dot(output.nu)
        self.assertVecEqual( Ax, output.y, RFP * atolm, RFP * P * rtol )
        self.assertVecEqual( ATnu, -output.mu, RFD * atoln, RFD * D * rtol )

    def assert_scaled_variables(self, A_equil, x0, nu0, local_vars, rho):
        x_scal = local_vars.e * local_vars.x
        nu_scal = -rho * local_vars.d * local_vars.yt
        y0_unscal = A_equil.dot(x0 / local_vars.e)
        mu0_unscal = A_equil.T.dot(nu0 / (rho * local_vars.d))

        self.assertVecEqual( x0, x_scal, self.ATOLN, self.RTOL )
        self.assertVecEqual( nu0, nu_scal, self.ATOLM, self.RTOL )
        self.assertVecEqual( y0_unscal, local_vars.y, self.ATOLM, self.RTOL )
        self.assertVecEqual( mu0_unscal, local_vars.xt, self.ATOLN, self.RTOL )

    def assert_coldstart_components(self, test_context):
        lib = test_context.lib
        A = test_context.A_dense
        m, n = A.shape
        solver = test_context.solver
        W = solver.contents.W
        params = test_context.params

        self.assertCall( lib.pogs_initialize_conditions(
                    params.obj, params.res, params.tol, params.settings, m, n) )

        self.assert_equilibrate_matrix(lib, W, A)
        A_equil = self.build_A_equil(lib, W, A)
        self.assert_apply_matrix(lib, W, A_equil)
        self.assert_apply_adjoint(lib, W, A_equil)
        self.assert_project_graph(lib, W, A_equil)
        self.assert_pogs_scaling(lib, solver, params)
        self.assert_pogs_primal_update(lib, solver, params.z)
        self.assert_pogs_prox(lib, solver, params)
        self.assert_pogs_project_graph(lib, solver, A_equil, params.z)
        self.assert_pogs_dual_update(lib, solver, params.z)
        self.assert_pogs_check_convergence(lib, solver, A_equil, params)
        self.assert_pogs_adapt_rho(lib, solver, params)
        self.assert_pogs_unscaling(lib, params.output, solver, params.z)

    def assert_pogs_call(self, test_context):
        ctx = test_context
        lib = ctx.lib
        solver = ctx.solver
        params = ctx.params
        f, g = params.f, params.g
        settings, info, output = params.settings, params.info, params.output

        self.assertCall( lib.pogs_solve(solver, params.f, params.g, settings, info, output.ptr) )
        if info.converged:
            self.assert_pogs_convergence(lib, ctx.A_dense, settings, output)

    def assert_pogs_warmstart_scaling(self, test_context):
        lib = test_context.lib
        A = test_context.A_dense
        solver = test_context.solver
        test_params = test_context.params

        A_equil = self.build_A_equil(lib, solver.contents.W, A)

        m, n = A_equil.shape
        settings = test_params.settings
        local_vars = test_params.z
        f, g, = test_params.f, test_params.g
        info, output = test_params.info, test_params.output

        # TEST POGS_SET_Z0
        rho = settings.rho
        x0, x0_ptr = self.gen_py_vector(lib, n, random=True)
        nu0, nu0_ptr = self.gen_py_vector(lib, m, random=True)
        settings.x0 = x0_ptr
        settings.nu0 = nu0_ptr
        self.assertCall( lib.pogs_update_settings(solver.contents.settings,
                                             ct.byref(settings)) )
        self.assertCall( lib.pogs_set_z0(solver) )
        load_all_local(lib, local_vars, solver)
        self.assert_scaled_variables(A_equil, x0, nu0, local_vars, rho)

        # TEST SOLVER WARMSTART
        x0, x0_ptr = self.gen_py_vector(lib, n, random=True)
        nu0, nu0_ptr = self.gen_py_vector(lib, m, random=True)
        settings.x0 = x0_ptr
        settings.nu0 = nu0_ptr
        settings.warmstart = 1
        settings.maxiter = 0

        if okctest.VERBOSE_TEST:
            print('\nwarm start variable loading test (maxiter = 0)')
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                                        output.ptr) )
        rho = solver.contents.rho
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )
        load_all_local(lib, local_vars, solver)
        self.assert_scaled_variables(A_equil, x0, nu0, local_vars, rho)

    def assert_pogs_warmstart(self, test_context):
        lib = test_context.lib
        solver = test_context.solver
        test_params = test_context.params

        f = test_params.f
        g = test_params.g
        info = test_params.info
        settings = test_params.settings
        output = test_params.output

        settings.verbose = 1

        # COLD START
        print('\ncold')
        settings.warmstart = 0
        settings.maxiter = MAXITER_DEFAULT
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

        # REPEAT
        print('\nrepeat')
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

        # RESUME
        print('\nresume')
        settings.resume = 1
        settings.rho = info.rho
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

        # WARM START: x0
        print('\nwarm start x0')
        settings.resume = 0
        settings.rho = 1
        settings.x0 = output.x.ctypes.data_as(lib.ok_float_p)
        settings.warmstart = 1
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

        # WARM START: x0, rho
        print('\nwarm start x0, rho')
        settings.resume = 0
        settings.rho = info.rho
        settings.x0 = output.x.ctypes.data_as(lib.ok_float_p)
        settings.warmstart = 1
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

        # WARM START: x0, nu0
        print('\nwarm start x0, nu0')
        settings.resume = 0
        settings.rho = 1
        settings.x0 = output.x.ctypes.data_as(lib.ok_float_p)
        settings.nu0 = output.nu.ctypes.data_as(lib.ok_float_p)
        settings.warmstart = 1
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

        # WARM START: x0, nu0
        print('\nwarm start x0, nu0, rho')
        settings.resume = 0
        settings.rho = info.rho
        settings.x0 = output.x.ctypes.data_as(lib.ok_float_p)
        settings.nu0 = output.nu.ctypes.data_as(lib.ok_float_p)
        settings.warmstart = 1
        self.assertCall( lib.pogs_solve(solver, f, g, settings, info,
                         output.ptr) )
        self.assertEqual( info.err, 0 )
        self.assertTrue( info.converged or info.k >= settings.maxiter )

    def assert_pogs_accelerate(self, test_context):
        ctx = test_context
        lib = ctx.lib
        solver = ctx.solver
        state = solver.contents.z.contents.state
        params = ctx.params
        f, g = params.f, params.g
        settings, info, output = params.settings, params.info, params.output
        settings.verbose = 1
        settings.maxiter = 5000

        print('POGS, -adaptive rho, -anderson')
        okctest.assert_noerr( lib.vector_set_all(state, 0.) )
        settings.adaptiverho = 0
        settings.accelerate = 0
        settings.rho = 1
        settings.warmstart = 0
        settings.resume = 0
        self.assertCall( lib.pogs_solve(solver, params.f, params.g, settings, info, output.ptr) )
        # if info.converged:
        #     self.assert_pogs_convergence(lib, ctx.A_dense, settings, output)

        print('POGS, +adaptive rho, -anderson')
        okctest.assert_noerr( lib.vector_set_all(state, 0.) )
        settings.adaptiverho = 1
        settings.accelerate = 0
        settings.rho = 1
        settings.warmstart = 0
        settings.resume = 0
        self.assertCall( lib.pogs_solve(solver, params.f, params.g, settings, info, output.ptr) )
        # if info.converged:
        #     self.assert_pogs_convergence(lib, ctx.A_dense, settings, output)

        print('POGS, -adaptive rho, +anderson')
        okctest.assert_noerr( lib.vector_set_all(state, 0.) )
        settings.adaptiverho = 0
        settings.accelerate = 1
        settings.rho = 1
        settings.warmstart = 0
        settings.resume = 0
        self.assertCall( lib.pogs_solve(solver, params.f, params.g, settings, info, output.ptr) )
        # if info.converged:
        #     self.assert_pogs_convergence(lib, ctx.A_dense, settings, output)

        print('POGS, +adaptive rho, +anderson')
        okctest.assert_noerr( lib.vector_set_all(state, 0.) )
        settings.adaptiverho = 1
        settings.accelerate = 1
        settings.rho = 1
        settings.warmstart = 0
        settings.resume = 0
        self.assertCall( lib.pogs_solve(solver, params.f, params.g, settings, info, output.ptr) )
        # if info.converged:
        #     self.assert_pogs_convergence(lib, ctx.A_dense, settings, output)

    def assert_pogs_unified(self, test_context):
        ctx = test_context
        lib = ctx.lib
        data = ctx.data
        flags = ctx.flags
        params = ctx.params
        f, g = params.f, params.g
        settings, info, output = params.settings, params.info, params.output

        settings.verbose = 1
        self.assertCall(lib.pogs(data, flags, f, g, settings, info, output.ptr, 0))
        if info.converged:
            self.assert_pogs_convergence(lib, ctx.A_dense, settings, output)

    def assert_pogs_io(self, test_context):
        ctx = test_context.lib
        lib = ctx.lib
        A = ctx.A_dense
        solver = ctx.solver
        params = ctx.params
        f, g = params.f, params.g
        settings, info, output = params.settings, params.info, params.output

        m, n = A.shape
        x_rand, _ = self.gen_py_vector(lib, n)
        nu_rand, _ = self.gen_py_vector(lib, m)
        settings.verbose = 1

        # solve
        print('initial solve -> export data')
        self.assertCall( lib.pogs_solve(
                solver, f, g, settings, info, output.ptr) )
        k_orig = info.k

        # EXPORT/IMPORT STATE
        n_state = solver.contents.z.contents.state.contents.size
        state_out = np.array(n_state, dtype=lib.pyfloat)
        rho_out = np.array(1, dtype=lib.pyfloat)

        state_ptr = lib.ok_float_pointerize(state_out)
        rho_ptr = lib.ok_float_pointerize(rho_out)

        okctest.assert_noerr( lib.pogs_solver_save_state(
                state_ptr, rho_ptr, solver) )

        build_solver = lambda: lib.pogs_init(ctx.data, ctx.flags)
        free_solver = lambda s: lib.pogs_finish(s, 0)
        with okctest.CVariableContext(build_solver, free_solver) as solver2:
            settings.resume = 1
            okctest.assert_noerr( lib.pogs_solver_load_state(
                    solver2, state_ptr, rho_ptr[0]))
            okctest.assert_noerr( lib.pogs_solve(
                    solver2, f, g, settings, info, output.ptr) )

            assert (info.k <= k_orig or not info.converged)

        # EXPORT/IMPORT SOLVER
        priv_data = lib.pogs_solver_priv_data()
        flags = lib.pogs_solver_flags()

        okctest.assert_noerr( lib.pogs_export_solver(
                priv_data, state_ptr, rho_ptr, flags, solver))

        build_solver = lambda: lib.pogs_load_solver(
                priv_data, state_ptr, rho_out[0], flags)
        with okctest.CVariableContext(build_solver, free_solver) as solver3:
            settings.resume = 1
            okctest.assert_noerr( lib.pogs_solve(
                    solver3, f, g, settings, info, output.ptr) )
