/*
 * cmi bring-up: kernel boot progress on the inherited framebuffer.
 *
 * The upstream zzz-boot-progress patch calls these hooks from arm_init.c,
 * startup.c, pe_kprintf.c, video_console.c, serial_console.c, sleh.c,
 * kern_exec.c and kern_exit.c, and ships osfmk/kern/boot_progress.h with the
 * prototypes. sheng implements the hooks against its display stack; cmi has no
 * panel driver yet, so this paints one white block per stage straight into the
 * framebuffer the bootloader already left scanning out (0x9C000000, 1080x2340),
 * exactly like the SEC progress marks in the firmware.
 *
 * Fatal paths (panic, abort, breakpoint, critical exit) fill the band below the
 * blocks red, so "how far did it get" and "did it die" are both visible at a
 * glance without a font or a console.
 *
 * SPDX-License-Identifier: MIT
 */
#include <stdint.h>

#define CMI_FB_BASE    0x9C000000ULL
#define CMI_FB_STRIDE  1080U
#define CMI_FB_HEIGHT  2340U

#define BLOCK_SIZE     16U
#define BLOCK_GAP      6U
#define BLOCK_TOP      8U
#define BAND_TOP       40U
#define BAND_HEIGHT    24U
#define BLOCK_LEFT     8U

#define WHITE          0x00FFFFFFU
#define RED            0x00FF3020U

static volatile uint32_t *gFb = (volatile uint32_t *)CMI_FB_BASE;
static unsigned gStride = CMI_FB_STRIDE;
static unsigned gWidth = 1080U;
static unsigned gHeight = CMI_FB_HEIGHT;
static unsigned gBlocks;
static int      gActive;

static void fill_rect(unsigned x, unsigned y, unsigned w, unsigned h, uint32_t colour)
{
	unsigned row, col;

	if (gFb == 0) {
		return;
	}
	if (x >= gWidth || y >= gHeight) {
		return;
	}
	if (x + w > gWidth) {
		w = gWidth - x;
	}
	if (y + h > gHeight) {
		h = gHeight - y;
	}
	for (row = 0; row < h; row++) {
		volatile uint32_t *line = gFb + (uintptr_t)(y + row) * gStride;
		for (col = 0; col < w; col++) {
			line[x + col] = colour;
		}
	}
}

void
boot_progress_init(void)
{
	gActive = 1;
	gBlocks = 0;
	fill_rect(0, BLOCK_TOP, gWidth, BAND_TOP - BLOCK_TOP, 0x00000000U);
}

void
boot_progress_bind(uintptr_t base, unsigned stride, unsigned width, unsigned height, unsigned bpp)
{
	(void)bpp;
	if (base != 0) {
		gFb = (volatile uint32_t *)base;
	}
	if (stride != 0) {
		gStride = stride;
	}
	if (width != 0) {
		gWidth = width;
	}
	if (height != 0) {
		gHeight = height;
	}
}

void
boot_progress_start(void)
{
	gActive = 1;
}

int
boot_progress_active(void)
{
	return gActive;
}

void
boot_progress_stage(const char *name)
{
	unsigned x;

	(void)name;
	if (!gActive || gFb == 0) {
		return;
	}
	x = BLOCK_LEFT + gBlocks * (BLOCK_SIZE + BLOCK_GAP);
	if (x + BLOCK_SIZE > gWidth) {
		return;
	}
	fill_rect(x, BLOCK_TOP, BLOCK_SIZE, BLOCK_SIZE, WHITE);
	gBlocks++;
}

void
boot_progress_process_stage(int pid, const char *stage, const char *name)
{
	(void)pid;
	(void)stage;
	boot_progress_stage(name);
}

void
boot_progress_putc(char c)
{
	(void)c;
}

void
boot_progress_irq(uint64_t a, uint64_t b, uint64_t c)
{
	(void)a;
	(void)b;
	(void)c;
}

void
boot_progress_poll(void)
{
}

void
boot_progress_user_breakpoint(void *frame, unsigned code)
{
	(void)frame;
	(void)code;
	fill_rect(0, BAND_TOP, gWidth, BAND_HEIGHT, RED);
}

void
boot_progress_user_abort(void *frame, unsigned code, uint64_t pc)
{
	(void)frame;
	(void)code;
	(void)pc;
	fill_rect(0, BAND_TOP, gWidth, BAND_HEIGHT, RED);
}

void
boot_progress_critical_exit(int code, char *message, unsigned long arg)
{
	(void)code;
	(void)message;
	(void)arg;
	fill_rect(0, BAND_TOP, gWidth, BAND_HEIGHT, RED);
}

void
boot_progress_exit(int code, const char *name, int pid, unsigned signal, uint64_t pc)
{
	(void)code;
	(void)name;
	(void)pid;
	(void)signal;
	(void)pc;
}
