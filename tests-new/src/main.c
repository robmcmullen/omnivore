#include <stdio.h>
#include <string.h>

#ifndef FALSE
#define FALSE  0
#endif
#ifndef TRUE
#define TRUE   1
#endif

typedef void (*callback_ptr)(unsigned char *);

static int have_shared = 0;

unsigned char *shared_memory = NULL;

#define SHMEM_TOTAL_SIZE (256*256)
static unsigned char fake_shared_memory[SHMEM_TOTAL_SIZE];

unsigned char *SHMEM_DebugGetFakeMemory(void) {
    return &fake_shared_memory[0];
}

int SHMEM_Initialise(void)
{
	/* initialize shared memory here */
    if (!have_shared) {
        if (!SHMEM_AcquireMemory())
            return FALSE;
        have_shared = 1;
    }
	return TRUE;
}

/* use memory that's not managed by the C code */
int SHMEM_UseMemory(unsigned char *raw, int len) {
    if (len >= SHMEM_TOTAL_SIZE) {
        shared_memory = raw;
        have_shared = 2;
        return TRUE;
    }
    return FALSE;
}

int SHMEM_AcquireMemory(void)
{
	/* get shared memory */
    memset(fake_shared_memory, 0, SHMEM_TOTAL_SIZE);
    shared_memory = &fake_shared_memory[0];
    return TRUE;
}

unsigned char *SHMEM_GetVideoArray(void) {
    printf("storage=%lx\n", shared_memory);
    printf("fake=%lx\n", &fake_shared_memory);
    return shared_memory;
}

void SHMEM_TestPattern(void) {
	unsigned char *dest = SHMEM_GetVideoArray();
	int i;
	for (i=0; i<SHMEM_TOTAL_SIZE; i++) {
		if (i & 2) *dest = '.';
		else *dest = 'x';
		dest++;
	}
}

void SHMEM_Debug4k(unsigned char *video_mem) {
	int x, y;

	for (y = 0; y < 16; y++) {
		for (x = 0; x < 64; x++) {
			/*printf(" %02x", src[x]);*/
			/* print out text version of screen, assuming graphics 0 memo pad boot screen */
			unsigned char c = video_mem[x];
			putchar(c);
		}
		putchar('\n');
		video_mem += x;
	}
}

int start_shmem(unsigned char *raw, int len, callback_ptr cb)
{
	printf("raw=%lx, len=%d\n", raw, len);
	if (raw) SHMEM_UseMemory(raw, len);

	SHMEM_TestPattern();

	if (cb) {
		unsigned char *fake_shared_memory = SHMEM_DebugGetFakeMemory();
		printf("fake %lx\n", fake_shared_memory);
		SHMEM_Debug4k(fake_shared_memory);
		printf("shared %lx\n", shared_memory);
		SHMEM_Debug4k(shared_memory);
		//memcpy(shared_memory, fake_shared_memory, SHMEM_TOTAL_SIZE);
		printf("callback=%lx\n", cb);
		(*cb)(shared_memory);
	}
}

/*
vim:ts=4:sw=4:
*/
