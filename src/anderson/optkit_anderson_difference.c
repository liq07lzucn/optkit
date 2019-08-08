#include "optkit_anderson_difference.h"

#ifdef __cplusplus
extern "C" {
#endif

ok_status anderson_difference_solve(void *blas_hdl, void *lapack_hdl, matrix *DX,
	matrix *DG, matrix *DXDG, vector *g, vector *gamma, int_vector *pivot)
{
	ok_status err = OPTKIT_SUCCESS;
	/* DXDG = DX' * DG */
	OK_CHECK_ERR( err, blas_gemm(blas_hdl, CblasTrans,
		CblasNoTrans, kOne, DX, DG, kZero, DXDG) );

	/* gamma := DX'g (for now) */
	OK_CHECK_ERR( err, blas_gemv(blas_hdl, CblasTrans, kOne, DX, g,
		kZero, gamma) );

	/* gamma = inv(DX'DG)DX'g */
	if (!err)
		err = lapack_solve_LU_flagged(lapack_hdl, DXDG, gamma, pivot,
			kANDERSON_SILENCE_LU);
	if (!kANDERSON_SILENCE_LU)
		OK_SCAN_ERR(err);

	return err;
}

ok_status anderson_difference_mix(void *blas_hdl, matrix *DF,
	vector *gamma, vector *x)
{
	OK_RETURNIF_ERR( blas_gemv(blas_hdl, CblasNoTrans, -kOne, DF, gamma,
		kOne, x) );
	return OPTKIT_SUCCESS;
}


//>>>>>>>>>>>>>>>>>>
ok_status anderson_difference_accelerate_template(void *blas_handle,
	void *lapack_handle, matrix *DX, matrix *DF, matrix *DG, matrix *DXDG,
	vector *f, vector *g, vector *x, vector *gamma,
        int_vector *pivot, size_t *iter, vector *iterate, vector *x_reduced,
        size_t n_reduction,
        ok_status (* x_reduction)(vector *x_rdx, vector *x, size_t n_rdx))
{
	ok_status err = OPTKIT_SUCCESS;
	ok_status lu_err = OPTKIT_SUCCESS;
	size_t lookback_dim, index, next_index;
	vector xcol, fcol, gcol;

	/* CHECK POINTERS, COMPATIBILITY OF X */
	OK_CHECK_MATRIX(DF);
	OK_CHECK_MATRIX(DG);
	OK_CHECK_PTR(iter);
	OK_CHECK_VECTOR(iterate);
	if (DG->size1 != iterate->size)
		return OK_SCAN_ERR( OPTKIT_ERROR_DIMENSION_MISMATCH );

	lookback_dim = DF->size2 + 1;
	index = *iter % (DF->size2);
	next_index = (*iter + 1) % (DF->size2);

	/*
	* f(x) = iterate
	* DF[:, index] = f_prev - f(x) = f_prev - iterate
	*/
	/* anderson_update_D("F")(aa->DF, aa->f, x, index); */

	fcol.data = OK_NULL;
	OK_CHECK_ERR( err, matrix_column(&fcol, DF, index) );
	OK_CHECK_ERR( err, vector_memcpy_vv(&fcol, f) );
	OK_CHECK_ERR( err, vector_memcpy_vv(f, iterate) );
	OK_CHECK_ERR( err, vector_sub(&fcol, f) );

	/*
	* DF[:, index] = g_prev - g
	*   step 1: add g_prev
	*   step 2: calculate g = f(x) - x = iterate - x
	*   step 3: subtract g
	*/
	gcol.data = OK_NULL;
	OK_CHECK_ERR( err, matrix_column(&gcol, DG, index) );
	OK_CHECK_ERR( err, vector_memcpy_vv(&gcol, g) );

	OK_CHECK_ERR( err, x_reduction(x_reduced, iterate, n_reduction) );
	OK_CHECK_ERR( err, vector_memcpy_vv(g, x_reduced) );
	OK_CHECK_ERR( err, vector_sub(g, x) );
	OK_CHECK_ERR( err, vector_sub(&gcol, g) );

	/* CHECK ITERATION >= LOOKBACK */
	if (*iter > lookback_dim && !err){
		OK_CHECK_ERR( lu_err, anderson_difference_solve(
			blas_handle, lapack_handle, DX, DG,
			DXDG, f, gamma, pivot) );

		/* x = f(x) + Jg = f(x) + DF \gamma, if solve was successful */
		if (!lu_err)
			OK_CHECK_ERR( err, anderson_difference_mix(
				blas_handle, DF, gamma, iterate) );
	}

	/*
	* DX[:, next_index] = x_prev - x
	*/
	xcol.data = OK_NULL;
	OK_CHECK_ERR( err, matrix_column(&xcol, DX, next_index) );
	OK_CHECK_ERR( err, vector_memcpy_vv(&xcol, x) );

	OK_CHECK_ERR( err, x_reduction(x_reduced, iterate, n_reduction) );
	OK_CHECK_ERR( err, vector_sub(&xcol, x_reduced) );
	OK_CHECK_ERR( err, vector_memcpy_vv(x, x_reduced) );

	*iter += 1;
	return err;
}


ok_status anderson_difference_accelerator_init(difference_accelerator *aa,
	size_t vector_dim, size_t lookback_dim)
{
	ok_status err = OPTKIT_SUCCESS;
	OK_CHECK_PTR(aa);
	if (aa->DF)
		return OK_SCAN_ERR( OPTKIT_ERROR_OVERWRITE );
	if (lookback_dim - 1 > vector_dim)
		// return OK_SCAN_ERR( OPTKIT_ERROR_DIMENSION_MISMATCH );
		lookback_dim = vector_dim + 1;

	aa->vector_dim = vector_dim;
	aa->lookback_dim = lookback_dim;
	aa->iter = 0;

	ok_alloc(aa->DX, sizeof(*aa->DX));
	OK_CHECK_ERR( err, matrix_calloc(aa->DX, vector_dim, lookback_dim - 1,
		CblasColMajor) );
	ok_alloc(aa->DF, sizeof(*aa->DF));
	OK_CHECK_ERR( err, matrix_calloc(aa->DF, vector_dim, lookback_dim - 1,
		CblasColMajor) );
	ok_alloc(aa->DG, sizeof(*aa->DG));
	OK_CHECK_ERR( err, matrix_calloc(aa->DG, vector_dim, lookback_dim - 1,
		CblasColMajor) );
	ok_alloc(aa->DXDG, sizeof(*aa->DXDG));
	OK_CHECK_ERR( err, matrix_calloc(aa->DXDG, lookback_dim - 1,
		lookback_dim - 1, CblasColMajor) );

	ok_alloc(aa->f, sizeof(*aa->f));
	OK_CHECK_ERR( err, vector_calloc(aa->f, vector_dim) );
	ok_alloc(aa->g, sizeof(*aa->g));
	OK_CHECK_ERR( err, vector_calloc(aa->g, vector_dim) );
	ok_alloc(aa->x, sizeof(*aa->x));
	OK_CHECK_ERR( err, vector_calloc(aa->x, vector_dim) );
        ok_alloc(aa->gamma, sizeof(*aa->gamma));
        OK_CHECK_ERR( err, vector_calloc(aa->gamma, lookback_dim - 1) );


	ok_alloc(aa->pivot, sizeof(*aa->pivot));
	OK_CHECK_ERR( err, int_vector_calloc(aa->pivot, lookback_dim - 1) );

	OK_CHECK_ERR( err, blas_make_handle(&(aa->blas_handle)) );
	OK_CHECK_ERR( err, lapack_make_handle(&(aa->lapack_handle)) );

	if (err)
		OK_MAX_ERR( err, anderson_difference_accelerator_free(aa) );

	return err;
}

ok_status anderson_difference_accelerator_free(difference_accelerator *aa)
{
	ok_status err = OPTKIT_SUCCESS;
	OK_CHECK_PTR(aa);

	OK_MAX_ERR( err, matrix_free(aa->DX) );
	// OK_SCAN_ERR( matrix_print(aa->DF) );
	OK_MAX_ERR( err, matrix_free(aa->DF) );
	OK_MAX_ERR( err, matrix_free(aa->DG) );
	OK_MAX_ERR( err, matrix_free(aa->DXDG) );

	OK_MAX_ERR( err, vector_free(aa->f) );
	OK_MAX_ERR( err, vector_free(aa->g) );
	OK_MAX_ERR( err, vector_free(aa->x) );
        OK_MAX_ERR( err, vector_free(aa->gamma) );

	OK_MAX_ERR( err, int_vector_free(aa->pivot) );

	OK_MAX_ERR( err, blas_destroy_handle(aa->blas_handle) );
	OK_MAX_ERR( err, lapack_destroy_handle(aa->lapack_handle) );

	ok_free(aa->DX);
	ok_free(aa->DF);
	ok_free(aa->DG);
	ok_free(aa->DXDG);

	ok_free(aa->f);
	ok_free(aa->g);
	ok_free(aa->x);
        ok_free(aa->gamma);
	ok_free(aa->pivot);

	return err;
}

ok_status anderson_difference_set_x0(difference_accelerator *aa, vector *x_initial)
{
	ok_status err = OPTKIT_SUCCESS;
	vector xcol;
	OK_CHECK_PTR(aa);
	OK_CHECK_VECTOR(x_initial);
	if (x_initial->size != aa->vector_dim)
		err = OK_SCAN_ERR( OPTKIT_ERROR_DIMENSION_MISMATCH );
	OK_CHECK_ERR( err, matrix_column(&xcol, aa->DX, 0) );
	OK_CHECK_ERR( err, vector_sub(&xcol, x_initial) );
	OK_CHECK_ERR( err, vector_memcpy_vv(aa->x, x_initial) );
	return OPTKIT_SUCCESS;
}

ok_status anderson_difference_accelerate(difference_accelerator *aa, vector *x)
{
	OK_CHECK_PTR(aa);
	return OK_SCAN_ERR( anderson_difference_accelerate_template(
		aa->blas_handle, aa->lapack_handle, aa->DX, aa->DF, aa->DG,
		aa->DXDG, aa->f, aa->g, aa->x, aa->gamma, aa->pivot,
                &aa->iter, x, x, (size_t) 0, anderson_reduce_null) );
}

#ifdef __cplusplus
}
#endif
