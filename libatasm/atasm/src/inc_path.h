/*==========================================================================
 * Project: atari cross assembler
 * File: inc_path.h
 *
 * Contains prototypes for searching include paths
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
#ifndef INC_PATH_H
#define INC_PATH_H

#define MAX_PATH 1024


#ifdef DOS
#  define DIR_SEP "\\"
#endif

#ifdef MACOS
#  define DIR_SEP ":"
#endif

#ifdef UNIX
#  define DIR_SEP "/"
#endif

#ifndef DIR_SEP
#  define DIR_SEP "/"
#endif

/*==========================================================================*
 * some prototypes
 *==========================================================================*/
str_list *init_include();

void append_include(str_list *, char *);
FILE *fopen_include(str_list *head, char *fname, int is_binary);

void free_str_list(str_list *);

extern str_list *includes;
extern str_list *predefs;
#endif
/*==========================================================================*/






