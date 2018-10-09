# This is the bare beginnings of a regression test suite, it needs work. For
# one thing, we need `known good' binaries to compare with (as it is, we're
# not checking the actual output of atasm at all, just the return value..)

all: test

clean:
	rm -f *.bin *.65o

test:
	@echo
	@echo "Test 1: raw output mode"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r testraw.m65 && echo " -- 1 OK"
	@echo
	@echo "Test 2: bad -o option"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -o testraw.m65 || echo " -- 2 OK"
	@echo
	@echo "Test 3: correct -o option"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -otestraw.bin testraw.m65 && echo " -- 3 OK"
	@echo
	@echo "Test 4: missing -u option"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -otestu.bin testu.m65 || echo " -- 4 OK"
	@echo
	@echo "Test 5: correct -u option"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -u -otestu.bin testu.m65 && echo " -- 5 OK"
	@echo
	@echo "Test 6: missing -u option, but .OPT ILL in code"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -otestill.bin testill.m65 && echo " -- 6 OK"
	@echo
	@echo "Test 7: correct -u option, *and* .OPT ILL in code"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -otestill.bin testill.m65 && echo " -- 7 OK"
	@echo
	@echo "Test 8: missing -dfoo=1 on the command line"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -otestdfoo.bin testdfoo.m65 || echo " -- 8 OK"
	@echo
	@echo "Test 9: correct -dfoo=1 on the command line"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -dFOO=1 -otestdfoo.bin testdfoo.m65 && echo " -- 9 OK"
	@echo
	@echo "Test 10: correct -dfoo=1+1 on the command line"
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -dFOO=1+1 -otestdfoo.bin testdfoo.m65 && echo " -- 10 OK"
	@echo
	@echo "Test 11: bad .pseudoop in source code."
	@echo "--------"
	cd ../tests && ../src/atasm -v -r -otestunkn.bin testunkn.m65 || echo " -- 11 OK"

