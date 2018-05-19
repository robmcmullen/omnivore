#  -*- coding: utf-8 -*-
# Atari constants from the atari800 project, GPL licensed.  Transformed using
# the find regex: \{(\".+\"),\s*(0x[0-9a-fA-F]+).*$ and replace regex: \2: \1,


class EmptyMemoryMap(object):
    name = "No Memory Map"

    rmemmap = {}
    wmemmap = {}

    @classmethod
    def get_name(cls, addr, write=False):
        if write:
            if addr in cls.wmemmap:
                return cls.wmemmap[addr]
        if addr in cls.rmemmap:
            return cls.rmemmap[addr]
        return ""

    def __contains__(self, addr):
        return addr in self.rmemmap or addr in self.wmemmap


class Atari800MemoryMap(EmptyMemoryMap):
    name = "Atari 400/800"

    rmemmap = {
        0x0000: "LNFLG",
        0x0001: "NGFLAG",
        0x0002: "CASINI",
        0x0003: "CASINI+1",
        0x0004: "RAMLO",
        0x0005: "RAMLO+1",
        0x0006: "TRAMSZ",
        0x0007: "CMCMD",
        0x0008: "WARMST",
        0x0009: "BOOT?",
        0x000a: "DOSVEC",
        0x000b: "DOSVEC+1",
        0x000c: "DOSINI",
        0x000d: "DOSINI+1",
        0x000e: "APPMHI",
        0x000f: "APPMHI+1",
        0x0010: "POKMSK",
        0x0011: "BRKKEY",
        0x0012: "RTCLOK",
        0x0013: "RTCLOK+1",
        0x0014: "RTCLOK+2",
        0x0015: "BUFADR",
        0x0016: "BUFADR+1",
        0x0017: "ICCOMT",
        0x0018: "DSKFMS",
        0x0019: "DSKFMS+1",
        0x001a: "DSKUTL",
        0x001b: "DSKUTL+1",
        0x001c: "ABUFPT",
        0x001d: "ABUFPT+1",
        0x001e: "ABUFPT+2",
        0x001f: "ABUFPT+3",
        0x0020: "ICHIDZ",
        0x0021: "ICDNOZ",
        0x0022: "ICCOMZ",
        0x0023: "ICSTAZ",
        0x0024: "ICBALZ",
        0x0025: "ICBAHZ",
        0x0026: "ICPTLZ",
        0x0027: "ICPTHZ",
        0x0028: "ICBLLZ",
        0x0029: "ICBLHZ",
        0x002a: "ICAX1Z",
        0x002b: "ICAX2Z",
        0x002c: "ICSPRZ",
        0x002d: "ICSPRZ+1",
        0x002e: "ICIDNO",
        0x002f: "CIOCHR",
        0x0030: "STATUS",
        0x0031: "CHKSUM",
        0x0032: "BUFRLO",
        0x0033: "BUFRHI",
        0x0034: "BFENLO",
        0x0035: "BFENHI",
        0x0036: "LTEMP",
        0x0037: "LTEMP+1",
        0x0038: "BUFRFL",
        0x0039: "RECVDN",
        0x003a: "XMTDON",
        0x003b: "CHKSNT",
        0x003c: "NOCKSM",
        0x003d: "BPTR",
        0x003e: "FTYPE",
        0x003f: "FEOF",
        0x0040: "FREQ",
        0x0041: "SOUNDR",
        0x0042: "CRITIC",
        0x0043: "FMSZPG",
        0x0044: "FMSZPG+1",
        0x0045: "FMSZPG+2",
        0x0046: "FMSZPG+3",
        0x0047: "FMSZPG+4",
        0x0048: "FMSZPG+5",
        0x0049: "FMSZPG+6",
        0x004a: "ZCHAIN",
        0x004b: "ZCHAIN+1",
        0x004c: "DSTAT",
        0x004d: "ATRACT",
        0x004e: "DRKMSK",
        0x004f: "COLRSH",
        0x0050: "TMPCHR",
        0x0051: "HOLD1",
        0x0052: "LMARGN",
        0x0053: "RMARGN",
        0x0054: "ROWCRS",
        0x0055: "COLCRS",
        0x0056: "COLCRS+1",
        0x0057: "DINDEX",
        0x0058: "SAVMSC",
        0x0059: "SAVMSC+1",
        0x005a: "OLDROW",
        0x005b: "OLDCOL",
        0x005c: "OLDCOL+1",
        0x005d: "OLDCHR",
        0x005e: "OLDADR",
        0x005f: "OLDADR+1",
        0x0060: "FKDEF",
        0x0061: "FKDEF+1",
        0x0062: "PALNTS",
        0x0063: "LOGCOL",
        0x0064: "ADRESS",
        0x0065: "ADRESS+1",
        0x0066: "TOADR",
        0x0067: "TOADR+1",
        0x0068: "SAVADR",
        0x0069: "SAVADR+1",
        0x006a: "RAMTOP",
        0x006b: "BUFCNT",
        0x006c: "BUFSTR",
        0x006d: "BUFSTR+1",
        0x006e: "BITMSK",
        0x006f: "SHFAMT",
        0x0070: "ROWAC",
        0x0071: "ROWAC+1",
        0x0072: "COLAC",
        0x0073: "COLAC+1",
        0x0074: "ENDPT",
        0x0075: "ENDPT+1",
        0x0076: "DELTAR",
        0x0077: "DELTAC",
        0x0078: "DELTAC+1",
        0x0079: "KEYDEF",
        0x007a: "KEYDEF+1",
        0x007b: "SWPFLG",
        0x007c: "HOLDCH",
        0x007d: "INSDAT",
        0x007e: "COUNTR",
        0x007f: "COUNTR+1",
        0x0080: "LOMEM",
        0x0081: "LOMEM+1",
        0x0082: "VNTP",
        0x0083: "VNTP+1",
        0x0084: "VNTD",
        0x0085: "VNTD+1",
        0x0086: "VVTP",
        0x0087: "VVTP+1",
        0x0088: "STMTAB",
        0x0089: "STMTAB+1",
        0x008a: "STMCUR",
        0x008b: "STMCUR+1",
        0x008c: "STARP",
        0x008d: "STARP+1",
        0x008e: "RUNSTK",
        0x008f: "RUNSTK+1",
        0x0090: "MEMTOP",
        0x0091: "MEMTOP+1",
        0x0092: "MEOLFLG",
        0x0094: "COX",
        0x0095: "POKADR",
        0x0096: "POKADR+1",
        0x0097: "SVESA",
        0x0098: "SVESA+1",
        0x0099: "MVFA",
        0x009a: "MVFA+1",
        0x009b: "MVTA",
        0x009c: "MVTA+1",
        0x009d: "CPC",
        0x009e: "CPC+1",
        0x009f: "LLNGTH",
        0x00a0: "TSLNUM",
        0x00a1: "TSLNUM+1",
        0x00a2: "MVLNG",
        0x00a3: "MVLNG+1",
        0x00a4: "ECSIZE",
        0x00a5: "ECSIZE+1",
        0x00a6: "DIRFLG",
        0x00a7: "STMLBD",
        0x00a8: "STINDEX",
        0x00a9: "OPSTKX",
        0x00aa: "ARSTKX",
        0x00ab: "EXSVOP",
        0x00ac: "EXSVPR",
        0x00ad: "LELNUM",
        0x00ae: "LELNUM+1",
        0x00af: "STENUM",
        0x00b0: "COMCNT",
        0x00b1: "ADFLAG",
        0x00b2: "SVDISP",
        0x00b3: "ONLOOP",
        0x00b4: "ENTDTD",
        0x00b5: "LISTDTD",
        0x00b6: "DATAD",
        0x00b7: "DATALN",
        0x00b8: "DATALN+1",
        0x00b9: "ERRNUM",
        0x00ba: "STOPLN",
        0x00bb: "STOPLN+1",
        0x00bc: "TRAPLN",
        0x00bd: "TRAPLN+1",
        0x00be: "SAVCUR",
        0x00bf: "SAVCUR+1",
        0x00c0: "IOCMD",
        0x00c1: "IODVC",
        0x00c2: "PROMPT",
        0x00c3: "ERRSAV",
        0x00c4: "TEMPA",
        0x00c5: "TEMPA+1",
        0x00c6: "ZTEMP2",
        0x00c7: "ZTEMP2+1",
        0x00c8: "COLOR",
        0x00c9: "PTABW",
        0x00ca: "LOADFLG",
        0x00d2: "VTYPE",
        0x00d3: "VNUM",
        0x00d4: "FR0",
        0x00d5: "FR0+1",
        0x00d6: "FR0+2",
        0x00d7: "FR0+3",
        0x00d8: "FR0+4",
        0x00d9: "FR0+5",
        0x00da: "FRE",
        0x00db: "FRE+1",
        0x00dc: "FRE+2",
        0x00dd: "FRE+3",
        0x00de: "FRE+4",
        0x00df: "FRE+5",
        0x00e0: "FR1",
        0x00e1: "FR1+1",
        0x00e2: "FR1+2",
        0x00e3: "FR1+3",
        0x00e4: "FR1+4",
        0x00e5: "FR1+5",
        0x00e6: "FR2",
        0x00e7: "FR2+1",
        0x00e8: "FR2+2",
        0x00e9: "FR2+3",
        0x00ea: "FR2+4",
        0x00eb: "FR2+5",
        0x00ec: "FRX",
        0x00ed: "EEXP",
        0x00ee: "NSIGN",
        0x00ef: "ESIGN",
        0x00f0: "FCHRFLG",
        0x00f1: "DIGRT",
        0x00f2: "CIX",
        0x00f3: "INBUFF",
        0x00f4: "INBUFF+1",
        0x00f5: "ZTEMP1",
        0x00f6: "ZTEMP1+1",
        0x00f7: "ZTEMP4",
        0x00f8: "ZTEMP4+1",
        0x00f9: "ZTEMP3",
        0x00fa: "ZTEMP3+1",
        0x00fb: "RADFLG",
        0x00fc: "FLPTR",
        0x00fd: "FLPTR+1",
        0x00fe: "FPTR2",
        0x00ff: "FPTR2+1",
        0x0200: "VDSLST",
        0x0201: "VDSLST+1",
        0x0202: "VPRCED",
        0x0203: "VPRCED+1",
        0x0204: "VINTER",
        0x0205: "VINTER+1",
        0x0206: "VBREAK",
        0x0207: "VBREAK+1",
        0x0208: "VKEYBD",
        0x0209: "VKEYBD+1",
        0x020a: "VSERIN",
        0x020b: "VSERIN+1",
        0x020c: "VSEROR",
        0x020d: "VSEROR+1",
        0x020e: "VSEROC",
        0x020f: "VSEROC+1",
        0x0210: "VTIMR1",
        0x0211: "VTIMR1+1",
        0x0212: "VTIMR2",
        0x0213: "VTIMR2+1",
        0x0214: "VTIMR4",
        0x0215: "VTIMR4+1",
        0x0216: "VIMIRQ",
        0x0217: "VIMIRQ+1",
        0x0218: "CDTMV1",
        0x0219: "CDTMV1+1",
        0x021a: "CDTMV2",
        0x021b: "CDTMV2+1",
        0x021c: "CDTMV3",
        0x021d: "CDTMV3+1",
        0x021e: "CDTMV4",
        0x021f: "CDTMV4+1",
        0x0220: "CDTMV5",
        0x0221: "CDTMV5+1",
        0x0222: "VVBLKI",
        0x0223: "VVBLKI+1",
        0x0224: "VVBLKD",
        0x0225: "VVBLKD+1",
        0x0226: "CDTMA1",
        0x0227: "CDTMA1+1",
        0x0228: "CDTMA2",
        0x0229: "CDTMA2+1",
        0x022a: "CDTMF3",
        0x022b: "SRTIMR",
        0x022c: "CDTMF4",
        0x022d: "INTEMP",
        0x022e: "CDTMF5",
        0x022f: "SDMCTL",
        0x0230: "SDLSTL",
        0x0231: "SDLSTH",
        0x0232: "SSKCTL",
        0x0233: "LCOUNT",
        0x0234: "LPENH",
        0x0235: "LPENV",
        0x0236: "BRKKY",
        0x0237: "BRKKY+1",
        0x0238: "VPIRQ",
        0x0239: "VPIRQ+1",
        0x023a: "CDEVIC",
        0x023b: "CCOMND",
        0x023c: "CAUX1",
        0x023d: "CAUX2",
        0x023e: "TEMP",
        0x023f: "ERRFLG",
        0x0240: "DFLAGS",
        0x0241: "DBSECT",
        0x0242: "BOOTAD",
        0x0243: "BOOTAD+1",
        0x0244: "COLDST",
        0x0245: "RECLEN",
        0x0246: "DSKTIM",
        0x0247: "PDVMSK",
        0x0248: "SHPDVS",
        0x0249: "PDIMSK",
        0x024a: "RELADR",
        0x024b: "RELADR+1",
        0x024c: "PPTMPA",
        0x024d: "PPTMPX",
        0x026b: "CHSALT",
        0x026c: "VSFLAG",
        0x026d: "KEYDIS",
        0x026e: "FINE",
        0x026f: "GPRIOR",
        0x0270: "PADDL0",
        0x0271: "PADDL1",
        0x0272: "PADDL2",
        0x0273: "PADDL3",
        0x0274: "PADDL4",
        0x0275: "PADDL5",
        0x0276: "PADDL6",
        0x0277: "PADDL7",
        0x0278: "STICK0",
        0x0279: "STICK1",
        0x027a: "STICK2",
        0x027b: "STICK3",
        0x027c: "PTRIG0",
        0x027d: "PTRIG1",
        0x027e: "PTRIG2",
        0x027f: "PTRIG3",
        0x0280: "PTRIG4",
        0x0281: "PTRIG5",
        0x0282: "PTRIG6",
        0x0283: "PTRIG7",
        0x0284: "STRIG0",
        0x0285: "STRIG1",
        0x0286: "STRIG2",
        0x0287: "STRIG3",
        0x0288: "HIBYTE",
        0x0289: "WMODE",
        0x028a: "BLIM",
        0x028b: "IMASK",
        0x028c: "JVECK",
        0x028d: "JVECK+1",
        0x028e: "NEWADR",
        0x028f: "NEWADR+1",
        0x0290: "TXTROW",
        0x0291: "TXTCOL",
        0x0292: "TXTCOL+1",
        0x0293: "TINDEX",
        0x0294: "TXTMSC",
        0x0295: "TXTMSC+1",
        0x0296: "TXTOLD",
        0x0297: "TXTOLD+1",
        0x0298: "TXTOLD+2",
        0x0299: "TXTOLD+3",
        0x029a: "TXTOLD+4",
        0x029b: "TXTOLD+5",
        0x029c: "CRETRY",
        0x029d: "HOLD3",
        0x029e: "SUBTMP",
        0x029f: "HOLD2",
        0x02a0: "DMASK",
        0x02a1: "TMPLBT",
        0x02a2: "ESCFLG",
        0x02a3: "TABMAP",
        0x02a4: "TABMAP+1",
        0x02a5: "TABMAP+2",
        0x02a6: "TABMAP+3",
        0x02a7: "TABMAP+4",
        0x02a8: "TABMAP+5",
        0x02a9: "TABMAP+6",
        0x02aa: "TABMAP+7",
        0x02ab: "TABMAP+8",
        0x02ac: "TABMAP+9",
        0x02ad: "TABMAP+A",
        0x02ae: "TABMAP+B",
        0x02af: "TABMAP+C",
        0x02b0: "TABMAP+D",
        0x02b1: "TABMAP+E",
        0x02b2: "LOGMAP",
        0x02b3: "LOGMAP+1",
        0x02b4: "LOGMAP+2",
        0x02b5: "LOGMAP+3",
        0x02b6: "INVFLG",
        0x02b7: "FILFLG",
        0x02b8: "TMPROW",
        0x02b9: "TMPCOL",
        0x02ba: "TMPCOL+1",
        0x02bb: "SCRFLG",
        0x02bc: "HOLD4",
        0x02bd: "DRETRY",
        0x02be: "SHFLOK",
        0x02bf: "BOTSCR",
        0x02c0: "PCOLR0",
        0x02c1: "PCOLR1",
        0x02c2: "PCOLR2",
        0x02c3: "PCOLR3",
        0x02c4: "COLOR0",
        0x02c5: "COLOR1",
        0x02c6: "COLOR2",
        0x02c7: "COLOR3",
        0x02c8: "COLOR4",
        0x02c9: "RUNADR",
        0x02ca: "RUNADR+1",
        0x02cb: "HIUSED",
        0x02cc: "HIUSED+1",
        0x02cd: "ZHIUSE",
        0x02ce: "ZHIUSE+1",
        0x02cf: "GBYTEA",
        0x02d0: "GBYTEA+1",
        0x02d1: "LOADAD",
        0x02d2: "LOADAD+1",
        0x02d3: "ZLOADA",
        0x02d4: "ZLOADA+1",
        0x02d5: "DSCTLN",
        0x02d6: "DSCTLN+1",
        0x02d7: "ACMISR",
        0x02d8: "ACMISR+1",
        0x02d9: "KRPDEL",
        0x02da: "KEYREP",
        0x02db: "NOCLIK",
        0x02dc: "HELPFG",
        0x02dd: "DMASAV",
        0x02de: "PBPNT",
        0x02df: "PBUFSZ",
        0x02e0: "RUNAD",
        0x02e1: "RUNAD+1",
        0x02e2: "INITAD",
        0x02e3: "INITAD+1",
        0x02e4: "RAMSIZ",
        0x02e5: "MEMTOP",
        0x02e6: "MEMTOP+1",
        0x02e7: "MEMLO",
        0x02e8: "MEMLO+1",
        0x02e9: "HNDLOD",
        0x02ea: "DVSTAT",
        0x02eb: "DVSTAT+1",
        0x02ec: "DVSTAT+2",
        0x02ed: "DVSTAT+3",
        0x02ee: "CBAUDL",
        0x02ef: "CBAUDH",
        0x02f0: "CRSINH",
        0x02f1: "KEYDEL",
        0x02f2: "CH1",
        0x02f3: "CHACT",
        0x02f4: "CHBAS",
        0x02f5: "NEWROW",
        0x02f6: "NEWCOL",
        0x02f7: "NEWCOL+1",
        0x02f8: "ROWINC",
        0x02f9: "COLINC",
        0x02fa: "CHAR",
        0x02fb: "ATACHR",
        0x02fc: "CH",
        0x02fd: "FILDAT",
        0x02fe: "DSPFLG",
        0x02ff: "SSFLAG",
        0x0300: "DDEVIC",
        0x0301: "DUNIT",
        0x0302: "DCOMND",
        0x0303: "DSTATS",
        0x0304: "DBUFLO",
        0x0305: "DBUFHI",
        0x0306: "DTIMLO",
        0x0307: "DUNUSE",
        0x0308: "DBYTLO",
        0x0309: "DBYTHI",
        0x030a: "DAUX1",
        0x030b: "DAUX2",
        0x030c: "TIMER1",
        0x030d: "TIMER1+1",
        0x030e: "ADDCOR",
        0x030f: "CASFLG",
        0x0310: "TIMER2",
        0x0311: "TIMER2+1",
        0x0312: "TEMP1",
        0x0313: "TEMP2",
        0x0314: "PTIMOT",
        0x0315: "TEMP3",
        0x0316: "SAVIO",
        0x0317: "TIMFLG",
        0x0318: "STACKP",
        0x0319: "TSTAT",
        0x031a: "HATABS",
        0x033d: "PUPBT1",
        0x033e: "PUPBT2",
        0x033f: "PUPBT3",
        0x0340: "B0-ICHID",
        0x0341: "B0-ICDNO",
        0x0342: "B0-ICCOM",
        0x0343: "B0-ICSTA",
        0x0344: "B0-ICBAL",
        0x0345: "B0-ICBAH",
        0x0346: "B0-ICPTL",
        0x0347: "B0-ICPTH",
        0x0348: "B0-ICBLL",
        0x0349: "B0-ICBLH",
        0x034a: "B0-ICAX1",
        0x034b: "B0-ICAX2",
        0x034c: "B0-ICAX3",
        0x034d: "B0-ICAX4",
        0x034e: "B0-ICAX5",
        0x034f: "B0-ICAX6",
        0x0350: "B1-ICHID",
        0x0351: "B1-ICDNO",
        0x0352: "B1-ICCOM",
        0x0353: "B1-ICSTA",
        0x0354: "B1-ICBAL",
        0x0355: "B1-ICBAH",
        0x0356: "B1-ICPTL",
        0x0357: "B1-ICPTH",
        0x0358: "B1-ICBLL",
        0x0359: "B1-ICBLH",
        0x035a: "B1-ICAX1",
        0x035b: "B1-ICAX2",
        0x035c: "B1-ICAX3",
        0x035d: "B1-ICAX4",
        0x035e: "B1-ICAX5",
        0x035f: "B1-ICAX6",
        0x0360: "B2-ICHID",
        0x0361: "B2-ICDNO",
        0x0362: "B2-ICCOM",
        0x0363: "B2-ICSTA",
        0x0364: "B2-ICBAL",
        0x0365: "B2-ICBAH",
        0x0366: "B2-ICPTL",
        0x0367: "B2-ICPTH",
        0x0368: "B2-ICBLL",
        0x0369: "B2-ICBLH",
        0x036a: "B2-ICAX1",
        0x036b: "B2-ICAX2",
        0x036c: "B2-ICAX3",
        0x036d: "B2-ICAX4",
        0x036e: "B2-ICAX5",
        0x036f: "B2-ICAX6",
        0x0370: "B3-ICHID",
        0x0371: "B3-ICDNO",
        0x0372: "B3-ICCOM",
        0x0373: "B3-ICSTA",
        0x0374: "B3-ICBAL",
        0x0375: "B3-ICBAH",
        0x0376: "B3-ICPTL",
        0x0377: "B3-ICPTH",
        0x0378: "B3-ICBLL",
        0x0379: "B3-ICBLH",
        0x037a: "B3-ICAX1",
        0x037b: "B3-ICAX2",
        0x037c: "B3-ICAX3",
        0x037d: "B3-ICAX4",
        0x037e: "B3-ICAX5",
        0x037f: "B3-ICAX6",
        0x0380: "B4-ICHID",
        0x0381: "B4-ICDNO",
        0x0382: "B4-ICCOM",
        0x0383: "B4-ICSTA",
        0x0384: "B4-ICBAL",
        0x0385: "B4-ICBAH",
        0x0386: "B4-ICPTL",
        0x0387: "B4-ICPTH",
        0x0388: "B4-ICBLL",
        0x0389: "B4-ICBLH",
        0x038a: "B4-ICAX1",
        0x038b: "B4-ICAX2",
        0x038c: "B4-ICAX3",
        0x038d: "B4-ICAX4",
        0x038e: "B4-ICAX5",
        0x038f: "B4-ICAX6",
        0x0390: "B5-ICHID",
        0x0391: "B5-ICDNO",
        0x0392: "B5-ICCOM",
        0x0393: "B5-ICSTA",
        0x0394: "B5-ICBAL",
        0x0395: "B5-ICBAH",
        0x0396: "B5-ICPTL",
        0x0397: "B5-ICPTH",
        0x0398: "B5-ICBLL",
        0x0399: "B5-ICBLH",
        0x039a: "B5-ICAX1",
        0x039b: "B5-ICAX2",
        0x039c: "B5-ICAX3",
        0x039d: "B5-ICAX4",
        0x039e: "B5-ICAX5",
        0x039f: "B5-ICAX6",
        0x03a0: "B6-ICHID",
        0x03a1: "B6-ICDNO",
        0x03a2: "B6-ICCOM",
        0x03a3: "B6-ICSTA",
        0x03a4: "B6-ICBAL",
        0x03a5: "B6-ICBAH",
        0x03a6: "B6-ICPTL",
        0x03a7: "B6-ICPTH",
        0x03a8: "B6-ICBLL",
        0x03a9: "B6-ICBLH",
        0x03aa: "B6-ICAX1",
        0x03ab: "B6-ICAX2",
        0x03ac: "B6-ICAX3",
        0x03ad: "B6-ICAX4",
        0x03ae: "B6-ICAX5",
        0x03af: "B6-ICAX6",
        0x03b0: "B7-ICHID",
        0x03b1: "B7-ICDNO",
        0x03b2: "B7-ICCOM",
        0x03b3: "B7-ICSTA",
        0x03b4: "B7-ICBAL",
        0x03b5: "B7-ICBAH",
        0x03b6: "B7-ICPTL",
        0x03b7: "B7-ICPTH",
        0x03b8: "B7-ICBLL",
        0x03b9: "B7-ICBLH",
        0x03ba: "B7-ICAX1",
        0x03bb: "B7-ICAX2",
        0x03bc: "B7-ICAX3",
        0x03bd: "B7-ICAX4",
        0x03be: "B7-ICAX5",
        0x03bf: "B7-ICAX6",
        0x03c0: "PRNBUF",
        0x03e8: "SUPERF",
        0x03e9: "CKEY",
        0x03ea: "CASSBT",
        0x03eb: "CARTCK",
        0x03ec: "DERRF",
        0x03ed: "ACMVAR",
        0x03f8: "BASICF",
        0x03f9: "MINTLK",
        0x03fa: "GINTLK",
        0x03fb: "CHLINK",
        0x03fc: "CHLINK+1",
        0x03fd: "CASBUF",
        0x9ffa: "R-CARTCS",
        0x9ffb: "R-CARTCS+1",
        0x9ffc: "R-CART",
        0x9ffd: "R-CARTFG",
        0x9ffe: "R-CARTAD",
        0x9fff: "R-CARTAD+1",
        0xbffa: "CARTCS",
        0xbffb: "CARTCS+1",
        0xbffc: "CART",
        0xbffd: "CARTFG",
        0xbffe: "CARTAD",
        0xbfff: "CARTAD+1",
        0xd000: "M0PF",
        0xd001: "M1PF",
        0xd002: "M2PF",
        0xd003: "M3PF",
        0xd004: "P0PF",
        0xd005: "P1PF",
        0xd006: "P2PF",
        0xd007: "P3PF",
        0xd008: "M0PL",
        0xd009: "M1PL",
        0xd00a: "M2PL",
        0xd00b: "M3PL",
        0xd00c: "P0PL",
        0xd00d: "P1PL",
        0xd00e: "P2PL",
        0xd00f: "P3PL",
        0xd010: "TRIG0",
        0xd011: "TRIG1",
        0xd012: "TRIG2",
        0xd013: "TRIG3",
        0xd014: "PAL",
        0xd015: "COLPM3",
        0xd016: "COLPF0",
        0xd017: "COLPF1",
        0xd018: "COLPF2",
        0xd019: "COLPF3",
        0xd01a: "COLBK",
        0xd01b: "PRIOR",
        0xd01c: "VDELAY",
        0xd01d: "GRACTL",
        0xd01e: "HITCLR",
        0xd01f: "CONSOL",
        0xd100: "PBI",
        0xd1ff: "PDVI",
        0xd1ff: "PDVS",
        0xd200: "POT0",
        0xd201: "POT1",
        0xd202: "POT2",
        0xd203: "POT3",
        0xd204: "POT4",
        0xd205: "POT5",
        0xd206: "POT6",
        0xd207: "POT7",
        0xd208: "ALLPOT",
        0xd209: "KBCODE",
        0xd20a: "RANDOM",
        0xd20b: "POTGO",
        0xd20d: "SERIN",
        0xd20e: "IRQST",
        0xd20f: "SKSTAT",
        0xd300: "PORTA",
        0xd301: "PORTB",
        0xd302: "PACTL",
        0xd303: "PBCTL",
        0xd400: "DMACTL",
        0xd401: "CHACTL",
        0xd402: "DLISTL",
        0xd403: "DLISTH",
        0xd404: "HSCROL",
        0xd405: "VSCROL",
        0xd407: "PMBASE",
        0xd409: "CHBASE",
        0xd40a: "WSYNC",
        0xd40b: "VCOUNT",
        0xd40c: "PENH",
        0xd40d: "PENV",
        0xd40e: "NMIEN",
        0xd40f: "NMIST",
        0xd40f: "NMIRES",
        0xd600: "PBIRAM",
        0xd800: "AFP",
        0xd803: "PDID1",
        0xd805: "PDIOV",
        0xd806: "PDIOV+1",
        0xd808: "PDIRQV",
        0xd809: "PDIRQV+1",
        0xd80b: "PDID2",
        0xd80d: "PDVV",
        0xd8e6: "FASC",
        0xd9aa: "IFP",
        0xd9d2: "FPI",
        0xda44: "ZFR0",
        0xda46: "ZF1",
        0xda60: "FSUB",
        0xda66: "FADD",
        0xdadb: "FMUL",
        0xdb28: "FDIV",
        0xdd40: "PLYEVL",
        0xdd89: "FLD0R",
        0xdd8d: "FLD0P",
        0xdd98: "FLD1R",
        0xdd9c: "FLD1P",
        0xdda7: "FST0R",
        0xddab: "FST0P",
        0xddb6: "FMOVE",
        0xddc0: "EXP",
        0xddcc: "EXP10",
        0xdecd: "LOG",
        0xded1: "LOG10",
        0xe400: "EDITRV",
        0xe410: "SCRENV",
        0xe420: "KEYBDV",
        0xe430: "PRINTV",
        0xe440: "CASETV",
        0xe450: "DINITV",
        0xe453: "DSKINV",
        0xe456: "CIOV",
        0xe459: "SIOV",
        0xe45c: "SETVBV",
        0xe45f: "SYSVBV",
        0xe462: "XITVBV",
        0xe465: "SIOINV",
        0xe468: "SENDEV",
        0xe46b: "INTINV",
        0xe46e: "CIOINV",
        0xe471: "BLKBDV",
        0xe474: "WARMSV",
        0xe477: "COLDSV",
        0xe47a: "RBLOKV",
        0xe47d: "CSOPIV",
        0xe480: "PUPDIV",
        0xe483: "SLFTSV",
        0xe486: "PHENTV",
        0xe489: "PHUNLV",
        0xe48c: "PHINIV",
        0xe48f: "GPDVV",
    }

    wmemmap = {
        0xd000: "HPOSP0",
        0xd001: "HPOSP1",
        0xd002: "HPOSP2",
        0xd003: "HPOSP3",
        0xd004: "HPOSM0",
        0xd005: "HPOSM1",
        0xd006: "HPOSM2",
        0xd007: "HPOSM3",
        0xd008: "SIZEP0",
        0xd009: "SIZEP1",
        0xd00a: "SIZEP2",
        0xd00b: "SIZEP3",
        0xd00c: "SIZEM",
        0xd00d: "GRAFP0",
        0xd00e: "GRAFP1",
        0xd00f: "GRAFP2",
        0xd010: "GRAFP3",
        0xd011: "GRAFM",
        0xd012: "COLPM0",
        0xd013: "COLPM1",
        0xd014: "COLPM2",
        0xd200: "AUDF1",
        0xd201: "AUDC1",
        0xd202: "AUDF2",
        0xd203: "AUDC2",
        0xd204: "AUDF3",
        0xd205: "AUDC3",
        0xd206: "AUDF4",
        0xd207: "AUDC4",
        0xd208: "AUDCTL",
        0xd209: "STIMER",
        0xd20a: "SKRES",
        0xd20d: "SEROUT",
        0xd20e: "IRQEN",
        0xd20f: "SKCTL",
        }


class Atari5200MemoryMap(Atari800MemoryMap):
    name = "Atari 5200"

    rmemmap = {
        0x0000: "POKMSK",
        0x0001: "RTCLOKH",
        0x0002: "RTCLOKL",
        0x0003: "CRITIC",
        0x0004: "ATRACT",
        0x0005: "SDLSTL",
        0x0006: "SDLSTH",
        0x0007: "SDMCTL",
        0x0008: "PCOLR0",
        0x0009: "PCOLR1",
        0x000a: "PCOLR2",
        0x000b: "PCOLR3",
        0x000c: "COLOR0",
        0x000d: "COLOR1",
        0x000e: "COLOR2",
        0x000f: "COLOR3",
        0x0010: "COLOR4",
        0x0011: "PADDL0",
        0x0012: "PADDL1",
        0x0013: "PADDL2",
        0x0014: "PADDL3",
        0x0015: "PADDL4",
        0x0016: "PADDL5",
        0x0017: "PADDL6",
        0x0018: "PADDL7",
        0x0200: "VIMIRQ",
        0x0201: "VIMIRQ+1",
        0x0202: "VVBLKI",
        0x0203: "VVBLKI+1",
        0x0204: "VVBLKD",
        0x0205: "VVBLKD+1",
        0x0206: "VDSLST",
        0x0207: "VDSLST+1",
        0x0208: "VKEYBD",
        0x0209: "VKEYBD+1",
        0x020a: "VKPD",
        0x020b: "VKPD+1",
        0x020c: "BRKKY",
        0x020d: "BRKKY+1",
        0x020e: "VBREAK",
        0x020f: "VBREAK+1",
        0x0210: "VSERIN",
        0x0211: "VSERIN+1",
        0x0212: "VSEROR",
        0x0213: "VSEROR+1",
        0x0214: "VSEROC",
        0x0215: "VSEROC+1",
        0x0216: "VTIMR1",
        0x0217: "VTIMR1+1",
        0x0218: "VTIMR2",
        0x0219: "VTIMR2+1",
        0x021a: "VTIMR4",
        0x021b: "VTIMR4+1",
        0xc000: "M0PF",
        0xc001: "M1PF",
        0xc002: "M2PF",
        0xc003: "M3PF",
        0xc004: "P0PF",
        0xc005: "P1PF",
        0xc006: "P2PF",
        0xc007: "P3PF",
        0xc008: "M0PL",
        0xc009: "M1PL",
        0xc00a: "M2PL",
        0xc00b: "M3PL",
        0xc00c: "P0PL",
        0xc00d: "P1PL",
        0xc00e: "P2PL",
        0xc00f: "P3PL",
        0xc010: "TRIG0",
        0xc011: "TRIG1",
        0xc012: "TRIG2",
        0xc013: "TRIG3",
        0xc014: "PAL",
        0xc015: "COLPM3",
        0xc016: "COLPF0",
        0xc017: "COLPF1",
        0xc018: "COLPF2",
        0xc019: "COLPF3",
        0xc01a: "COLBK",
        0xc01b: "PRIOR",
        0xc01c: "VDELAY",
        0xc01d: "GRACTL",
        0xc01e: "HITCLR",
        0xc01f: "CONSOL",
        0xd400: "DMACTL",
        0xd401: "CHACTL",
        0xd402: "DLISTL",
        0xd403: "DLISTH",
        0xd404: "HSCROL",
        0xd405: "VSCROL",
        0xd407: "PMBASE",
        0xd409: "CHBASE",
        0xd40a: "WSYNC",
        0xd40b: "VCOUNT",
        0xd40c: "PENH",
        0xd40d: "PENV",
        0xd40e: "NMIEN",
        0xd40f: "NMIST",
        0xd40f: "NMIRES",
        0xe800: "POT0",
        0xe801: "POT1",
        0xe802: "POT2",
        0xe803: "POT3",
        0xe804: "POT4",
        0xe805: "POT5",
        0xe806: "POT6",
        0xe807: "POT7",
        0xe808: "ALLPOT",
        0xe809: "KBCODE",
        0xe80a: "RANDOM",
        0xe80b: "POTGO",
        0xe80d: "SERIN",
        0xe80e: "IRQST",
        0xe80f: "SKSTAT",
        }

    wmemmap = {
        0xc000: "HPOSP0",
        0xc001: "HPOSP1",
        0xc002: "HPOSP2",
        0xc003: "HPOSP3",
        0xc004: "HPOSM0",
        0xc005: "HPOSM1",
        0xc006: "HPOSM2",
        0xc007: "HPOSM3",
        0xc008: "SIZEP0",
        0xc009: "SIZEP1",
        0xc00a: "SIZEP2",
        0xc00b: "SIZEP3",
        0xc00c: "SIZEM",
        0xc00d: "GRAFP0",
        0xc00e: "GRAFP1",
        0xc00f: "GRAFP2",
        0xc010: "GRAFP3",
        0xc011: "GRAFM",
        0xc012: "COLPM0",
        0xc013: "COLPM1",
        0xc014: "COLPM2",
        0xe800: "AUDF1",
        0xe801: "AUDC1",
        0xe802: "AUDF2",
        0xe803: "AUDC2",
        0xe804: "AUDF3",
        0xe805: "AUDC3",
        0xe806: "AUDF4",
        0xe807: "AUDC4",
        0xe808: "AUDCTL",
        0xe809: "STIMER",
        0xe80a: "SKRES",
        0xe80d: "SEROUT",
        0xe80e: "IRQEN",
        0xe80f: "SKCTL",
        }


class Apple2MemoryMap(EmptyMemoryMap):
    name = "Apple ]["

    rmemmap = {
 #Monitor Zero Page locations
        0x0020: "WNDLFT",       # Left column of the Scroll Window
        0x0021: "WNDWDTH",       # Width of the Scroll Window
        0x0022: "WNDTOP",       # Top line of the Scroll Window
        0x0023: "WNDBTM",       # Bottom line of Scroll Window
        0x0024: "CH",       # Displacement from WNDLFT
        0x0025: "CV",
        0x0026: "GBASL",
        0x0027: "GBASH",
        0x0028: "BASL",
        0x0029: "BASH",
        0x002A: "BAS2L",
        0x002B: "BAS2H",
        0x002C: "H2",
        0x002D: "V2",
        0x002F: "LASTIN",
        0x0030: "COLOR",
        0x0031: "MODE",
        0x0032: "INVFLG",
        0x0033: "PROMPT",
        0x0034: "YSAV",
        0x0035: "YSAV1",
        0x0036: "CSWL",
        0x0037: "CSWH",
        0x0038: "KSWL",
        0x0039: "KSWH",
        0x003A: "PCL",
        0x003B: "PCH",
        0x003C: "A1L",
        0x003D: "A1H",
        0x003E: "A2L",
        0x003F: "A2H",
        0x0040: "A3L",
        0x0041: "A3H",
        0x0042: "A4L",
        0x0043: "A4H",
        0x0044: "A5L",
        0x0045: "A5H",
        0x0046: "XREG",
        0x0047: "YREG",
        0x0048: "STATUS",
        0x0049: "SPNT",
        0x004E: "RNDL",
        0x004F: "RNDH",
        0x0050: "ACL",
        0x0051: "ACH",
        0x0052: "XTNDL",
        0x0053: "XTNDH",
        0x0054: "AUXL",
        0x0055: "AUXH",
# IO registers
        0xC000: "KEYBOARD",       # keyboard data (latched) (RD-only)
        0xC001: "SET80COL",
        0xC002: "CLRAUXRD",       # read from auxilliary 48K
        0xC003: "SETAUXRD",
        0xC004: "CLRAUXWR",       # write to auxilliary 48K
        0xC005: "SETAUXWR",
        0xC006: "CLRCXROM",       # use external slot ROM
        0xC007: "SETCXROM",
        0xC008: "CLRAUXZP",       # use auxilliary ZP, stack, & LC
        0xC009: "SETAUXZP",
        0xC00A: "CLRC3ROM",       # use external slot C3 ROM
        0xC00B: "SETC3ROM",
        0xC00C: "CLR80VID",       # use 80-column display mode
        0xC00D: "SET80VID",
        0xC00E: "CLRALTCH",       # use alternate character set ROM
        0xC00F: "SETALTCH",
        0xC010: "STROBE",       # strobe (unlatch) keyboard data
        0xC011: "RDLCBNK2",       # reading from LC bank $Dx 2
        0xC012: "RDLCRAM",       # reading from LC RAM
        0xC013: "RDRAMRD",       # reading from auxilliary 48K
        0xC014: "RDRAMWR",       # writing to auxilliary 48K
        0xC015: "RDCXROM",       # using external slot ROM
        0xC016: "RDAUXZP",       # using auxilliary ZP, stack, & LC
        0xC017: "RDC3ROM",       # using external slot C3 ROM
        0xC018: "RD80COL",       # using 80-column memory mapping
        0xC019: "RDVBLBAR",       # not VBL (VBL signal low)
        0xC01A: "RDTEXT",       # using text mode
        0xC01B: "RDMIXED",       # using mixed mode
        0xC01C: "RDPAGE2",       # using text/graphics page2
        0xC01D: "RDHIRES",       # using Hi-res graphics mode
        0xC01E: "RDALTCH",       # using alternate character set ROM
        0xC01F: "RD80VID",       # using 80-column display mode
        0xC030: "SPEAKER",       # toggle speaker diaphragm
        0xC050: "CLRTEXT",       # enable text-only mode
        0xC051: "SETTEXT",
        0xC052: "CLRMIXED",       # enable graphics/text mixed mode
        0xC053: "SETMIXED",
        0xC054: "TXTPAGE1",       # select page1/2 (or page1/1x)
        0xC055: "TXTPAGE2",
        0xC056: "CLRHIRES",       # enable Hi-res graphics
        0xC057: "SETHIRES",
        0xC058: "SETAN0",       # 4-bit annunciator inputs
        0xC059: "CLRAN0",
        0xC05A: "SETAN1",
        0xC05B: "CLRAN1",
        0xC05C: "SETAN2",
        0xC05D: "CLRAN2",
        0xC05E: "SETAN3",
        0xC05F: "CLRAN3",
        0xC060: "CASSETTE",			# Cassette input
        0xC061: "OPNAPPLE",       # open apple (command) key data
        0xC062: "CLSAPPLE",       # closed apple (option) key data
        0xC070: "PDLTRIG",       # trigger paddles
        0xC081: "ROMIN",       # RD ROM, WR-enable LC RAM
        0xC083: "LCBANK2",       # RD LC RAM bank2, WR-enable LC RAM
        0xC08B: "LCBANK1",       # RD LC RAM bank1, WR-enable LC RAM
        0xCFFF: "CLRC8ROM",       # switch out slot C8 ROM
#Keyboard-related ROM routines, from Monitors Peeled
        0xFD0C: "RDKEY",	# Set screen to blink at cursor saving original character in A-reg. from (BASL),Y
        0xFD18: "RDKEY",	# Jump Indirect (KSWL) to KEYIN
        0xFD1B: "KEYIN",	# Increment random number at RNDL,H while polling keyboard register.
        0xFD26: "KEYIN",	# Store A-reg to (BASL),Y (clear blink set by RDKEY routine).
        0xFD28: "KEYIN",	# Load A-reg from Keyboard register
        0xFD2F: "ESC",	# Call RDKEY for Escape key service
        0xFD32: "ESC",	# Call ESC1 with char in A-reg to do indicated function.
        0xFD35: "RDCHAR",	# Call RDKEY to get next char into A. Compare to $93. =, br to ESC to call for next char and do ESC
        0xFC2C: "ESC1",	# Using character in A-reg, br to FC2C 64556 -980 ESC1 routine for Escape key service.
        0xFD3D: "NOTCR",	#Echo keyboard input thru COUT to screen, from IN,X , with INVFLG temporarily set to $FF.
        0xFD4D: "NOTCR",	#Pickup char from IN,X; if $88 goto BCKSPC; if $98 goto CANCEL; if X-reg (input index) greater than $F7 fall into FD5C.; Otherwise to NOTCR1, bypass Bell
        0xFD5C: "NOTCR",	#Sound bell if X indicates 248+ input characters.
        0xFD5F: "NOTCR1",	#Increment X ; If X not zero goto NXTCHAR; If x=o fall into CANCEL
        0xFD62: "CANCEL",	#Load $DC (backslash) into A-reg to indicate cancelled input.
        0xFD64: "CANCEL",	#Call COUT to print A-reg then fall into GETLNZ
        0xFD67: "GETLNZ",	#Print Carriage Return thru COUT
        0xFD6A: "GETLN",	#Load PROMPT into A-reg
        0xFD6C: "GETLN",	#Call COUT to print A-reg
        0xFD6F: "GETLN",	#Load X-reg with $01 for passage thru backspace operation.
        0xFD71: "BCKSPC",	#If x=o goto GETLNZ to start over. else decrement X, fall into NXTCHAR
        0xFD75: "NXTCHAR",	#Call RDCHAR to get next character If character gotten is $95 (ctrlU cursor right arrow) pick up screen character from (BASL), Y to replace it.
        0xFD84: "ADDINP",	#store A-reg to input area at IN,X Compare to return.
#Cassette-related ROM routines, from Monitors Peeled
        0xFECD: "WRITE ",	#
        0xFEFD: "READ ",	#
        0xFCC9: "HEADR ",	#
        0xFCFA: "RD2BIT",	#
        0xFCFD: "RDBIT ",	#
        0xFCEC: "RDBYTE",	#
        0xFCD6: "WRBIT ",	#
        0xFEED: "WRBYTE",	#
#programming aids routines, from Monitors Peeled
        0xFDED: "COUT",	#Write byte in A to screen at CV,CH
        0xFD8E: "CROUT",	#Print Carriage Return thru COUT
        0xF948: "PRBLNK ",	#Print three blanks thru COUT
        0xF94A: "PRBL2",	#Print eX) blanks thru COUT
        0xF94C: "PRBL3",	#Print character in A followed by (X )-1 blanks
        0xFF3A: "BELL",	#Print BELL code thru COUT
        0xFF2D: "PRERR",	#Print "ERR" and BELL thru COUT
        0xFDE3: "PRHEX",	#Print low nibble of A as hex char
        0xFDDA: "PRBYTE",	#Print A-reg as 2 hex nibbles
        0xF940: "PRNTYX",	#Print hex of Y,X regs
        0xF941: "PRNTAX",	#Print hex of A,X regs
        0xF944: "PRNTX",	#Print hex of X reg
        0xFD96: "PRYX2",	#Print CR, then hex of Y,X regs, then minus sign or dash
        0xFD99: "PRHEX",	#Print hex of Y,X regs, then dash
        0xFD92: "PRA1",	#Print CR, hex of A1H,A1L, and dash
        0xFDA3: "XAM8",	#Print memory as hex with preceeding address from mmmm to mmm7 where mmmm is contents of A1L,H on entry.
        0xFDB3: "XAM",	#Print memory as hex from (A1L,H) to (A2L,H) inclusive.
        0xFF4A: "SAVE",	#Save A,X,Y,P,S regs at $45-49
        0xFAD7: "REGDSP",	#Display registers with names from  $45-49 as SAVEd, with preceeding carriage return.
        0xFADA: "RGDSP1",	#Display regs as above without CR
        0xFF3F: "RESTORE",	#Restore regs A,X,Y,P not S from $45
        0xFA43: "STEP",	#Execute one instruction at (PCL,H)
        0xFE2C: "MOVE",	#Move memory contents to (A4L,H) from (A1L,H) thru (A2L,H)
        0xFE36: "VFY",	#Compare memory contents (A4L,H) to (A1L,H) thru (A2L,H), differences are displayed.
        0xFCB4: "NXTA4",	#Increment A4L,H ($42,43) and
        0xFCBA: "NXTA1",	#Inc A1L,H (3C,D), set carry if A2L,H not less than A1L,H
# Output Subroutines, from Assembly Lines
        0xFDED: "COUT",	#Output a character
        0xFDF0: "COUT1",	#Output to screen
        0xFE80: "SETINV",	#Set Inverse mode
        0xFE84: "SETNORM",	#Set Normal Mode
        0xFD8E: "CROUT",	# Generate a <RETURN>
        0xFD8B: "CROUT1",	# <RETURN> with clear
        0xFDDA: "PRBYTE",	# Print a hexadecimal byte
        0xFDE3: "PRHEX",	# Print a hexadecimal digit
        0xF941: "PRNTAX",	# Print A and X in hexadecimal
        0xF948: "PRBLNK",	#Print 3 spaces
        0xF94A: "PRBL2",	#Print many spaces
        0xFF3A: "BELL",	#Output a 'bell' character
        0xFBDD: "BELL1",	# Bep the Apple's speaker
# Input Subroutines, from Assembly Lines
        0xFD0C: "RDKEY",	#Get an input character
        0xFD35: "RDCHAR",	#Get an input character or escape code
        0xFD1B: "KEYIN",	#Read the Apple's keyboard
        0xFD6A: "GETLN",	#Get an input line with prompt
        0xFD67: "GETLNZ",	#Get an input line
        0xFD6F: "GETLN1",	#Get an input line, no prompt
#Low-Res Graphics Subroutines, from Assembly Lines
        0xF864: "SETCOL",	#Set low-res graphics color
        0xF85F: "NEXTCOL",	#Increment colorby 3
        0xF800: "PLOT",		#Plot a block on the Low-Res Screen
        0xF819: "HLINE",	#Draw a horizontal line of blocks
        0xF828: "VLINE",	#Draw a vertical line of blocks
        0xF832: "CLRSCR",	#Clear the entire low-res screen
        0xF836: "CLRTOP",	#Clear the top ofthe low-res Screen
        0xF871: "SCRN",	#Read the low-res screen
# Hi-Res Graphics Subroutines, from Assembly Lines
        0xF3E2: "HGR ",	#Hi-res page 1
        0xF3D8: "HGR2",	#Hi-res page 2
        0xF3F2: "HCLR",	#Clear to black
        0xF3F6: "BKGND",	#Clear to color
        0xF6F0: "HCOLOR",	#Set color
        0xF411: "HPOSN",	#Position the cursor
        0xF457: "HPLOT",	#Plot at cursor
        0xF5CB: "HFIND",	#Return the cursor position
        0xF53A: "HLIN",	#Draw a line
        0xF730: "SHNUM",	#Load shape number
        0xF601: "DRAW",	#Draw a shape
        0xF65D: "XDRAW",	#Erase a shape (draw XOR)
# Floating Point Accumulator routines, from Assembly Lines
        0xEBAF: "ABS",	#Absolute value
        0xEC23: "INT",	#INT function
        0xEFAE: "RND",	#Random number
        0xEB82: "SIGN",	#Sign of FAC (in Accumulator)
        0xEB90: "SGN",	#Sign of FAC (in FAC)
        0xEE8D: "SQR",	#Square root
        0xEF09: "EXP",	#Exponentiation
        0xE941: "LOG",	#Logarithm base e
        0xEE97: "FPWRT",	#Raise ARG to the FAC power (base e)
        0xEBB2: "FCOMP",	#Compare FAC to memory
        0xEED0: "NEGOP",	#Multiply by -1
        0xE7A0: "FADDH",	#Add 0.5
        0xEA55: "DIV10",	#Divide by 10
        0xEA39: "MUL10",	#Multiply by 10
# Trig functions, from Assembly Lines
        0xEFEA: "COS",	#the cosine function of FAC.
        0xEFFA: "SIN",	#the sine function of FAC.
        0xEFF1: "TAN",	#the tangent function of FAC.
        0xF09E: "ATN",	#the arctangent of FAC.
        0xED34: "FOUT",	#Create a string at the start of the stack
# Other Subroutines, from Assembly Lines
        0xFCA8: "WAIT",	#Delay
        0xFB1E: "PREAD",	#Read a game controller
        0xFF2D: "PRERR",	#Print 'ERR'
        0xFF4A: "IOSAVE",	#Save all registers
        0xFF3F: "IOREST"	#Restore all registers
    }

    wmemmap = {
        0xC000: "CLR80COL"       # use 80-column memory mapping (WR-only)
    }


class KIM1MemoryMap(EmptyMemoryMap):
    name = "KIM-1"

    rmemmap = {
        0x00EF: "PCL"  ,     # Program Counter - Low Order Byte
        0x00F0: "PGH"  ,     # Program Counter - High Order Byte
        0x00F1: "P"    ,   # Status Register
        0x00F2: "SF"   ,    # Stack Pointer
        0x00F3: "A"    ,   # Accumulator
        0x00F4: "Y"    ,   # Y-Index Register
        0x00F5: "X"    ,   # X-Index Register
        0x1700: "PAD"  ,     # 6530-003 A Data Register
        0x1701: "PADD" ,      # 6530-003 A Data Direction Register
        0x1702: "PBD"  ,     # 6530-003 B Data Register
        0x1703: "PBDD" ,      # 6530-003 B Data Direction Register
        0x1704: "TIMER",       # 	 6530-003 Interval Timer
        0x170F: "TIMER2",       #
        0x17F5: "SAL"  ,     # Starting Address - Low Order Byte
        0x17F6: "SAH"  ,     # Starting Address - High Order Byte
        0x17F7: "EAL"  ,     # Ending Address - Low Order Byte
        0x17F8: "EAH"  ,     # Ending Address - High Order Byte
        0x17F9: "ID"   ,    # File Identification Number
        0x17FA: "NMIL" ,      # NMI Vector - Low Order Byte
        0x17FB: "NMIH" ,      # NMI Vector - High Order Byte
        0x17FC: "RSTL" ,      # RST Vector - Low Order Byte
        0x17FD: "RSTH" ,      # RST Vector - High Order Byte
        0x17FE: "IRQL" ,      # IRQ Vector - Low Order Byte
        0x17FF: "IRQH" ,      # IRQ Vector - High Order Byte
        0x1800: "DUMPT",       #	Start Address - Audio Tape Dump
        0x1873: "LOADT",       #Start Address - Audio Tape Load
        0x1C00: "NMI"  ,     #Start Address for NMI using KIM "Save Nachine" Routine (Load in 17FA & 17FB)
        0x17F7: "EAL"  ,     #Ending Address - Low Order Byte
        0x17F8: "EAH"       #Ending Address - High Order Byte
	}

    wmemmap = {
    }
