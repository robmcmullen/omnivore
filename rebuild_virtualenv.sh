#!/bin/bash

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

if [ -d /noaa/virtualenv/wx3 ]
then
    echo "Skipping existing main wx3 development directory"
else
    virtualenv /noaa/virtualenv/wx3
    source /noaa/virtualenv/wx3/bin/activate
    pip install six
    pip install configobj
    pip install cython
    pip install --upgrade setuptools # Need setuptools-18.5 or cython won't produce .c files
    pip install numpy
    pip install pytz
    pip install bson
    pip install jsonpickle
    pip install atrcopy
    install_wx
fi

if [ -d /noaa/virtualenv/sdist-test ]
then
    echo "Skipping existing sdist-test directory"
else
    virtualenv /noaa/virtualenv/sdist-test
    source /noaa/virtualenv/sdist-test/bin/activate
    install_wx
fi

