/*==========================================================================
 * Project: ATasm: atari cross assembler
 * File: dimage.c
 *
 * original xfd disk routines based on xfd_tools package by
 * Ivo van Poorten (P) 1995;
 *
 * Other disk/DOS information gleened from Ken Siders, Brian Watson,
 * Jindrich Kubec, and Michael Beck
 *==========================================================================
 * Started: 07/28/97
 * Modified:
 *  01/11/1999 mws moved from EnvisionPC to ATasm
 *                 added delete_file, recognition of DD density disks
 *  10/19/2003 mws added preliminary ATR support, put DD/ED recognition
 *                 into place
 *  10/20/2003 mws DOS 2.5 SS_ED support; Only call read/write VTOC once
 *                 per written file
 *==========================================================================
 *  TODO: Add double-density and dual-density xfd
 *        look at adding ATR support               -- done mws 10/20/2003
 *==========================================================================
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 *===========================================================================*/

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "compat.h"

#define lowb(x) ((x)&0x00ff)
#define highb(x) (((x)>>8)&0x00ff)

#define VTOC_SECTOR 360
#define VTOC_SECTOR2 1024

#define DIR_START_SECTOR 361
#define DIR_END_SECTOR 368
#define DIR_ENTRIES 8
#define DIR_ENTRY_SZ 16

#define SS_SD 720       /* Single Sided, Single Density */
#define SS_ED 1040      /* Single Sided, Enhanced (Medium) Density */
#define SS_DD 720       /* Single Sided, Double Density */
#define DS_DD 1440      /* Double Sided, Double Density */

/* Note on sector usage:
   125/253 sector link high (+ entrynumber in top 6 bits)
   126/254 sector link low
   127/255 count of bytes in use */
/*=========================================================================*/
typedef struct DiskImg {
  FILE *image;
  int header;
  int secSize;
  int dskSize;
  int lnk;
  unsigned char *secbuf;
  unsigned char *VTOCsec;
} DiskImg;
/*=========================================================================*/
int readVTOC(DiskImg *img);
/*=========================================================================*/
void kill_disk(DiskImg *image) {
  fclose(image->image);
  free(image->secbuf);
  free(image->VTOCsec);
  free(image);
}
/*=========================================================================*/
DiskImg *get_new_disk(char *dname) {
  FILE *fd;
  unsigned char hdr[16];
  long lof,imgsz;
  size_t sz;
  DiskImg dimg,*img;
  int ok;

  dimg.header=0;

  fd=fopen(dname,"rb+");
  if (!fd) {
    fprintf(stderr,"Cannot open Atari disk image '%s'\n",dname);
    return NULL;
  }

  sz=fread(hdr,1,16,fd);
  if (sz!=16) {
    fprintf(stderr,"Cannot open Atari disk image '%s'\n",dname);
    return NULL;
  }
  fseek(fd,0L,SEEK_END);
  lof=ftell(fd);
  rewind(fd);

  /* Check for ATR image */
  if ((hdr[0]==0x96)&&(hdr[1]==0x02)) {
    dimg.secSize=((int)hdr[4])+(((int)hdr[5])<<8);
    if ((dimg.secSize==128)||(dimg.secSize==256)) {
      imgsz=(((int)hdr[2])+(((int)hdr[3])<<8)+(((int)hdr[6])<<16)+(((int)hdr[7])<<24))<<4;
      dimg.dskSize=imgsz/dimg.secSize;
      dimg.header=16;
      if (lof!=imgsz+16) {
        fclose(fd);
        fprintf(stderr,"Unrecognized disk image\n");
        return NULL;
      }
    }
  }
  if (!dimg.header) {
    dimg.secSize=128;
    dimg.dskSize=720;
    dimg.secSize=(lof>(1040*128))?256:128;
    dimg.dskSize=lof/dimg.secSize;

    if ((lof!=92160)&&(lof!=184320)&&(lof!=133120)) {
      fclose(fd);
      fprintf(stderr,"Unrecognized disk image\n");
      return NULL;
    }
  }

  if ((dimg.secSize!=128)||((dimg.dskSize!=720)&&(dimg.dskSize!=1040))) {
    fclose(fd);
    fprintf(stderr,"ATasm can currently only handle single or enhanced density .XFD/.ATR images\n");
    fprintf(stderr,"Detected: %s, %d bytes/sec, %d sectors\n",dimg.header?".ATR":".XFD",dimg.secSize,dimg.dskSize);
    return NULL;
  }

  img=(DiskImg *)malloc(sizeof(DiskImg));
  img->image=fd;
  img->header=dimg.header;
  img->secSize=dimg.secSize;
  img->lnk=img->secSize-3;
  img->dskSize=dimg.dskSize;
  img->VTOCsec=(unsigned char *)malloc(256);
  img->secbuf=(unsigned char *)malloc(img->secSize);

  memset(img->secbuf,0,img->secSize);
  memset(img->VTOCsec,0,256);
  ok=readVTOC(img);

  if ((!ok)||(img->VTOCsec[0]!=2)) {
    fprintf(stderr,"ATasm can currently only handle Atari DOS 2.0s, 2.5 or compatibles\n");
    kill_disk(img);
    return NULL;
  }
  return img;
}
/*=========================================================================*/
int sector_pos(DiskImg *img,int sector) {
  if ((img->secSize>128)&&(sector>3))
    return 384+(sector-4)*256+img->header;  /* For SS_DD */
  else
    return (sector-1)*128+img->header; /* For SS_SD/SS_ED */
}
/*=========================================================================*/
void convertfname(char *in, char *out) {
  int x,y;
  char *look;

  look=in+strlen(in);
  while ((*look!='\\')&&(*look!='/')&&(look!=in)) {
    look--;
  }
  in=look;

  for(x=0; x<11; x++)
    out[x]=32;
  out[11]=0;

  x=0;
  y=*in++;

  while ((y!=0)&&(y!='.')) {
    out[x]=TOUPPER(y);
    if(x!=8) x++;
    y=*in++;
  }
  out[8]=32;
  if (y!=0) {
    x=8;
    y=*in++;
    while((x<11)&&(y)&&(y!='.')) {
      out[x]=TOUPPER(y);
      x++;
      y=*in++;
    }
  }
}
/*=========================================================================*/
int readsec(DiskImg *img, int nr) {
  size_t sz;
  if ((nr>img->dskSize)||(nr<1))
    return 0;
  fseek(img->image,(long)sector_pos(img,nr),SEEK_SET);
  sz=fread(img->secbuf,img->secSize,1,img->image);
  if (sz==1)
    return 1;
  return 0;
}
/*=========================================================================*/
int writesec(DiskImg *img, int nr) {
  if ((nr>img->dskSize)||(nr<1))
    return 0;

  fseek(img->image,(long)(sector_pos(img,nr)),SEEK_SET);
  fwrite(img->secbuf,img->secSize,1,img->image);
  return 1;
}
/*=========================================================================*/
int readVTOC(DiskImg *img) {
  size_t sz;
  fseek(img->image,(long)(sector_pos(img,VTOC_SECTOR)),SEEK_SET);
  sz=fread(img->VTOCsec,img->secSize,1,img->image);
  if (sz!=1)
    return 0;
  if (img->dskSize==SS_ED) {
    /* if 2.5 ED VTOC is also at sector 1024, which overlaps in a odd way... */
    unsigned char buf[128];
    fseek(img->image,(long)(sector_pos(img,VTOC_SECTOR2)),SEEK_SET);
    sz=fread(buf,img->secSize,1,img->image);
    if (sz!=1)
      return 0;
    memcpy(img->VTOCsec+100,buf+84,44);
  }
  return 1;
}
/*=========================================================================*/
void writeVTOC(DiskImg *img) {
  if (img->dskSize==SS_ED) {
    unsigned char buf[128];
    /* Note if 2.5 ED/DD VTOC is also at sector 1024 */
    memcpy(buf,img->VTOCsec+10+6,128);
    fseek(img->image,(long)(sector_pos(img,VTOC_SECTOR2)),SEEK_SET);
    fwrite(buf,128,1,img->image);
    memcpy(buf,img->VTOCsec,128);
    memset(buf+100,0,27);
    fseek(img->image,(long)(sector_pos(img,VTOC_SECTOR)),SEEK_SET);
    fwrite(buf,128,1,img->image);
  } else {
    fseek(img->image,(long)(sector_pos(img,VTOC_SECTOR)),SEEK_SET);
    fwrite(img->VTOCsec,img->secSize,1,img->image);
  }
}
/*=========================================================================*/
int find_free_sec(DiskImg *img) {
  int x,y,len;
  int freesec;

  /*  readVTOC(img); */
  if (img->dskSize==SS_ED)
    len=138;
  else
    len=100;

  for(x=10;x<len;x++)
    if (img->VTOCsec[x]!=0) break;

  freesec=(x-10)*8;

  y=img->VTOCsec[x];

  /* if (y&0x80) freesec+=0; */
  if (y&0x40) freesec+=1;
  else if (y&0x20) freesec+=2;
  else if (y&0x10) freesec+=3;
  else if (y&0x08) freesec+=4;
  else if (y&0x04) freesec+=5;
  else if (y&0x02) freesec+=6;
  else if (y&0x01) freesec+=7;

  return freesec;
}
/*=========================================================================*/
void freesec(DiskImg *img, int nr) {
  int byte,bit,secsfree;

  /* readVTOC(img); */

  byte=nr/8;
  bit=nr%8;

  img->VTOCsec[10+byte]|=(0x80>>bit);
  if (nr<720) {
    secsfree=img->VTOCsec[3]+img->VTOCsec[4]*256;
    secsfree++;
    img->VTOCsec[3]=lowb(secsfree);
    img->VTOCsec[4]=highb(secsfree);
  } else if (img->dskSize==SS_ED) {
    secsfree=img->VTOCsec[138]+img->VTOCsec[139]*256;
    secsfree++;
    img->VTOCsec[138]=lowb(secsfree);
    img->VTOCsec[139]=highb(secsfree);
  }

  /* writeVTOC(img); */
}
/*=========================================================================*/
void marksec(DiskImg *img, int nr) {
  int byte,bit;
  int secsfree;

  /* readVTOC(img); */

  byte=nr/8;
  bit=nr%8;

  img->VTOCsec[10+byte]&=((0x80>>bit)^0xff);
  if (nr<720) {
    secsfree=img->VTOCsec[3]+img->VTOCsec[4]*256;
    secsfree--;
    img->VTOCsec[3]=lowb(secsfree);
    img->VTOCsec[4]=highb(secsfree);
  } else if (img->dskSize==SS_ED) {
    secsfree=img->VTOCsec[138]+img->VTOCsec[139]*256;
    secsfree--;
    img->VTOCsec[138]=lowb(secsfree);
    img->VTOCsec[139]=highb(secsfree);
  }
  /*  writeVTOC(img); */
}
/*=========================================================================*/
int scandir(DiskImg *img, char *filename, int del) {
  int secnum,cnt,status,startsec;
  int endofdir;
  char fname[12];

  /* For each entry:
     flags - 0x80 delete; 0x40 in use; 0x20 locked; 0x2 dos2; 0x3 dos25?
     count - sector count low
     count - sector count high
     start - first sector low
     start - first sector high
     name[8] - file name [space padded]
     ext[3] - file ext [space padded]
  */

  endofdir=0;
  secnum=DIR_START_SECTOR;
  startsec=-1;

  while(!endofdir) {
    readsec(img,secnum);

    for(cnt=0; cnt<DIR_ENTRIES; cnt++) {
      status=img->secbuf[cnt*DIR_ENTRY_SZ];
      /*length=img->secbuf[cnt*DIR_ENTRY_SZ+1]+256*img->secbuf[cnt*DIR_ENTRY_SZ+2];*/

      if (!status) {
        endofdir=1;
        break;
      }

      if (!(status&0x80)) {
        memcpy(fname,&img->secbuf[cnt*DIR_ENTRY_SZ+5],11);
        fname[11]=0;
        if (!strncmp(filename,fname,11)) {
          startsec=img->secbuf[cnt*DIR_ENTRY_SZ+3]+img->secbuf[cnt*DIR_ENTRY_SZ+4]*256;
          if (del) {
            /* It turns out that purging directory entry causes DOS to stop
               reading the directory... better just mark as deleted */
            img->secbuf[cnt*DIR_ENTRY_SZ]|=0x80;
            writesec(img,secnum);
          }
        }
      }
    }
    secnum++;
    if (secnum>DIR_END_SECTOR)
      endofdir=1;
  }
  return startsec;
}
/*=========================================================================*/
void writedirentry(DiskImg *img, char *file, int startsec, int len, int entry, int ed){
  int qwe,asd;
  int x;

  qwe=entry/8;
  asd=entry%8;

  readsec(img,DIR_START_SECTOR+qwe);

  if (ed)
    img->secbuf[asd*16+0]=0x3; /* Mark as DOS2.5 > 719 */
  else
    img->secbuf[asd*16+0]=0x42; /* Mark in-use for DOS2 */
  img->secbuf[asd*16+1]=lowb(len/img->lnk+1);
  img->secbuf[asd*16+2]=highb(len/img->lnk+1);
  img->secbuf[asd*16+3]=lowb(startsec);
  img->secbuf[asd*16+4]=highb(startsec);

  for(x=0;x<12;x++)
    img->secbuf[asd*16+5+x]=file[x];

  writesec(img,DIR_START_SECTOR+qwe);
}
/*=========================================================================*/
int find_newentry(DiskImg *img) {
  int secnum,cnt,status,entrynum;
  int endofdir;

  endofdir=0;
  secnum=DIR_START_SECTOR;
  entrynum=-1;

  while(!endofdir) {
    readsec(img,secnum);

    for(cnt=0;cnt<8;cnt++) {
      status=img->secbuf[cnt*16];

      if ((status==0)||(status&0x80)) {
        entrynum=(secnum-DIR_START_SECTOR)*8+cnt;
        endofdir=1;
        break;
      }
    }
    secnum++;
    if (secnum>368)
      endofdir=1;
  }
  return entrynum;
}
/*=========================================================================*/
int delete_file(DiskImg *img, char *filename) {
  int i,secnum,startsec;

  /* Find starting sector of file to delete */
  startsec=scandir(img,filename,1);

  if (startsec>=0) {
    i=secnum=startsec;
    while(i) {
      readsec(img,secnum);
      i=img->secbuf[img->lnk+1]+((img->secbuf[img->lnk]&0x03)<<8);
      memset(img->secbuf,0,img->secSize);
      writesec(img,secnum);
      freesec(img,secnum);
      secnum=i;
    }
    return 1;
  }
  return 0;
}
/*=========================================================================*/
int write_xfd_file(char *fimage, char *file) {
  FILE *in;
  DiskImg *image;
  size_t sz;
  int startsec,cursec,nextsec;
  int entrynum, secsfree;
  int qwe,x,max,ed;
  long lof;
  char fname[12];
  unsigned char data[128];

  ed=cursec=0; /* remove annoying warning */

  in=fopen(file,"rb");
  if (!in) {
    fprintf(stderr,"Unable to open input binary.\n");
    return -1;
  }

  image=get_new_disk(fimage);
  if (!image) {
    fclose(in);
    return -2;
  }
  fseek(in,0L,SEEK_END);
  lof=ftell(in);
  rewind(in);
  max=lof;
  convertfname(file,fname);

  startsec=scandir(image,fname,0);
  if (startsec>=0)  {
    fprintf(stderr,"*Warning* Removing existing file on Atari disk image.\n");
    delete_file(image,fname);
  }

  /* check free sectors */
  secsfree=image->VTOCsec[3]+image->VTOCsec[4]*256;
  if (image->dskSize==SS_ED) {
    secsfree+=image->VTOCsec[138]+image->VTOCsec[139]*256;
  }

  /* check if input is too big */
  if ((secsfree*image->lnk)<max) {
    kill_disk(image);
    fclose(in);
    fprintf(stderr,"Not enough room on Atari disk image.\n");
    return -1;
  }

  /* find place in directory */
  entrynum=find_newentry(image);
  if (entrynum==-1) {
    kill_disk(image);
    fclose(in);
    fprintf(stderr,"Not enough room on Atari disk image.\n");
    return -1;
  }

  /* find first free sector (=startsec) */
  startsec=find_free_sec(image);

  /* write file */
  qwe=max%image->lnk;
  for(x=0;x<(max/image->lnk); x++) {
    cursec=find_free_sec(image);
    marksec(image,cursec);
    nextsec=find_free_sec(image);
    if (in) {
      sz=fread(data,1,image->lnk,in);
      memcpy(image->secbuf,data,sz);
    } else
      memcpy(image->secbuf,data+x*image->lnk,image->lnk);

    image->secbuf[image->lnk]=(entrynum<<2)+((highb(nextsec))&0x03);
    image->secbuf[image->lnk+1]=lowb(nextsec);
    image->secbuf[image->lnk+2]=image->lnk;
    writesec(image,cursec);
    if ((cursec>719)&&(image->dskSize==SS_ED))
      ed=1;
  }
  if (qwe) {
    x=max/image->lnk;
    cursec=find_free_sec(image);
    marksec(image,cursec);
    if (in) {
      sz=fread(data,1,image->lnk,in);
      memcpy(image->secbuf,data,sz);
    } else
      memcpy(image->secbuf,data+x*image->lnk,qwe);
    image->secbuf[image->lnk]=(entrynum<<2);
    image->secbuf[image->lnk+1]=0;
    image->secbuf[image->lnk+2]=qwe;
    writesec(image,cursec);
    if ((cursec>719)&&(image->dskSize==SS_ED))
      ed=1;
  } else {
    image->secbuf[image->lnk]=(entrynum<<2);
    image->secbuf[image->lnk+1]=0;
    writesec(image,cursec);
    if ((cursec>719)&&(image->dskSize==SS_ED))
      ed=1;
  }

  /* Save our changes... */
  writeVTOC(image);

  /* write directory entry */
  writedirentry(image,fname,startsec,max,entrynum,ed);

  /* close and exit */
  fprintf(stderr,"Binary file '%s' saved to %s image '%s'\n",file,image->header?".ATR":".XFD",fimage);

  kill_disk(image);
  fclose(in);
  return 0;
}
/*=========================================================================*/
