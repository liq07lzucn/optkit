import sys
from optkit.tests import *


def main(*args, **kwargs):
	tests = []
	passing = 0
	if '--linsys' in args: tests.append(test_linsys)
	if '--prox' in args: tests.append(test_prox)
	if '--proj' in args: tests.append(test_projector)
	if '--equil' in args: tests.append(test_equil)
	if '--norm' in args: tests.append(test_normalizedprojector)
	if '--block' in args: tests.append(test_blocksplitting)
	if '--pogs' in args: tests.append(test_pogs)
	if '--cequil' in args: tests.append(test_cequil)
	if '--cproj' in args: tests.append(test_cproj)
	if '--cpogs' in args: tests.append(test_cpogs)
	if '--cstore' in args: tests.append(test_cstore)


	for t in tests: passing += t(*args, **kwargs)
	print "{}/{} tests passed".format(passing, len(tests))
	if len(tests)==0:
		test_names = ['--linsys', '--prox', '--proj',
		'--equil', '--norm', '--block', '--pogs', '--py_all',
		'--cequil', '--cproj', '--cpogs', '--cstore', '--c_all']

		print str("no tests specified.\nuse optional arguments:\n"
			"{}\nor\n--all\n to specify tests.".format(test_names))


if __name__== "__main__":
	args=[]
	kwargs={}
	reps=1


	args += sys.argv
	if '--all' in args:
		args += ['--py_all', '--c_all']
	if '--py_all' in args: 
		args+=['--linsys','--allsub','--prox','--proj','--equil',
			'--norm','--block','--pogs']
	if '--c_all' in args:
		args+=['--cequil', '--cproj', '--cpogs', '--cstore']



	if '--size' in sys.argv:
		pos = sys.argv.index('--size')
		if len(sys.argv) > pos + 2:
			kwargs['shape']=(int(sys.argv[pos+1]),int(sys.argv[pos+2]))
	if '--file' in sys.argv:
		pos = sys.argv.index('--file')
		if len(sys.argv) > pos + 1:
			kwargs['file']=str(sys.argv[pos+1])
	if '--reps' in sys.argv:
		pos = sys.argv.index('--reps')
		if len(sys.argv) > pos + 1:
			reps=int(sys.argv[pos+1])

	for r in xrange(reps):
		main(*args,**kwargs)
