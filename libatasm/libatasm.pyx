cdef extern:
    int py_assemble(char *, char *, char *)

def mac65_assemble(source):
    cdef char *source_c
    cdef char *listfile_c
    
    source_c = source
    listfile = source + b".lst"
    listfile_c = listfile
    errfile = source + b".err"
    errfile_c = errfile

    exitval = py_assemble(source_c, listfile_c, errfile_c)
    with open(errfile, "r") as fh:
        errors = fh.read()
        #print errors
    if exitval == 1:
        #print "ERROR!!!!"
        text = None
    else:
        #print "source", source
        #print "opening -->", listfile, "<--"
        with open(listfile, "r") as fh:
            text = fh.read()
            #print text

    #print "exitval=", exitval
    return errors, text
