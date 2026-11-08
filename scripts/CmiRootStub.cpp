// SPDX-License-Identifier: BSD-2-Clause-Patent
// cmi attempt-5: the UFS driver is compiled WITHOUT NATIVE_VERIFIED_BLOCK, so
// no vr_* / policy symbols are referenced. This stub keeps only the two
// symbols the rest of the kernel still needs at link time.
extern "C" __attribute__((weak)) void boot_progress_poll(void)
{
}

// payload.py::check_native_root requires _sheng_pmgr_run when
// native-ufs-root=1 and sheng-pmgr=2 are set. XNU_SHENG_PMGR is off here,
// so bsd_init.c never calls it; this no-op only satisfies that check.
// It is NOT a real PMGR -- AMFI may still panic with "No PMGR" on the handset.
extern "C" void sheng_pmgr_run(void)
{
}
