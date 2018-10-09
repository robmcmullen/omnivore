# If you want to use the compressed state files (you do), uncomment
# the following lines, specifing the path to the zlib header file
# and the library.
# The zlib library homepage can be found at:
#   http://www.gzip.org/zlib/

# for DOS (adjust paths as appropriate)
#USEZ    = -DZLIB_CAPABLE -I/work/djgpp/src/zlib/
#ZLIB    = -L/work/djgpp/src/zlib -lz
#DOS     = -DDOS

# if you are compiling under UNIX, change the above lines to
# reflect the location of zlib.  I use:
USEZ    = -DZLIB_CAPABLE
ZLIB    = -lz
UNIX    = -DUNIX

# Compiler flags, if you are using egcs, pgcs, or gcc >2.8.1 use:
#CFLAGS  = -g -Wall $(USEZ) $(DOS) $(UNIX) $(ARCH)
CFLAGS  = -Wall $(USEZ) $(DOS) $(UNIX) -O3 -fomit-frame-pointer $(ARCH)

L       =  $(ZLIB)
CC      = gcc
DESTDIR	= /usr/local/bin
MANDIR	= /usr/local/man/man1
DOCDIR	= /usr/local/doc/atasm

.c.o:
	$(CC) $(CFLAGS) -c $<

all:    prog

OBJS    = asm.o symbol.o parser.o setparse.o state.o dimage.o inc_path.o crc32.o atasm_err.o state2.o

asm.o: ops.h directive.h symbol.h inc_path.h atasm_err.h
atasm_err.o: atasm_err.h symbol.h
inc_path.o: symbol.h inc_path.h atasm_err.h
setparse.o: symbol.h
state.o: symbol.h
state2.o: symbol.h
symbol.o: symbol.h inc_path.h atasm_err.h

prog : $(OBJS)
	$(CC) -o atasm $(OBJS) $(L) $(ARCH)

clean:
	rm -f *.rej *.o *~ atasm atasm.1 atasm.exe
	cd ../tests && make clean

test: all
	cd ../tests && make

install: all
	cp atasm $(DESTDIR)
	chown root.root $(DESTDIR)/atasm || true
	chmod 711 $(DESTDIR)/atasm
	mkdir $(DOCDIR) >/dev/null 2>&1 || echo $(DOCDIR) already exists
	cp ../atasm.txt $(DOCDIR)
	chown root.root $(DOCDIR)/atasm.txt || true
	chmod 644 $(DOCDIR)/atasm.txt
	sed -e 's,%%DOCDIR%%,$(DOCDIR),g' < atasm.1.in > atasm.1
	cp atasm.1 $(MANDIR)
	chown root.root $(MANDIR)/atasm.1 || true
	chmod 644 $(MANDIR)/atasm.1
