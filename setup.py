import sys
import glob
from setuptools import setup, find_packages, Extension

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS"]
else:
    extra_compile_args = []

import numpy

MONOLITHIC = True
DEV = False

extensions = [
    Extension("udis_fast.disasm_info",
        sources = ["udis_fast/disasm_info.c"],
        extra_compile_args = extra_compile_args,
        include_dirs = [numpy.get_include()],
        )]

if DEV:
    e = Extension("udis_fast.disasm_speedups_dev",
        sources = [
        "udis_fast/disasm_speedups_dev.c",
        "udis_fast/hardcoded_parse_dev.c",
        ],
        extra_compile_args = extra_compile_args,
        include_dirs = [numpy.get_include()],
        )
    extensions.append(e)
elif MONOLITHIC:
    e = Extension("udis_fast.disasm_speedups_monolithic",
        sources = [
        "udis_fast/disasm_speedups_monolithic.c",
        "udis_fast/hardcoded_parse_monolithic.c",
        ],
        extra_compile_args = extra_compile_args,
        include_dirs = [numpy.get_include()],
        )
    extensions.append(e)
else:
    for parser in glob.glob("udis_fast/hardcoded_parse_*.c"):
        if "monolithic" in parser:
            continue
        print parser
        cpu = parser.replace("udis_fast/hardcoded_parse_", "").replace(".c", "")
        cpu_root = "disasm_speedups_%s" % cpu
        mod_name = "udis_fast.%s" % cpu_root
        mod_file = ("%s.c" % mod_name).replace("udis_fast.", "udis_fast/")

        # When not in monolithic mode, each CPU's disassembler is a separate
        # module, and each has to have its own Cython file using the name of
        # the module. Using one pyx for all the files results in "dynamic
        # module does not define init function" because it's looking for e.g.
        # initdisasm_speedups_6502 and only finds the generic
        # initdisasm_speedups. Changing all the references in the generated C
        # file works, no need to cythonize different versions.
        with open("udis_fast/disasm_speedups.c", "r") as fh:
            src = fh.read()
            src = src.replace("disasm_speedups", cpu_root)
            with open(mod_file, "w") as wfh:
                wfh.write(src)
        e = Extension(mod_name,
        sources = [mod_file,
                   "udis_fast/hardcoded_parse_%s.c" % cpu,
                  ],
        extra_compile_args = extra_compile_args,
        include_dirs = [numpy.get_include()],
        )
        extensions.append(e)

cmdclass = dict()

# Cython is only used when creating a source distribution. Users don't need
# to install Cython unless they are modifying the .pyx files themselves.
if "sdist" in sys.argv:
    from distutils.command.sdist import sdist as _sdist

    class sdist(_sdist):
        def run(self):
            from Cython.Build import cythonize
            cythonize(["udis_fast/disasm_speedups.pyx"])
            _sdist.run(self)
    cmdclass["sdist"] = sdist

setup(
    name = "udis",
    ext_modules = extensions,
)