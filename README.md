# UniXNU-cmi

UniXNU device repository for the Xiaomi Mi 10 Pro (`cmi`, Qualcomm SM8250).

Status: **format 2 configuration and hardware description in place; no build and no
device boot yet.** The porting record ([porting.toml](porting.toml)) is the
authoritative statement of what is measured, what is planned and what is blocked.

## Scope

| Item | Value |
| --- | --- |
| Device | Xiaomi Mi 10 Pro, codename `cmi` |
| SoC | SM8250 (kona), `qcom,msm-id` 0x164, `qcom,board-id` 0x24 |
| DRAM | three banks, sum 0x1fbb00000 (7.93 GiB, this handset is the 8 GB SKU) |
| Panel | `qcom,mdss_dsi_j2_p2_1_38_0c_0a_dsc_cmd`, 1080x2340, 60/90 Hz, DSC cmd |
| Touch | `st,fts` at `i2c@a94000`, address 0x49, reset GPIO 38, irq GPIO 39 |
| OS profile | `ipados-17.7.11-21H461` (shared with UniXNU-sheng and umi) |

## Prerequisites

- A UniXNU checkout next to this repository (`[package] unixnu = "../UniXNU"`).
- The shared SoC repository `UniXNU-sm8250-common`, pinned in [feeds.toml](feeds.toml).
- `dtc` on the host: `./unixnu payload` compiles `device:dts/cmi.dts`.
- Local build inputs (`unixnu.local.toml` in the UniXNU checkout): firmware DTB,
  kernelcache, trust cache, Data seed and a device seed.
- Host tools per [guide/requirements](https://unixnu.com/zh/guide/requirements).

## Build

```sh
./unixnu defconfig cmi_defconfig -D ../UniXNU-cmi
./unixnu fetch      -D ../UniXNU-cmi
./unixnu status --json -D ../UniXNU-cmi
./unixnu tree       -D ../UniXNU-cmi
./unixnu kernel     -D ../UniXNU-cmi
./unixnu build package -D ../UniXNU-cmi
./unixnu firmware   -D ../UniXNU-cmi
./unixnu payload    -D ../UniXNU-cmi
./unixnu bootimg    -D ../UniXNU-cmi
```

Output lives in `out/cmi/ipados-17.7.11-21H461/cmi/`.

## Hardware description

`dts/cmi.dts` includes `sm8250.dtsi` from the SoC repository and declares exactly one
enabled `memory` node (single contiguous range, equal to `payload.dram_size`) plus the
measured reserved-memory regions.

`GopFramebuffer` renders through the firmware GOP handoff, so the display path needs no
device-tree node; panel initialization belongs to the firmware package `cmiPkg`, which
does not exist yet.

## Known blockers

1. `UniXNU-sm8250-common` is not published; `feeds.toml` still holds a placeholder commit.
2. `cmiPkg` does not exist: fork `uefi-umi`'s `Platforms/Xiaomi/umiPkg`.
3. ShengUfs matches `qcom,sm8550-ufshc`; this board reports `qcom,ufshc`.
4. Reserved-memory `no-map` / `reusable` flags are unset (not measured).
5. Installing replaces the 226 GiB Android `userdata` partition.

## Links

- [Porting guide](https://unixnu.com/zh/porting/steps)
- [Device repository reference](https://unixnu.com/zh/porting/device-repository)
- [Device tree](https://unixnu.com/zh/porting/device-tree)
- [Porting record](https://unixnu.com/zh/porting/records)
- Measured inputs: [inputs.md](inputs.md) · current state: [MIGRATION.md](MIGRATION.md)
