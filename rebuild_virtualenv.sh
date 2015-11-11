#!/bin/bash

ROOT=/noaa/virtualenv

function install_wx {
    mkdir $VIRTUAL_ENV/src
    cd $VIRTUAL_ENV/src
    tar xvf /opt/download/wxPython-src-3.0.2.0.tar.bz2 
    cd wxPython-src-3.0.2.0/
    ./configure --prefix=$VIRTUAL_ENV
    make -j 8
    make install
    cat <<EOF >> $VIRTUAL_ENV/bin/activate
LD_LIBRARY_PATH="$VIRTUAL_ENV/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH
EOF
    cd wxPython
    python setup.py install
}

function install_virtualenv {
    DIR=$1

    if [ -d $ROOT/$DIR ]
    then
        echo "Skipping existing $DIR virtualenv directory"
    else
        virtualenv $ROOT/$DIR
        source $ROOT/$DIR/bin/activate
        pip install --upgrade setuptools # Need setuptools-18.5 or cython won't produce .c files
        install_wx
    fi
}

install_virtualenv wx3
install_virtualenv sdist-test
