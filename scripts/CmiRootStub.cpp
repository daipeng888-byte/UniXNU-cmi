// SPDX-License-Identifier: BSD-2-Clause-Patent
// Refusal-only owner-root stub for the cmi (SM8250) UFS bring-up link.
//
// build-arm-driver.py compiles ShengUfs with -DNATIVE_VERIFIED_BLOCK=1, so its
// verified-block paths reference owner-root symbols that only
// libVerifiedRootProbe.a defines. That archive needs an owner-signed policy
// bundle plus a full audit of the real OS image, which this build does not have.
// This stub satisfies the link with ZERO policies and a crypto bridge that
// always refuses, so nothing can be authenticated through it. It exists only so
// the UFS controller probe can run and report what the hardware actually does.
//
// Do NOT extend this into a trust root or let it return success.
#include <stddef.h>
#include <stdint.h>

#include "VerifiedBlockPolicy.h"
#include "verified_root.h"

extern "C" {

const NativeVerifiedBlockPolicy verified_root_policies[1] = {{nullptr, 0}};
const uint64_t verified_root_policy_count = 0;

extern const uint8_t verified_root_key[VR_KEY_BYTES] = {0};

static int refuse_sha256(const void *, size_t, uint8_t[32])
{
  return -1;
}

static int refuse_rsa3072_sha256(const uint8_t[VR_KEY_BYTES], const uint8_t[32],
                                 const uint8_t[VR_SIGNATURE_BYTES])
{
  return -1;
}

extern const struct vr_crypto vr_xnu_crypto = {refuse_sha256, refuse_rsa3072_sha256};

int vr_open(const uint8_t *, size_t, const uint8_t[VR_KEY_BYTES], uint64_t,
            const struct vr_crypto *, struct vr_view *)
{
  return VR_SIGNATURE;
}

int vr_verify_block(const struct vr_view *, uint64_t, const void *, size_t,
                    const struct vr_crypto *)
{
  return VR_BLOCK;
}

}  // extern "C"

// NativeUfs.cpp declares this weak, but the reference sits inside a template
// instantiation where the attribute is dropped, so the link still needs a
// definition. cmi has no boot-progress injection; weak so a real library wins.
extern "C" __attribute__((weak)) void boot_progress_poll(void)
{
}
