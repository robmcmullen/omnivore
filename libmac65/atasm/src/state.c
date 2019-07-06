/*===========================================================================
 * Project: ATasm: atari cross assembler
 * File: state.c
 *
 * Contains code for reading and saving machine state
 * This is based on the state file as defined in Atari800-0.9.8g,
 * the file specification may change as time goes on.
 *
 * This code is largely expirimental, but has been tested successfully with
 * Atari800Win2.5c and Atari800-0.9.8g
 *===========================================================================
 * Created: 12/19/98 mws  (I/O code based off of source from Atari800-0.9.8g)
 *
 * Modifications:
 *  10/22/2003 - updated to be compatible with Atari 1.3.0 cvs (save state 3)
 *
 *===========================================================================
 * TODO:
 *  Verify compatibility with version 2 state files (do they exist anymore?)
 *
 *  If assembling to ROM area, and an XL/XE snapshot assume they are
 *  actually writing to RAM underneath...
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

#include "symbol.h"

#ifdef ZLIB_CAPABLE

#include "zlib.h"

#define GZOPEN( X, Y )		gzopen( X, Y )
#define GZCLOSE( X )		gzclose( X )
#define GZREAD( X, Y, Z )	gzread( X, Y, Z )
#define GZWRITE( X, Y, Z )	gzwrite( X, Y, Z )
#else	/* ZLIB_CAPABLE */
#define GZOPEN( X, Y )		fopen( X, Y )
#define GZCLOSE( X )		fclose( X )
#define GZREAD( X, Y, Z )	fread( Y, Z, 1, X )
#define GZWRITE( X, Y, Z )	fwrite( Y, Z, 1, X )
#define gzFile FILE *
#endif	/* not ZLIB_CAPABLE */

/* Some Emulator specific defines... */
#define UBYTE unsigned char
#define UWORD unsigned short int

gzFile StateIn;
gzFile StateOut;

typedef enum {
  TV_PAL,
  TV_NTSC
} TVmode;

typedef enum {
  Atari_OSA,
  Atari_OSB,
  AtariXLXE,
  Atari5200
} Machine;

#define RAM 0
#define ROM 1
#define HARDWARE 2

/* Work space for saving/loading state files */
TVmode tv_mode;
Machine machine;
int os, pil_on, default_tv_mode, default_system, ram_size;
int mach_xlxe;
UBYTE Antic4;
UWORD CPU2;

UBYTE *Antic1,*CPU1,*memory, *attrib, *atari_basic, *atarixl_os;
UBYTE *atarixe_memory, *under_atari_basic, *under_atarixl_os;
UWORD *Antic2;
int *Antic3;

/*==========================================================================*/
/* Value is memory location of data, num is number of type to save */
void SaveUBYTE(UBYTE *data, int num) {
  int result;

  /* Assumption is that UBYTE = 8bits and the pointer passed in refers
     directly to the active bits if in a padded location. If not (unlikely)
     you'll have to redefine this to save appropriately for cross-platform
     compatibility */
  result = GZWRITE( StateOut, data, num );
  if (result == 0) {
    fprintf(stderr,"Error updating state file.\n");
    exit(-1);
  }
}
/*==========================================================================*/
void ReadUBYTE(UBYTE *data, int num) {
  int result;

  result = GZREAD( StateIn, data, num );
  if (result == 0) {
    fprintf(stderr,"Error updating state file.\n");;
    exit(-1);
  }
}
/*==========================================================================*/
/* Value is memory location of data, num is number of type to save */
void SaveUWORD( UWORD *data, int num ) {
  /* UWORDS are saved as 16bits, regardless of the size on this particular
     platform. Each byte of the UWORD will be pushed out individually in
     LSB order. The shifts here and in the read routines will work for both
     LSB and MSB architectures. */
  while( num > 0 ) {
    UWORD temp;
    UBYTE byte;
    int	result;

    temp = *data;
    byte = temp & 0xff;
    result = GZWRITE( StateOut, &byte, 1 );
    if( result == 0 ) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    temp >>= 8;
    byte = temp & 0xff;
    result = GZWRITE( StateOut, &byte, 1 );
    if( result == 0 )
    {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }
    num--;
    data++;
  }
}
/*==========================================================================*/
/* Value is memory location of data, num is number of type to save */
void ReadUWORD( UWORD *data, int num ) {
  while(num >0) {
    UBYTE	byte1, byte2;
    int	result;

    result = GZREAD( StateIn, &byte1, 1 );
    if( result == 0 ) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    result = GZREAD( StateIn, &byte2, 1 );
    if( result == 0 ) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }
    *data = (byte2 << 8) | byte1;
    num--;
    data++;
  }
}
/*==========================================================================*/
void SaveINT( int *data, int num ) {
  unsigned char signbit = 0;

  if( *data < 0 )
    signbit = 0x80;

  /* INTs are always saved as 32bits (4 bytes) in the file. They can
     be any size on the platform however. The sign bit is clobbered
     into the fourth byte saved for each int; on read it will be
     extended out to its proper position for the native INT size */
  while( num > 0 ) {
    unsigned int	temp;
    UBYTE	byte;
    int result;

    temp = (unsigned int)*data;

    byte = temp & 0xff;
    result = GZWRITE( StateOut, &byte, 1 );
    if (result == 0) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    temp >>= 8;
    byte = temp & 0xff;
    result = GZWRITE( StateOut, &byte, 1 );
    if( result == 0 ) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    temp >>= 8;
    byte = temp & 0xff;
    result = GZWRITE( StateOut, &byte, 1 );
    if( result == 0 ) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    temp >>= 8;
    byte = temp & 0xff;
    /* Possible sign bit is always saved on fourth byte */
    byte &= signbit;
    result = GZWRITE( StateOut, &byte, 1 );
    if( result == 0 ) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    num--;
    data++;
  }
}
/*==========================================================================*/
void ReadINT( int *data, int num ) {
  unsigned char signbit = 0;

  while (num>0) {
    int	temp;
    UBYTE byte1, byte2, byte3, byte4;
    int result;

    result = GZREAD(StateIn, &byte1, 1);
    if (result==0) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    result=GZREAD(StateIn, &byte2, 1);
    if (result==0) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    result=GZREAD(StateIn, &byte3, 1);
    if(result == 0) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    result=GZREAD(StateIn, &byte4, 1);
    if(result==0) {
      fprintf(stderr,"Error updating state file.\n");;
      num = 0;
      continue;
    }

    signbit = byte4 & 0x80;
    byte4 &= 0x7f;

    temp = (byte4 << 24) | (byte3 << 16) | (byte2 << 8) | byte1;
    if( signbit )
      temp = -temp;
    *data = temp;

    num--;
    data++;
  }
}
/*==========================================================================*/
void MainStateRead() {
  UBYTE temp;

  ReadUBYTE(&temp, 1);
  if(!temp)
    tv_mode = TV_PAL;
  else
    tv_mode = TV_NTSC;

  mach_xlxe = 0;
  ReadUBYTE(&temp,1);
  ReadINT(&os,1);
  switch(temp) {
  case 0:
    machine = os==1 ? Atari_OSA : Atari_OSB;
    ram_size=48;
    break;
  case 1:
    machine = AtariXLXE;
    ram_size=64;
    mach_xlxe = 1;
    break;
  case 2:
    machine = AtariXLXE;
    ram_size=128;
    mach_xlxe = 1;
    break;
  case 3:
    machine = AtariXLXE;
    ram_size=320;
    mach_xlxe = 1;
    break;
  case 4:
    machine = Atari5200;
    ram_size=16;
    break;
  case 5:
    machine = os==1 ? Atari_OSA : Atari_OSB;
    ram_size=16;
    break;
  case 6:
    machine = AtariXLXE;
    ram_size=16;
    break;
  case 7:
    machine = AtariXLXE;
    ram_size=576;
    break;
  case 8:
    machine = AtariXLXE;
    ram_size=1088;
    break;

  default:
    machine = AtariXLXE;
    ram_size=64;
    fprintf(stderr, "Warning: Bad machine type in state save, defaulting to XL\n" );
    break;
  }
  ReadINT(&pil_on,1);
  ReadINT(&default_tv_mode,1);
  ReadINT(&default_system,1);
}
/*==========================================================================*/
void MainStateSave() {
  UBYTE temp;

  /* Possibly some compilers would handle an enumerated type differently,
     so convert these into unsigned bytes and save them out that way */
  if (tv_mode==TV_PAL)
    temp = 0;
  else
    temp = 1;

  SaveUBYTE(&temp, 1);

  if( machine == Atari_OSA ) {
    temp = ram_size==16 ? 5:0;
    os=1;
    default_system=1;
  } else if( machine == Atari_OSB ) {
    temp = ram_size==16 ? 5:0;
    os=2;
    default_system=2;
  } else if( machine == AtariXLXE ) {
    switch(ram_size) {
    case 16:
      temp = 6;
      default_system = 3;
      break;
    case 64:
      temp = 1;
      default_system = 3;
      break;
    case 128:
      temp = 2;
      default_system = 4;
      break;
    case 320:
    case 321:
      temp = 3;
      default_system = 5;
      break;
    case 576:
      temp = 7;
      default_system = 6;
      break;
    case 1088:
      temp = 8;
      default_system = 7;
      break;
    }
  } else if( machine == Atari5200 ) {
    temp = 4;
    default_system = 6;
  }

  SaveUBYTE(&temp, 1);
  SaveINT(&os, 1);
  SaveINT(&pil_on, 1);
  SaveINT(&default_tv_mode, 1);
  SaveINT(&default_system, 1);
}
/*==========================================================================*/
void AnticStateRead(int ver) {
  if (ver==2) { /* WinAtari800 */
    Antic1=(UBYTE *)malloc(sizeof(UBYTE)*1855);
    Antic2=(UWORD *)malloc(sizeof(UWORD)*37);
    Antic3=(int *)malloc(sizeof(int)*41);
    ReadUBYTE(Antic1,1855);
    ReadUWORD(Antic2,37);
    ReadINT(Antic3,41);
    ReadUBYTE(&Antic4,1);
  } else if (ver==3) { /* Atari800 > 1.0.0 statefile / atari800win */
    Antic1=(UBYTE *)malloc(sizeof(UBYTE)*14);
    Antic2=(UWORD *)malloc(sizeof(UWORD)*2);
    Antic3=(int *)malloc(sizeof(int)*3);
    ReadUBYTE(Antic1,14);
    ReadUWORD(Antic2,2);
    ReadINT(Antic3,3);
  }
}
/*==========================================================================*/
void AnticStateSave(int ver) {
  if (ver==2) {  /* WinAtari800 */
    SaveUBYTE(Antic1,1855);
    SaveUWORD(Antic2,37);
    SaveINT(Antic3,41);
    SaveUBYTE(&Antic4,1);
    free(Antic1);
    free(Antic2);
    free(Antic3);
  } else if (ver==3) {  /* Atari800 > 1.0.0 statefile / atari800win */
    SaveUBYTE(Antic1,14);
    SaveUWORD(Antic2,2);
    SaveINT(Antic3,3);
    free(Antic1);
    free(Antic2);
    free(Antic3);
  }
}
/*==========================================================================*/
void CpuStateSave(UBYTE SaveVerbose) {
  SaveUBYTE(CPU1,6);
  free(CPU1);

  SaveUBYTE(&memory[0],65536);
  SaveUBYTE(&attrib[0],65536);
  free(memory);
  free(attrib);

  if (mach_xlxe) {
    if(SaveVerbose!=0) {
      SaveUBYTE(&atari_basic[0],8192);
      free(atari_basic);
    }
    SaveUBYTE(&under_atari_basic[0],8192);
    free(under_atari_basic);

    if(SaveVerbose!=0) {
      SaveUBYTE(&atarixl_os[0],16384);
      free(atarixl_os);
    }
    SaveUBYTE( &under_atarixl_os[0],16384);
    free(under_atarixl_os);
  }
}
/*==========================================================================*/
void CpuStateRead(UBYTE SaveVerbose) {
  CPU1=(UBYTE *)malloc(sizeof(UBYTE)*6);
  atari_basic=under_atari_basic=atarixl_os=
                                under_atarixl_os=atarixe_memory=NULL;

  memory=(UBYTE *)malloc(sizeof(UBYTE)*65536);
  attrib=(UBYTE *)malloc(sizeof(UBYTE)*65536);

  ReadUBYTE(CPU1,6);
  ReadUBYTE(&memory[0],65536);
  ReadUBYTE(&attrib[0],65536);

  if (mach_xlxe) {
    if (SaveVerbose!=0) {
      atari_basic=(UBYTE *)malloc(sizeof(UBYTE)*8192);
      ReadUBYTE(&atari_basic[0], 8192);
    }
    under_atari_basic=(UBYTE *)malloc(sizeof(UBYTE)*8192);
    ReadUBYTE(&under_atari_basic[0], 8192);

    if (SaveVerbose!=0) {
      atarixl_os=(UBYTE *)malloc(sizeof(UBYTE)*16384);
      ReadUBYTE(&atarixl_os[0],16384);
    }
    under_atarixl_os=(UBYTE *)malloc(sizeof(UBYTE)*16384);
    ReadUBYTE( &under_atarixl_os[0],16384);
  }
}
/*==========================================================================*/
int FileCopy(gzFile in, gzFile out) {
  int result;
  UBYTE *buf;

  buf=(UBYTE *)malloc(16384);

  do {
    result=GZREAD(in,buf,16384);
    GZWRITE(out,buf,result);
  } while(result==16384);

  free(buf);
  return 1;
}
/*==========================================================================*/
int Update_Mem() {
  unsigned char *scan, *end;
  int a,b,i,walk;
  char *tp[]={"ROM","HARDWARE"};
  scan=activeBank->bitmap;
  end=scan+8192;
  walk=0;

  while(scan!=end) {
    a=*scan;
    b=128;
    for(i=0;i<8;i++) {
      if (a&b) {
        memory[walk]=activeBank->memmap[walk];
        if (attrib[walk]!=RAM) {
          fprintf(stderr,"Warning: Compiling to %s at location %.4X\n",
                  tp[attrib[walk]-1],walk);
        }
      }
      b=b>>1;
      walk++;
    }
    scan++;
  }
  return 1;
}
/*==========================================================================*/
int save_A800state(char *fin, char *fout) {
  int result, result1;
  char	header_string[9];
  UBYTE	StateVersion  = 0; /* The version of the save file */
  UBYTE	SaveVerbose   = 0; /* Verbose mode means save basic, OS if patched */

  StateIn=GZOPEN(fin,"rb");
  if(!StateIn) {
    fprintf(stderr,"Could not open template state file '%s'.\n",fin);
    return 0;
  }

  result=GZREAD(StateIn,header_string,8);
  header_string[8]=0;
  if(strcmp(header_string,"ATARI800")) {
    fprintf(stderr, "'%s' is not an Atari800 state file.\n",fin);
    result=GZCLOSE(StateIn);
    return 0;
  }

  result=GZREAD(StateIn,&StateVersion,1);
  result1=GZREAD(StateIn,&SaveVerbose,1);
  if(result==0||result1==0) {
    fprintf(stderr, "Couldn't read from state file '%s'.\n",fin);
    result = GZCLOSE(StateIn);
    return 0;
  }

  if(( StateVersion != 2) && (StateVersion!=3 )) {
    fprintf(stderr, "'%s' is an incompatible state file version [%d].\n",fin,StateVersion);
    result=GZCLOSE(StateIn);
    return 0;
  }

  MainStateRead();
  AnticStateRead(StateVersion);
  CpuStateRead(SaveVerbose);

  StateOut=GZOPEN(fout,"wb");
  if(!StateOut) {
    fprintf(stderr, "Could not open '%s' for state save.\n",fout);
    return 0;
  }
  result = GZWRITE(StateOut,"ATARI800",8);
  if(!result) {
    fprintf(stderr, "Could not save to '%s'\n",fout);
    return 0;
  }

  SaveUBYTE(&StateVersion, 1);
  SaveUBYTE(&SaveVerbose, 1);

  MainStateSave();
  AnticStateSave(StateVersion);
  Update_Mem();
  CpuStateSave(SaveVerbose);
  FileCopy(StateIn,StateOut);

  result=GZCLOSE(StateOut);
  result=GZCLOSE(StateIn);

  fprintf(stderr,"Created Atari800 state file '%s'\n",fout);
  return 1;
}
/*==========================================================================*/
int templateType(char *fin) {
  FILE *in;
  int result;
  char header_string[64];
  char *buf;

  /* Guess if we are an atari++ save file */
  in=fopen(fin,"rb");
  if(!in) {
    fprintf(stderr,"Could not open template state file '%s'.\n",fin);
    return 0;
  }
  buf=(char *)malloc(8192);
  while(!feof(in)) {
    result=fread(buf,1,8191,in);
    buf[result]=0;
    if (strstr(buf,"+RAM::Page")) {
      free(buf);
      fclose(in);
      return 2;
    }
  }
  free(buf);
  fclose(in);

  /* Check for Atari800 save file */
  StateIn=GZOPEN(fin,"rb");
  if(!StateIn) {
    fprintf(stderr,"Could not open template state file '%s'.\n",fin);
    return 0;
  }
  result=GZREAD(StateIn,header_string,8);
  header_string[8]=0;
  if(!strcmp(header_string,"ATARI800")) {
    result=GZCLOSE(StateIn);
    return 1;
  }
  GZCLOSE(StateIn);

  return 0;
}
/*=========================================================================*/
int save_state(char *fin, char *fname) {
  int tp=templateType(fin);

  fname[find_extension(fname)]=0;

  if (tp==1) {
    strcat(fname,".a8s");
  } else if (tp==2) {
    strcat(fname,".state");
  } else return 0;

  if (!strcmp(fin,fname)) {
    fprintf(stderr,"Error: template state file and save state file cannot be the same!\n");
    return 0;
  }

  if (tp==1)
    return save_A800state(fin,fname);

  return save_snapshot(fin,fname);
}
/*=========================================================================*/
