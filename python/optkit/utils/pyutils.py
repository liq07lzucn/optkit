from optkit.types import ok_enums as enums, ok_float_p, \
					     ok_vector, ok_matrix, ok_function
from optkit.types.lowlevel import c_uint_p
from optkit.defs import FLOAT_CAST
from ctypes import c_uint
from numpy import ndarray

def ndarray_pointer(x, function = False):
	if not isinstance(x,ndarray):
		print ("Optkit error: input to method `ndarray_pointer "
			  "must be a NumPy array. \n "
			  "Input type: {}".format(type(x)))
		return None
	if not function:
		if x.dtype != FLOAT_CAST:
			print ("Optkit error: input to method `ndarray_pointer` " 
			  "must be a NumPy array of type {} when keyword argument"
			  "`function` is set to `False` or not provided.\n "
			  "Input array type: {}".format(FLOAT_CAST, x.dtype))
			return None
		else: return x.ctypes.data_as(ok_float_p)
	elif function:
		if x.dtype != c_uint:
			print ("Optkit error: input to method `ndarray_pointer` " 
				  "must be a NumPy array of type {} when keyword argument"
				  "`function` is set to `True`.\n "
				  "Input array type: {}".format(c_uint, x.dtype))
			return None
		else: 
			return x.ctypes.data_as(c_uint_p)


def istypedtuple(x,n, type_):
	valid = isinstance(x,tuple)
	if valid:
		valid &= len(x)==int(n)
		valid &= all(map(lambda y: type(y)==type_, x))
	return valid
