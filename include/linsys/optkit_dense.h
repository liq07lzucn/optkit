#ifndef OPTKIT_LINSYS_DENSE_H_
#define OPTKIT_LINSYS_DENSE_H_

#include "optkit_vector.h"
#include "optkit_matrix.h"
#include "optkit_blas.h"

#ifdef __cplusplus
extern "C" {
#endif

void denselib_version(int * maj, int * min, int * change, int * status);

void linalg_cholesky_decomp(void * linalg_handle, matrix * A);
void linalg_cholesky_svx(void * linalg_handle, const matrix * L, vector * x);

void linalg_diag_gramian(const matrix * A, vector * v);
void linalg_matrix_broadcast_vector(matrix * A, const vector * v,
	const enum OPTKIT_TRANSFORM operation, const enum CBLAS_SIDE side);
void linalg_matrix_reduce_indmin(indvector * indices, vector * minima,
	matrix * A, const enum CBLAS_SIDE side);
void linalg_matrix_reduce_min(vector * minima, matrix * A,
	const enum CBLAS_SIDE side);
void linalg_matrix_reduce_max(vector * maxima, matrix * A,
	const enum CBLAS_SIDE side);

/* device reset */
ok_status ok_device_reset(void);

#ifdef __cplusplus
}
#endif

#endif  /* OPTKIT_LINSYS_DENSE_H_ */
