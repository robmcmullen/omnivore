cd ..
cproto -I libatari800/include/linux -I libatari800/atari800/src -e libatari800/atari800/src/libatari800/main.c|grep "extern " > libatari800.h