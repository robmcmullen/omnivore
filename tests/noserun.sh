#!/bin/bash

PYTHONPATH=$PWD/..
nosetests --exe $*
