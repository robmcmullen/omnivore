#!/bin/bash

VENV=/tmp/omnivore-install-test$$
OMNIVORE=$HOME/src/omnivore

/usr/bin/python3 -m venv $VENV
source $VENV/bin/activate

echo $PATH
pip install numpy pathlib2
# pip install pytest
# pip install pathlib2
pip install $OMNIVORE/dist/omnivore-2.0a7.tar.gz
# cd $OMNIVORE
# pip install .

echo "activate with:"
echo "source $VENV/bin/activate"
