VERSION := $(shell python -c "import omnivore; print(omnivore.__version__)")
SDIST := omnivore-framework/dist/omnivore-framework-${VERSION}.tar.gz

all: framework

omnivore-framework/omnivore:
	ln -s ../omnivore omnivore-framework

omnivore-framework/traits:
	ln -s ../deps/traits/traits omnivore-framework

omnivore-framework/traitsui:
	ln -s ../deps/traitsui/traitsui omnivore-framework

omnivore-framework/apptools:
	ln -s ../deps/apptools/apptools omnivore-framework

omnivore-framework/envisage:
	ln -s ../deps/envisage/envisage omnivore-framework

omnivore-framework/pyface:
	ln -s ../deps/pyface/pyface omnivore-framework

omnivore-framework/fs:
	ln -s ../deps/pyfilesystem/fs omnivore-framework

omnivore-framework/LICENSE: LICENSE
	ln -s ../LICENSE omnivore-framework

omnivore-framework/LICENSE.Enthought: LICENSE.Enthought
	ln -s ../LICENSE.Enthought omnivore-framework

${SDIST}:
	(cd omnivore-framework; python setup.py sdist)

framework: omnivore-framework/omnivore omnivore-framework/traits omnivore-framework/traitsui omnivore-framework/apptools omnivore-framework/envisage omnivore-framework/pyface omnivore-framework/fs omnivore-framework/LICENSE omnivore-framework/LICENSE.Enthought ${SDIST}

clean:
	rm -rf omnivore-framework/dist
	rm -f omnivore-framework/LICENSE*
