from os import path, popen, uname
from setuptools import setup
from setuptools.command.install import   install
from distutils.command.build import build
from subprocess import call
from multiprocessing import cpu_count

USE_OPENMP = False
SPARSE_POGS = False
ABSTRACT_POGS = False
BASEPATH = path.abspath(path.join(path.dirname(path.abspath(__file__)),'..'))
LIBPATH = path.join(BASEPATH, 'build')
LONG_DESC='`optkit` provides a Python interface for CPU and GPU \
(dense/sparse) linear algebra, enabling the composition of C- or \
CUDA C-based optimization routines in a Python environment.'

class OptkitBuild(build):
  def run(self):
    NVCC = popen("which nvcc").read()!=""
    EXT = "dylib" if uname()[0] == "Darwin" else "so"

    # run original build code
    build.run(self)

    # build optkit
    message = 'Compiling optkit---CPU and GPU' if NVCC else \
                'Compiling optkit---CPU only'

    devices = ['cpu', 'gpu'] if NVCC else ['cpu']
    precisions = ['32', '64']

    for prec in precisions:
        for dev in devices:
            cmd = [ 'make', 'all' ]
            cmd.extend([ 'FLOAT={}'.format(int(prec=='32')) ])
            cmd.extend([ 'GPU={}'.format(int(dev=='gpu')) ])
            if USE_OPENMP: cmd.extend([ 'USE_OPENMP=1' ])

            # run Make for each condition (make CPU/GPU, 32/64)
            def compile():
              call(cmd, cwd=BASEPATH)

            self.execute(compile, [], message)

    pogs_matrices = ['dense']
    if SPARSE_POGS:
        pogs_matrices.append('sparse')
    if ABSTRACT_POGS:
        pogs_matrices.append('abstract')

    CPU_LIBS = []
    GPU_LIBS = []
    for device in devices:
        libs = []
        for precision in precisions:
            sparse = COMPILE_GPU_SPARSE if dev=='gpu' else COMPILE_CPU_SPARSE
            linsys_matrices = ['dense', 'sparse']
            print('making linsys libraries for:'
                '\n\tDEVICE: {}\n\tPRECISION: {}\n\t MATRICES {}'.format(
                device, precision, linsys_matrices))
            for matrix in linsys_matrices:
                libs.append('libok_{}_{}{}.{}'.format(matrix, device,
                    precision, EXT))
            print('making prox libraries for:'
                '\n\tDEVICE: {}\n\tPRECISION: {}'.format(
                device, precision))
            libs.append('libprox_{}{}.{}'.format(device, precision, EXT))
            print('making pogs libraries for:'
                '\n\tDEVICE: {}\n\tPRECISION: {}\n\t MATRICES {}'.format(
                device, precision, pogs_matrices))
            for matrix in pogs_matrices:
                libs.append('libpogs_{}_{}{}.{}'.format(matrix, device,
                    precision, EXT))

        if device =='gpu':
            GPU_LIBS = libs
        else:
            CPU_LIBS = libs

    # set target files to Make output
    target_files = CPU_LIBS + GPU_LIBS


    # copy resulting tool to library build folder
    self.mkpath(self.build_lib)
    libtarg = path.join(self.build_lib, '_optkit_libs')
    self.mkpath(libtarg)
    for target in target_files:
          self.copy_file(path.join(LIBPATH,target), libtarg)


class OptkitInstall(install):
    def initialize_options(self):
        install.initialize_options(self)
        self.build_scripts = None

    def finalize_options(self):
        install.finalize_options(self)
        self.set_undefined_options('build', ('build_scripts', 'build_scripts'))

    def run(self):
        # run original install code
        install.run(self)

        # install Optkit executables
        self.copy_tree(self.build_lib, self.install_lib)

setup(
    name='optkit',
    version='0.0.4b',
    author='Baris Ungun',
    author_email='ungun@stanford.edu',
    url='http://github.com/bungun/optkit/',
    package_dir={'optkit': 'optkit'},
    packages=['optkit',
              'optkit.libs',
              'optkit.utils',
              'optkit.types',
              'optkit.tests'],
    license='GPLv3',
    zip_safe=False,
    description='Python optimization toolkit',
    long_description=LONG_DESC,
    install_requires=["numpy >= 1.8",
                      "scipy >= 0.13",
                      "toolz"],
    cmdclass={'build' : OptkitBuild, 'install' : OptkitInstall}
)