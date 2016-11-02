#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "compat.h"
#include "symbol.h"
#include "inc_path.h"
#include "atasm_err.h"

extern symbol *linkit();
extern symbol *sort(symbol *head);
extern int init_asm();
extern int assemble(char *fname);

/* Dummy functions not needed for cython interface */
int save_state(char *fin, char *fout) {
    return 0;
}

int write_xfd_file(char *fimage, char *file) {
    return 0;
}

/*=========================================================================*
 * function dump_all
 * prints out all symbols entered into the symbol table in label format
 *=========================================================================*/
int dump_all(FILE *out) {
  symbol *sym,*head;

  head=linkit();
  if (!head) {
    return 0;
  }
  head=sym=sort(head);

  fprintf(out,"\n\nEquates:\n");
  while(sym) {
    if (sym->name[0])
      if (((sym->tp==EQUATE)||(sym->tp==TEQUATE))&&(sym->name[0]!='=')) {
      fprintf(out,"%c%s: %.4x\n",(sym->tp==TEQUATE)?'*':' ',
             sym->name,sym->addr&0xffff);
    }
    sym=sym->lnk;
  }
  sym=head;
  fprintf(out,"\n\nSymbol table:\n");
  while(sym) {
    if (sym->name[0])
      if ((sym->tp==LABEL)&&(sym->name[0]!='=')) {
      if ((strchr(sym->name,'?'))&&(opt.MAElocals))
        ;
      else {
        fprintf(out,"%s: %.4x\n",sym->name,sym->addr&0xffff);
      }
    }
    sym=sym->lnk;
  }
  return 0;
}

/*=========================================================================*
 * function main
 *
 * starts the whole process
 *=========================================================================*/
int py_assemble(char *fname, char *listfile, char *errfile) {
  int exitval = 0;

  opt.savetp=opt.verbose=0;
  opt.MAElocals=1;
  opt.fillByte=0xff;

  includes=init_include();
  predefs=NULL;
  listFile=NULL;

  printf("fname: %s\n", fname);

        listFile=fopen(listfile,"wt");
        if (!listFile) {
          fprintf(stderr, "Cannot write to list file'%s'\n",listfile);
          return 1;
        }
        opt.verbose|=2;

  init_asm();

        errFile=fopen(errfile,"wt");
        if (!errFile) {
          fprintf(stderr, "Cannot write to error file'%s'\n",errfile);
          return 1;
        }
  TRY {
      assemble(fname);
      dump_all(listFile);
  }
  CATCH {
    printf("GOT EXCEPTION!\n");
    exitval = 1;
  }
  END_TRY;

  fclose(listFile);
  fclose(errFile);

  clean_up();
  return exitval;
}
/*=========================================================================*/
