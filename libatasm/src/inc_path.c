/*==========================================================================
 * Project: ATasm: atari cross assembler
 * File: inc_path.c
 *
 * Provides a linked list store search directories for .INCLUDEd files.
 *==========================================================================
 * Created: 08/03/2002 B. Watson
 * Modifications:
 *  08/05/02 mws added comment blocks, reformatted slightly
 *  03/03/03 mws fopen include now tries to open natural path first, then
 *               explores includes
 *  07/27/03 mws rewrote to reduce number and size of mallocs
 *==========================================================================*
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

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "compat.h"
#include "symbol.h"
#include "inc_path.h"
#include "atasm_err.h"

/*=========================================================================*
  funtion free_str_list
  parameters: str - the head of the list to free

  This cleans up a string list
 *=========================================================================*/
void free_str_list(str_list *str) {
  str_list *kill, *walk=str;
  while(walk) {
    kill=walk;
    walk=walk->next;
    free(kill->str);
    free(kill);
  }
}

/*=========================================================================*
 * function init_include
 * parameters: none
 *
 * initializes search directory list;
 *=========================================================================*/
str_list *init_include() {
  str_list *head;

  head=(str_list*)malloc(sizeof(str_list));
  if (head==NULL)
    error("Cannot allocate memory to initialize include list",1);
  head->next = NULL;
  head->str = (char*)malloc(2);
  if (head->str==NULL)
    error("Cannot allocate memory to initialize include list",1);
  head->str[0]='.';
  head->str[1]=0;
  return head;
}

/*=========================================================================*
  funtion append_include
  parameters: head - the current list head;
              path - the path to append

  add another path to the include directory search path
 *=========================================================================*/
void append_include(str_list *head, char *path) {
  str_list *append, *walk=head;

  if ((!path)||(!(*path)))
    return;

  while(walk->next) {
    if (!strcmp(walk->str,path))
      return;
    walk=walk->next;
  }

  append=(str_list *)malloc(sizeof(str_list));
  if(!append)
    error("Cannot grow include list",1);
  append->str=(char*)malloc(strlen(path)+1);
  if (append->str == NULL)
    error("Cannot grow include list",1);
  strcpy(append->str, path);
  append->next=NULL;
  walk->next=append;
}

/*=========================================================================*
  funtion fopen_include
  parameters: head - the list to search
        fname - the file to open

  attempts to open a file, checking all include paths
 *=========================================================================*/
FILE *fopen_include(str_list *head, char *fname, int is_binary) {
  char errbuf[255],mode[3];
  char *full_path;
  FILE *in;

  if (is_binary)
    strcpy(mode,"rb");
  else
    strcpy(mode,"rt");

  /* First, attempt to open file normally... */
  in=fopen(fname,mode);
  if (in)
    return in;

  /* Now test with include paths... */
  full_path = (char*)malloc(MAX_PATH);
  if(full_path==NULL)
    error("Cannot allocate %d bytes in fopen_include",1);

  while(head) {
    full_path[0] = '\0';
    strcpy(full_path, head->str);
    strcat(full_path, DIR_SEP);
    strcat(full_path, fname);
    in=fopen(full_path,mode);
    if (in) {
      free(full_path);
      return in;
    }
    head=head->next;
  }
  free(full_path);
  snprintf(errbuf,255,"Cannot open file: '%s'", fname);
  error(errbuf, 1);
  return NULL;
}
/*=========================================================================*/






