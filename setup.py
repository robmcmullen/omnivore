# Copyright (c) 2008-2013 by Enthought, Inc.
# All rights reserved.

# NOTE: For py2exe, dependencies can't be installed using python eggs.
# Pip/distutils will do automatic dependency installation using eggs by
# default, but it seems to be able to be disabled using:
#
#     [easy_install]
#     zip_ok = False
#
# in the ~/.pydistutils.cfg.  On windows, this goes in  %HOME%\pydistutils.cfg
#
# See https://docs.python.org/2/install/#location-and-names-of-config-files

import os
import sys
import shutil
import glob
import subprocess
from setuptools import find_packages
from distutils.core import setup
from distutils.extension import Extension
try:
    from Cython.Distutils import build_ext
except ImportError:
    use_cython = False
else:
    use_cython = True

ext_modules = [
    Extension("traits.ctraits",
              sources = ["traits/ctraits.c"],
              extra_compile_args = ["-DNDEBUG=1", "-O3" ]#, '-DPy_LIMITED_API'],
              ),
    ]

cmdclass = dict()

# Conditional cython recipe from http://stackoverflow.com/questions/4505747
if use_cython:
    # Numpy required before the call to setup if generating the C file using
    # cython, but this shouldn't be a problem for normal users because the C
    # files will be distributed with the source.
    import numpy
    
    # Cython needs some replacements for default build commands
    cmdclass["build_ext"] = build_ext

    ext_modules.append(
        Extension("omnimon.utils.wx.bitviewscroller_speedups",
                  sources=["omnimon/utils/wx/bitviewscroller_speedups.pyx"],
                  include_dirs=[numpy.get_include()],
                  )
        )
else:
    from setuptools.command.build_ext import build_ext as _build_ext

    # Bootstrap numpy so that numpy can be installed as a dependency, from:
    # http://stackoverflow.com/questions/19919905
    class build_ext(_build_ext):
        def finalize_options(self):
            _build_ext.finalize_options(self)
            # Prevent numpy from thinking it is still in its setup process:
            __builtins__.__NUMPY_SETUP__ = False
            import numpy
            self.include_dirs.append(numpy.get_include())
    cmdclass["build_ext"] = build_ext

    ext_modules.append(
        Extension("omnimon.utils.wx.bitviewscroller_speedups",
                  sources=["omnimon/utils/wx/bitviewscroller_speedups.c"],
                  )
        )

if "sdist" in sys.argv:
    from distutils.command.sdist import sdist as _sdist

    class sdist(_sdist):
        def run(self):
            # Make sure the compiled Cython files in the distribution are up-to-date
            from Cython.Build import cythonize
            cythonize(["omnimon/utils/wx/bitviewscroller_speedups.pyx"])
            _sdist.run(self)
    cmdclass["sdist"] = sdist

import omnimon
full_version = omnimon.__version__
spaceless_version = full_version.replace(" ", "_")

data_files = []
data_files.extend(omnimon.get_py2exe_data_files())

import traitsui
data_files.extend(omnimon.get_py2exe_data_files(traitsui, excludes=["*/qt4/*"]))

import pyface
data_files.extend(omnimon.get_py2exe_data_files(pyface, excludes=["*/qt4/*", "*/pyface/images/*.jpg"]))

common_includes = [
    "ctypes",
    "ctypes.util",
    "wx.lib.pubsub.*",
    "wx.lib.pubsub.core.*",
    "wx.lib.pubsub.core.kwargs.*",
    "multiprocessing",
    "pkg_resources",
    "configobj",
    
    "traits",
    
    "traitsui",
    "traitsui.editors",
    "traitsui.editors.*",
    "traitsui.extras",
    "traitsui.extras.*",
    "traitsui.wx",
    "traitsui.wx.*",
 
    "pyface",
    "pyface.*",
    "pyface.wx",
 
    "pyface.ui.wx",
    "pyface.ui.wx.init",
    "pyface.ui.wx.*",
    "pyface.ui.wx.grid.*",
    "pyface.ui.wx.action.*",
    "pyface.ui.wx.timer.*",
    "pyface.ui.wx.tasks.*",
    "pyface.ui.wx.workbench.*",
]
common_includes.extend(omnimon.get_py2exe_toolkit_includes())
print common_includes

py2app_includes = [
]

common_excludes = [
    "test",
#    "unittest", # needed for numpy
    "pydoc_data",
    "pyface.ui.qt4",
    "traitsui.qt4",
     "Tkconstants",
    "Tkinter", 
    "tcl", 
    "_imagingtk",
    "PIL._imagingtk",
    "ImageTk",
    "PIL.ImageTk",
    "FixTk",
    ]

py2exe_excludes = [
    ]

package_data = {
    '': ['images/*',
         '*.ini',
         ],
    'apptools': ['help/help_plugin/*.ini',
                 'help/help_plugin/action/images/*.png',
                 'logger/plugin/*.ini',
                 'logger/plugin/view/images/*.png',
                 'naming/ui/images/*.png',
                 ],
    'traitsui': ['image/library/*.zip',
                 'wx/images/*',
                 'qt4/images/*',
                 ],
    }

packages = find_packages()
print packages

base_dist_dir = "dist-%s" % spaceless_version
win_dist_dir = os.path.join(base_dist_dir, "win")
mac_dist_dir = os.path.join(base_dist_dir, "mac")

is_64bit = sys.maxsize > 2**32

if sys.platform.startswith("win"):
    import py2exe
    if is_64bit:
        # Help py2exe find MSVCP90.DLL
        sys.path.append("c:/Program Files (x86)/Microsoft Visual Studio 9.0/VC/redist/amd64/Microsoft.VC90.CRT")
    else:
        # Help py2exe find MSVCP90.DLL
        sys.path.append("c:/Program Files (x86)/Microsoft Visual Studio 9.0/VC/redist/x86/Microsoft.VC90.CRT")

def remove_pyc(basedir):
    for curdir, dirlist, filelist in os.walk(basedir):
        print curdir
        for name in filelist:
            if name.endswith(".pyo"):
                c = name[:-1] + "c"
                cpath = os.path.join(curdir, c)
                print "  " + name
                # remove .pyc if .pyo exists
                if os.path.exists(cpath):
                    os.remove(cpath)
                # remove .py if not in numpy because numpy is crazy
                path = cpath[:-1]
                if os.path.exists(path) and "numpy" not in path:
                    os.remove(path)

def remove_numpy_tests(basedir):
    print basedir
    for f in glob.glob("%s/*/tests" % basedir):
        print f
        shutil.rmtree(f)
    for f in glob.glob("%s/tests" % basedir):
        print f
        shutil.rmtree(f)
    for f in ["tests", "f2py", "testing", "core/include", "core/lib", "distutils"]:
        path = os.path.join(basedir, f)
        shutil.rmtree(path, ignore_errors=True)
    testing = "%s/testing" % basedir
    os.mkdir(testing)
    
    tester_replace = """class Tester(object):
    def bench(self, label='fast', verbose=1, extra_argv=None):
        pass
    test = bench
"""
    fh = open("%s/__init__.py" % testing, "wb")
    fh.write(tester_replace)
    fh.close()

if 'nsis' not in sys.argv:
    if sys.platform.startswith("win"):
        shutil.rmtree(win_dist_dir, ignore_errors=True)
    elif sys.platform.startswith('darwin'):
        shutil.rmtree(mac_dist_dir, ignore_errors=True)

    setup(
        name = 'Omnimon',
        version = omnimon.__version__,
        author = omnimon.__author__,
        author_email = omnimon.__author_email__,
        url = omnimon.__url__,
        download_url = ('%s-%s.tar.gz' % (omnimon.__download_url__, omnimon.__version__)),
        classifiers = [c.strip() for c in """\
            Development Status :: 3 - Alpha
            Intended Audience :: Developers
            License :: OSI Approved :: GNU General Public License (GPL)
            Operating System :: MacOS
            Operating System :: Microsoft :: Windows
            Operating System :: OS Independent
            Operating System :: POSIX
            Operating System :: Unix
            Programming Language :: Python
            Topic :: Software Development :: Libraries
            Topic :: Text Editors
            """.splitlines() if len(c.strip()) > 0],
        description = "The Atari 8-bit binary editor sponsored by the Player/Missile Podcast.",
        long_description = open('README.rst').read(),
        cmdclass = cmdclass,
        ext_modules = ext_modules,
        install_requires = omnimon.__requires__,
        setup_requires = ["numpy"],
        license = "BSD",
        packages = find_packages(),
        package_data = package_data,
        data_files=data_files,
        
        app=["run.py"],
        windows=[dict(
            script="run.py",
            icon_resources=[(1, "omnimon/icons/omnimon.ico")],
        )],
        options=dict(
            py2app=dict(
                dist_dir=mac_dist_dir,
                argv_emulation=True,
                packages=[],
                optimize=2,  # Equivalent to running "python -OO".
                semi_standalone=False,
                includes=common_includes + py2app_includes,
                excludes=common_excludes,
                frameworks=[],
                iconfile="omnimon/icons/omnimon.icns",
                plist=dict(
                    CFBundleName="Omnimon",
                    CFBundleTypeExtensions=["xex", "atr", "xfd", "obx"],
                    CFBundleTypeName="Document",
                    CFBundleTypeRole="Editor",
                    CFBundleShortVersionString=omnimon.__version__,
                    CFBundleGetInfoString="Omnimon %s" % omnimon.__version__,
                    CFBundleExecutable="Omnimon",
                    CFBUndleIdentifier="com.playermissile",
                )
            ),
            py2exe=dict(
                dist_dir=win_dist_dir,
                optimize=2,
                skip_archive=True,
                compressed=False,
                packages=[],
                includes=common_includes,
                excludes=common_excludes + py2exe_excludes,
            ),
            build=dict(compiler="msvc",) if sys.platform.startswith("win") else {},
            ),
        platforms = ["Windows", "Linux", "Mac OS-X", "Unix"],
        zip_safe = False,
        )

if 'py2exe' in sys.argv and sys.platform.startswith("win"):
    print "*** create installer ***"

    if is_64bit:
        nsis_arch = """ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64"""
        
        # copy manifest and app config files to work around side-by-side
        # errors
        for f in glob.glob(r'pyinstaller/Microsoft.VC90.CRT-9.0.30729.6161/*'):
            print f
            shutil.copy(f, win_dist_dir)
    else:
        nsis_arch = ""
    shutil.copy("%s/run.exe" % win_dist_dir, "%s/omnimon.exe" % win_dist_dir)
    iss_filename = "%s\\omnimon.iss" % win_dist_dir
    iss_file = open(iss_filename, "w")
    iss_file.write( """
[Setup]
AppId={{8AE5A4C3-B67E-4243-9F45-401C554A9019}
AppName=Omnimon
AppVerName=Omnimon %s
AppPublisher=Player/Missile Podcast
AppPublisherURL=http://www.playermissile.com/
AppSupportURL=http://www.playermissile.com/
AppUpdatesURL=http://www.playermissile.com/
DefaultDirName={pf}\Omnimon
DefaultGroupName=Omnimon
OutputBaseFilename=Omnimon_%s
SetupIconFile=..\..\omnimon\icons\omnimon.ico
Compression=lzma
SolidCompression=yes
%s

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "omnimon.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\Omnimon"; Filename: "{app}\omnimon.exe"
Name: "{commondesktop}\Omnimon"; Filename: "{app}\omnimon.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Omnimon"; Filename: "{app}\omnimon.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\omnimon.exe"; Description: "{cm:LaunchProgram,Omnimon}"; Flags: nowait postinstall skipifsilent
""" % ( full_version, spaceless_version, nsis_arch ) )
    iss_file.close()

    os.system(
        '"C:\Program Files (x86)\Inno Setup 5\ISCC.exe" %s' % iss_filename,
    )
elif 'py2app' in sys.argv and sys.platform.startswith('darwin'):
    remove_pyc(mac_dist_dir)
    app_name = "%s/Omnimon.app" % mac_dist_dir
    
    # Strip out useless binary stuff from the site packages zip file.
    # Saves 3MB or so
    site_packages = "%s/Contents/Resources/lib/python2.7/site-packages.zip" % app_name
    subprocess.call(['/usr/bin/zip', '-d', site_packages, "distutils/command/*", "wx/locale/*", "*.c", "*.pyx", "*.png", "*.jpg", "*.ico", "*.xcf", "*.icns", "reportlab/fonts/*", ])

    # fixup numpy
    numpy_dir = "%s/Contents/Resources/lib/python2.7/numpy" % app_name
    remove_numpy_tests(numpy_dir)

    fat_app_name = "%s/Omnimon.fat.app" % mac_dist_dir
    os.rename(app_name, fat_app_name)
    subprocess.call(['/usr/bin/ditto', '-arch', 'x86_64', fat_app_name, app_name])
    cwd = os.getcwd()
    os.chdir(mac_dist_dir)
    subprocess.call(['/usr/bin/zip', '-r', '-9', '-q', "Omnimon-%s-darwin.zip" % spaceless_version, 'Omnimon.app', ])
    os.chdir(cwd)
    shutil.rmtree(fat_app_name)
