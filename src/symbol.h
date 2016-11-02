/*==========================================================================
 * Project: atari cross assembler
 * File: symbol.h
 *
 * Contains typedefs and prototypes for the assembler
 *==========================================================================
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 *==========================================================================*/
#ifndef SYMBOL_H
#define SYMBOL_H

#define MAJOR_VER 1
#define MINOR_VER 8
#define BETA_VER 0

/*==========================================================================*/
typedef struct memBank {
  int id, sym_id;
  unsigned char *memmap, *bitmap;  /* memory snapshot, and bitmap */
  int offset;
  struct memBank *nxt;
} memBank;
/*==========================================================================*/
typedef struct symbol {  /* Symbol table entry */
  char *name;
  /* tp:
     0: opcode
     1: directive
     2: user label
     3: user transitory equate
     4: macro
     5: macro label/equate
     6: equate
     7: macro transitory label
   */
  short tp;
  unsigned short addr;
  unsigned short bank;
  unsigned short ref;
  unsigned short num;
  char *macroShadow;
  struct symbol *nxt;
  struct symbol *lnk, *mlnk;
} symbol;
/*==========================================================================*/
typedef struct unkLabel {
  char *label;
  int zp;
  struct unkLabel *nxt;
} unkLabel;
/*==========================================================================*/
typedef struct strList {
  char *str;
  struct strList *next;
} str_list;
/*==========================================================================*/
/* Some defines for symbol types -- see above comment */
#define OPCODE 0
#define DIRECT 1
#define LABEL  2
#define TEQUATE 3
#define MACRON 4
#define MACROL 5
#define EQUATE 6
#define MACROQ 7
/*==========================================================================*/
typedef struct file_stack { /* File process entry */
  char *name;
  FILE *in;
  int line;
  struct file_stack *nxt;
} file_stack;
/*==========================================================================*/
typedef struct macro_line { /* an entry in a macro */
  char *line;
  struct macro_line *nxt;
} macro_line;
/*==========================================================================*/
typedef struct macro {  /* a macro */
  char *name;           /* name */
  int tp,param, num;    /* number of parameters, # lines */
  short times;          /* number of invokations */
  macro_line *lines;    /* The actual text */
  symbol *mlabels;      /* assembled labels */
  struct macro *nxt;
} macro;
/*==========================================================================*/
typedef struct macro_call {
  int argc;             /* number of arguments passed to macro */
  macro *orig;          /* pointer to original macro */
  macro_line *cmd;      /* parameters */
  macro_line *line;     /* pointer to next macro line */
  struct macro_call *nxt;
} macro_call;

/*==========================================================================*
 * some symbols
 *==========================================================================*/
extern unsigned short pc;   /* program counter */
extern int pass; /* pass number */
extern int eq, verbose;  /* assignment flag, verbosity flag */
extern int local,numwarn,bsize;
extern int repass;  /* flag indicating that a referenced label changed size */
extern file_stack *fin;
extern macro *macro_list;
extern macro_call *invoked;
extern memBank *banks, *activeBank;
extern char *outline;  /* the line of text written out in verbose mode */
extern unkLabel *unkLabels; /* list of unknown, referenced symbols */

extern int double_fwd; /* flag indicating a double forward reference occured */

#define HSIZE 511
extern symbol *hash[HSIZE];
extern FILE *listFile;

/*==========================================================================*
 * some prototypes
 *==========================================================================*/
char *get_nxt_word(int tp);
int squeeze_str(char *str);
int num_cvt(char *num);

unsigned short get_expression(char *str, int tp);
int get_signed_expression(char *str, int tp);
int get_name(char *src, char *dst);

symbol *findsym(char *name);
int addsym(symbol *wrd);
void remsym(symbol *wrd);
symbol *get_sym();
int dump_symbols();
int dump_labels(char *fname);
macro_call *get_macro_call(char *name);
int macro_subst(char *name, char *in, macro_line *cmd, int max);
int create_macro(symbol *sym);
int macro_param(macro_call *mc, char *cmd);
int skip_macro();
int clear_ref();
int do_rept(symbol *sym);
int del_rept(macro_call *kill);

void cleanUnk();
void fixRepass();
int find_extension(char *name);

int save_state(char *fin, char *fout);
int save_snapshot(char *fin, char *fout);

int write_xfd_file(char *image, char *file);
void process_predef(str_list *def);

void clean_up();

void addUnk(char *unk);
unkLabel *isUnk(char *unk);
void defUnk(char *unk, unsigned short addr);

int clear_banks();
void kill_banks();
#endif
