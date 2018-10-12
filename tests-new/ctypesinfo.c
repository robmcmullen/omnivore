#include <stdio.h>

struct info{
    int input;
    int out;
};

void getVal(struct info *a){
    printf("in = %i \n", a->input);
    printf("out = %i \n", a->out);
    a->out = 77;
}
