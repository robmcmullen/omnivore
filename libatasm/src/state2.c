/*===========================================================================
 * Project: ATasm: atari cross assembler
 * File: state2.c
 *
 * Contains code for reading and saving machine snapshot for atari++
 *===========================================================================
 * Created: 10/17/03 mws
 *
 * Modifications:
 *   10/21/2003  mws Fixed several bugs, now actually loads into Atari++
 *===========================================================================
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
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "compat.h"
#include "symbol.h"

/*=========================================================================*
 * function fromhex
 * parameters: txt, pointer to 2 digit hex string
 *
 * this functions returns the value of a 2 digit hex string (case insensitve)
 *=========================================================================*/
int fromhex(char *txt) {
  int num;
  if ((txt[0]>='0')&&(txt[0]<='9')) {
    num=(txt[0]-'0')*16;
  } else {
    num=(TOUPPER(txt[0])-'A'+10)*16;
  }
  if ((txt[1]>='0')&&(txt[1]<='9')) {
    num+=(txt[1]-'0');
  } else {
    num+=(TOUPPER(txt[1])-'A'+10);
  }
  return num&255;
}

/*=========================================================================*
 * function save_page
 * parameters: out, the file to save;
 *             page, the page to save;
 *
 * this function writes out a page to the snapshot file
 *=========================================================================*/
int save_page(FILE *out, unsigned char *page) {
  int i,column=0;

  for(i=0;i<256;i++) {
    if (column>=40) {
      fprintf(out,"\n");
      column=0;
    }
    fprintf(out,"%02x",*page);
    column++;
    page++;
  }
  fprintf(out,"\n");
  return 1;
}

/*=========================================================================*
 * function read_page
 * parameters: in, the file to read
 *             buf, workspace (512 chars)
 *             page, the resultant page
 *
 * read a snapshot RAM page from Atari++ file
 *=========================================================================*/
int read_page(FILE *in, char *buf, unsigned char *page) {
  int l,len,num=0;

  memset(page,0,256);

  while((!feof(in))&&(num<256)) {
    buf[0]=0;
    if (!fgets(buf,512,in))
      buf[0]=0;
    if (buf[0]=='#')
      continue;
    len=strlen(buf);
    for(l=0;l+1<len;l+=2) {
      if (num<256)
        page[num++]=(unsigned char)fromhex(buf+l);
      else {
        num=-1;
        break;
      }
    }
  }
  return (num==256);
}

/*=========================================================================*
 * function merge_page
 * parameters: pageNum, page to merge
 *             page, resultant memory
 *
 * merge compiled memory onto snapshot state
 *=========================================================================*/
int merge_page(int pageNum, unsigned char *page) {
  unsigned char *scan, *end;
  int a,b,i,walk,mwalk;
  scan=activeBank->bitmap;

  if (pageNum>255)
    return 0;

  /* Scan one page at a time */
  scan+=pageNum*32;
  end=scan+32;
  walk=0;
  mwalk=pageNum*256;

  while(scan!=end) {
    a=*scan;
    b=128;
    for(i=0;i<8;i++) {
      if (a&b) {
        page[walk]=activeBank->memmap[mwalk];
      }
      b=b>>1;
      walk++;
      mwalk++;
    }
    scan++;
  }
  return 1;
}

/*=========================================================================*
 * function save_snapshot
 * parameters: save to an Atari++ snapshot
 *
 * this functions creates an Atari++ snapshot based on a snapshot template
 *=========================================================================*/
int save_snapshot(char *fin, char *fout) {
  FILE *in, *out;
  char *buf;
  unsigned char *page;
  int pageNum;
  int okay;

  in=fopen(fin,"rt");
  if (!in) {
    fprintf(stderr,"Could not open template state file '%s'.\n",fin);
    return 0;
  }
  buf=(char *)malloc(512);
  if (!buf) {
    fprintf(stderr,"Could not allocate work space.\n");
    return 0;
  }
  page=(unsigned char *)malloc(256);
  if (!page) {
    fprintf(stderr,"Could not allocate work space.\n");
    return 0;
  }
  /* try to see if we are really an atari++ state file */
  okay=0;
  while(!feof(in)) {
    buf[0]=0;
    if (!fgets(buf,512,in))
      buf[0]=0;
    if (!strncmp("+RAM::",buf,6)) {
      okay=1;
      break;
    }
  }
  if (!okay) {
    fprintf(stderr,"Template snapshot '%s' not an Atari++ snapshot.\n",fin);
    fclose(in);
    free(buf);
    free(page);
    return 0;
  }

  out=fopen(fout,"wt");
  if (!out) {
    fprintf(stderr,"Cannot open snapshot '%s' for writing.\n",fout);
    free(buf);
    free(page);
    return 0;
  }

  pageNum=0;
  in=fopen(fin,"rt");
  if (in) {
    while(!feof(in)) {
      buf[0]=0;
      if (!fgets(buf,512,in))
        buf[0]=0;
      if (!strncmp("+RAM::",buf,6)) {
        fprintf(out,"%s",buf);
        if (!read_page(in,buf,page)) {
          fprintf(stderr,"Error reading template Atari++ snapshot.\n");
          fclose(in);
          fclose(out);
          free(buf);
          free(page);
          return 0;
        }
        merge_page(pageNum,page);
        save_page(out,page);
        pageNum++;
      } else {
        fprintf(out,"%s",buf);
      }
    }
  }
  fclose(in);
  fclose(out);
  free(buf);
  free(page);
  fprintf(stderr,"Created Atari++ snapshot file '%s'\n",fout);
  return 1;
}
/*=========================================================================*/
