// SPDX-License-Identifier: BSD-2-Clause-Patent
// cmi: weak no-op definitions for board-optional probe hooks.
//
// Mach-O static kernel links reject an undefined weak_import even when the
// caller guards it with `if (&symbol)`. The alioth/sheng board packages carry
// real providers for these (touch, GPU, PCIe, USB debug, UFS DPU/SMMU); cmi
// does not select those components yet. All definitions are weak, so a later
// real provider overrides them without a duplicate-symbol error.
//
// Kept in the same archive as the display backend because that archive is the
// one the kernel link force-loads.

#include <stdint.h>

/* ---- functions ---- */
__attribute__((weak)) int native_hid_input_probe(void) { return 0; }
__attribute__((weak)) void native_gpu_probe(void) { }
__attribute__((weak)) void alioth_pcie_init(void) { }
__attribute__((weak)) void alioth_wifi_start(void) { }
__attribute__((weak)) void alioth_backlight_probe(void) { }
__attribute__((weak)) void alioth_buttons_probe(void) { }
__attribute__((weak)) void boot_diag_ls_reset(void) { }
__attribute__((weak)) void sheng_cpufreq_probe(void) { }
__attribute__((weak)) void armcpu_spi_attach(void) { }
__attribute__((weak)) uintptr_t native_ufs_smmu_base(void) { return 0; }
__attribute__((weak)) int native_ufs_dpu_window_build(uintptr_t base) { (void)base; return 0; }
__attribute__((weak)) int qcom_usb_debug_register_framebuffer(const void *p) { (void)p; return 0; }
__attribute__((weak)) uint64_t qcom_usb_debug_write(const void *p, uint64_t n) { (void)p; (void)n; return 0; }

/* IOSurface getters are absolute bindings in original-bindings.o; do not
 * define them here or the linker would see two different symbol kinds. */

/* ---- scalar telemetry ---- */
__attribute__((weak)) volatile uint32_t native_touch_seq;
__attribute__((weak)) volatile uint32_t native_touch_fail_step;
__attribute__((weak)) volatile int native_touch_stage_result;
__attribute__((weak)) volatile unsigned native_touch_stage_value;
__attribute__((weak)) volatile unsigned native_touch_stage_total;
__attribute__((weak)) volatile unsigned native_touch_crc_expected;
__attribute__((weak)) volatile unsigned native_touch_crc_received;
__attribute__((weak)) volatile unsigned native_touch_hdr0;
__attribute__((weak)) volatile unsigned native_touch_hdr1;
__attribute__((weak)) volatile unsigned native_touch_hdr2;
__attribute__((weak)) volatile unsigned native_touch_hdr3;
__attribute__((weak)) volatile unsigned native_touch_data0;
__attribute__((weak)) volatile unsigned native_touch_data1;
__attribute__((weak)) volatile unsigned native_touch_data2;
__attribute__((weak)) volatile unsigned native_touch_ready;
__attribute__((weak)) volatile unsigned native_touch_ready_ms;
__attribute__((weak)) volatile unsigned native_touch_app_id;
__attribute__((weak)) volatile uint32_t native_adreno_wc_distrusted;
__attribute__((weak)) volatile unsigned native_gpu_gmu_firmware_size;
__attribute__((weak)) volatile unsigned native_gpu_sqe_firmware_size;
__attribute__((weak)) volatile unsigned native_gpu_zap_firmware_size;
__attribute__((weak)) volatile uintptr_t native_gpu_gmu_firmware;
__attribute__((weak)) volatile uintptr_t native_gpu_sqe_firmware;
__attribute__((weak)) volatile uintptr_t native_gpu_zap_firmware;

/* ---- array telemetry ---- */
__attribute__((weak)) volatile uint32_t native_touch_pin_cfg[3];
__attribute__((weak)) volatile uint32_t native_touch_pin_want[3];
__attribute__((weak)) volatile uint32_t native_touch_tlmm_probe[3];
__attribute__((weak)) volatile uint32_t native_touch_app_rc[3];
__attribute__((weak)) volatile char native_touch_stage_name[32];
__attribute__((weak)) volatile uint32_t native_adreno_cache_stats[5];
__attribute__((weak)) volatile uint32_t native_adreno_submit_phase[7];
__attribute__((weak)) volatile uint32_t native_adreno_wc_audit[6];
