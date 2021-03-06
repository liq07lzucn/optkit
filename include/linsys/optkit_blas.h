#ifndef OPTKIT_LINSYS_BLAS_H_
#define OPTKIT_LINSYS_BLAS_H_

#include "optkit_vector.h"
#include "optkit_matrix.h"

#ifdef __cplusplus
extern "C" {
#endif

/* BLAS context */
ok_status blas_make_handle(void ** linalg_handle);
ok_status blas_destroy_handle(void * linalg_handle);

/* BLAS LEVEL 1 */
ok_status blas_axpy(void * linalg_handle, ok_float alpha, const vector * x,
	vector * y);
ok_status blas_nrm2(void * linalg_handle, const vector *x, ok_float * result);
ok_status blas_scal(void * linalg_handle, const ok_float alpha, vector * x);
ok_status blas_asum(void * linalg_handle, const vector * x, ok_float * result);
ok_status blas_dot(void * linalg_handle, const vector * x, const vector * y,
	ok_float * result);
// ok_status blas_dot_inplace(void * linalg_handle, const vector * x, const vector * y,
// 	ok_float * deviceptr_result);

/* BLAS LEVEL 2 */
ok_status blas_gemv(void * linalg_handle, enum CBLAS_TRANSPOSE transA,
	ok_float alpha, const matrix * A, const vector * x, ok_float beta,
	vector * y);

ok_status blas_trsv(void * linalg_handle, enum CBLAS_UPLO uplo,
	enum CBLAS_TRANSPOSE transA, enum CBLAS_DIAG Diag, const matrix * A,
	vector * x);

ok_status blas_sbmv(void * linalg_handle, enum CBLAS_ORDER order,
	enum CBLAS_UPLO uplo, const size_t num_superdiag, const ok_float alpha,
	const vector * vecA, const vector * x, const ok_float beta, vector * y);

ok_status blas_diagmv(void * linalg_handle, const ok_float alpha,
	const vector * vecA, const vector * x, const ok_float beta, vector * y);

/* BLAS LEVEL 3 */
ok_status blas_syrk(void * linalg_handle, enum CBLAS_UPLO uplo,
	enum CBLAS_TRANSPOSE transA, ok_float alpha, const matrix *A,
	ok_float beta, matrix *C);

ok_status blas_gemm(void * linalg_handle, enum CBLAS_TRANSPOSE transA,
	enum CBLAS_TRANSPOSE transB, ok_float alpha, const matrix *A,
	const matrix *B, ok_float beta, matrix *C);

ok_status blas_trsm(void * linalg_handle, enum CBLAS_SIDE Side,
	enum CBLAS_UPLO uplo, enum CBLAS_TRANSPOSE transA, enum CBLAS_DIAG Diag,
	ok_float alpha, const matrix *A, matrix *B);

#ifdef __cplusplus
}
#endif

#endif /* OPTKIT_LINSYS_BLAS_H_ */
