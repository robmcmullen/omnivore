/*==========================================================================
 * Project: atari cross assembler
 * File: setparse.c
 *
 * Contains the routines to intilize expression parsing
 *==========================================================================
 * Created: 3/26/98 mws
 * Modifications:
 *                12/18/98 mws rewrote for full expression parsing
 *                03/03/03 mws added interpretation of #$LABEL
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
 *=========================================================================*/

#include <string.h>
#include <stdio.h>
#include <ctype.h>

#include "compat.h"
#include "symbol.h"
#include "atasm_err.h"

int yyparse();
extern int rval;
int vnum, nums[64];

char *parse_string;
/*=========================================================================*
  function yylex()

  returns the next token in the expression stream to the parser
 *=========================================================================*/
int yylex()
{
  char terminals[]="[]<>-N/*+-&|^=#GLAOv";
  char *look,c;

  if (parse_string) {
    c=*parse_string;
    parse_string++;
  } else
    c=0;

  look=strchr(terminals,c);
  if (!look) {
    error("Malformed expression",1);
    return 0;
  } else {
    return c;
  }
}
/*=========================================================================*
  function parse_expr(char *str)
  parameters: str - the expression to parse (numbers and directive only)

  Create simpler expression (replace .DIRECTIVEs, etc) and then return
  retult.
 *=========================================================================*/
int parse_expr(char *a) {
  int v,num;
  char expr[80], *look, *walk, *n;

  vnum=num=0;
  look=a;
  walk=expr;
  while(*look) {
    if (ISDIGIT(*look)) {
      *walk++='v';
      n=walk;
      while(ISDIGIT(*look))
        *n++=*look++;
      *n=0;
      sscanf(walk,"%d",&v);
      nums[num]=v;
      num++;
    } else if ((*look=='<')&&(*(look+1)=='>')) {
      look+=2; *walk++='#';
    } else if ((*look=='<')&&(*(look+1)=='=')) {
      look+=2; *walk++='L';
    } else if ((*look=='>')&&(*(look+1)=='=')) {
      look+=2; *walk++='G';
    } else *walk++=*look++;
  }
  *walk=0;
  parse_string=expr;

  if (yyparse()) {
    error("Malformed expression",1);
  }
  return rval;
}
/*=========================================================================*
  function get_name(char *src, char *dst)
  parameters: src - pointer to source string
              dst - pointer to destination string

  This copies an alphanumeric string from src to dst, stopping when either
  an illegal character is found, or the string terminates.  The name is
  capitalized as it is copied
 *=========================================================================*/
int get_name(char *src, char *dst) {
  int l=0;

  while((ISALNUM(*src))||(*src=='_')||(*src=='?')||(*src=='@')) {/*||(*src=='.')) { */
    *dst++=TOUPPER(*src++);
    l++;
  }
  *dst=0;
  return l;
}

/*=========================================================================*
  function validate_symbol(char *str)
  parameters: str - the symbol to check

  This function verifies that a symbol is a legal address...
 *=========================================================================*/
symbol *validate_symbol(char *str) {
  symbol *s;

  s=findsym(str);
  if (s) {
    if (s->tp==MACRON) {
      char err[256];
      snprintf(err,256,"Cannot use macro name '%s' as an address.",s->name);
      error(err,1);
    } else if (s->tp==OPCODE) {
      error("Cannot use reserved opcode as an address.",1);
    }
  }
  return s;
}
/*=========================================================================*
  function get_expression(char *str, int tp)
  parameters: str - the expression to parse
              tp  - flag error (1=yes, 0=return 0xffff)
  returns the value of the expression

  This function calculates the value of an expression, or generates an error
 *=========================================================================*/
unsigned short get_expression(char *str, int tp) {
  return (unsigned short) get_signed_expression(str, tp);
}

int get_signed_expression(char *str, int tp) {
  char buf[256], work[256];
  char *look, *walk, *w;
  int v;
  symbol *sym;
  char math[]="[]*/+-&|^<>=";

  buf[0]=0;
  walk=buf;
  look=str;
  while(*look) {
    if (*look=='*') {
      if ((walk==buf)||((!ISDIGIT(*(walk-1)))&&(*(walk-1)!=']'))||
          (*(look+1)=='*')) {
        snprintf(work,256,"%d",pc);
        strcpy(walk,work);
        walk+=strlen(work);
        look++;
      } else *walk++=*look++;
    } else if (strchr(math,*look))
      *walk++=*look++;
    else if (*look=='!')      /* Old binary OR operator */
      *walk++='|';
    else if (ISDIGIT(*look)) {
      while(ISDIGIT(*look)) { /* Immediate value */
        *walk++=*look++;
      }
    } else if (*look=='$') {  /* Hex value */
      char *hold;
      w=work;
      *w++=*look++;
      hold=look;

      while(ISXDIGIT(*look))
        *w++=*look++;
      if (ISALPHA(*look)) {  /* symbol #$SOMETHING, give warning */
        v=get_name(hold,work);
        look=hold+v;
        sym=findsym(work);
        if (!sym) {
          error("Non-hex expression",1);
        } else {
          snprintf(buf,256,"Interpreting '$%s' as hex value '$%x'",work,sym->addr);
          error(buf,0);
        }
        v=sym->addr;
        sym->ref=1;
        snprintf(work,256,"$%x",v);
      } else
        *w=0;
      v=num_cvt(work);
      snprintf(work,256,"%d",v);
      strcpy(walk,work);
      walk+=strlen(work);
    } else if ((*look=='~')||(*look=='%')) {  /* binary value */
      w=work;
      *w++=*look++;
      while(ISDIGIT(*look))
        *w++=*look++;
      *w=0;
      v=num_cvt(work);
      snprintf(work,256,"%d",v);
      strcpy(walk,work);
      walk+=strlen(work);
    } else if (*look=='\'') { /* Character value */
      look++;
      v=*look;
      look++;
      if ((*look=='\'')&&(v!=' ')) {
        error("Probably shouldn\'t be surrounded by \'",0);
        look++;
      }
      snprintf(work,256,"%d",v);
      strcpy(walk,work);
      walk+=strlen(work);
    } else if (*look=='.') {
      if (!STRNCASECMP(look,".NOT",4)) {
        look+=4; *walk++='N';
      } else if (!STRNCASECMP(look,".AND",4)) {
        look+=4; *walk++='A';
      } else if (!STRNCASECMP(look,".OR",3)) {
        look+=3; *walk++='O';
      } else if (!STRNCASECMP(look,".BANKNUM",8)) {
        look+=9;
        v=get_name(look,work);
        look+=v;
        sym=validate_symbol(work);
        if ((!sym)||
            ((sym->tp!=LABEL)&&(sym->tp!=MACROL))) {
          error(".BANKNUM operator is only valid for labels.",1);
        } else {
          int bank=sym->bank&0xff;
          snprintf(work,256,"%d",bank);
          strcpy(walk,work);
          walk+=strlen(work);
        }
      } else if (!STRNCASECMP(look,".DEF",4)) {
        look+=4;
        v=get_name(look,work);
        look+=v;
        sym=validate_symbol(work);
        if (!sym)
          *walk++='0';
        else
          *walk++='1';
      } else if (!STRNCASECMP(look,".REF",4)) {
        look+=4;
        v=get_name(look,work);
        look+=v;
        sym=validate_symbol(work);
        if (!sym)
          *walk++='0';
        else {
          if (sym->ref)
            *walk++='1';
          else
            *walk++='0';
        }
      } else {
        error("Invalid compiler directive in expression.",1);
      }
    } else if (*look=='(') {
      look++;
      *walk++='[';
    } else if (*look==')') {
      look++;
      *walk++=']';
    } else {
      v=get_name(look,work);
      look+=v;
      sym=validate_symbol(work);
      if ((!sym)&&(tp)) {
        snprintf(buf,256,"Unknown symbol '%s'",work);
        dump_symbols();
        error(buf,1);
      }
      if ((!sym)||((sym->tp==MACROL)&&(!sym->macroShadow))) {
        unkLabel *look;

        look=isUnk(work);
        if (look) {
          if (look->zp)
            return 0xff;
        } else {
          addUnk(work);
        }
        if (sym)  /* mws fix for overflow.m65 */
          return sym->addr;
        return 0xffff;
      } else {
        v=sym->addr;
        if ((pass)&&(v==0xffff)&&(sym->ref!=1)) {
          double_fwd=1;
        }
      }
      sym->ref=1;
      snprintf(work,256,"%d",v);
      strcpy(walk,work);
      walk+=strlen(work);
    }
  }
  *walk=0;
  v=parse_expr(buf);
  return v;
}
/*=========================================================================*/
