from libudis.libudis cimport parse_func_t, string_func_t

cdef extern:
    parse_func_t find_parse_function(char *)
    string_func_t find_string_function(char *)
