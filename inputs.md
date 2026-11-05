# cmi 硬件输入记录

对应[移植设备 · 第 1 步](https://unixnu.com/zh/porting/steps)的"结果"：硬件清单和缺失输入列表。
所有值来自目标设备实测（TWRP root shell，只读），**不含推测**。

- 采集时间：2026-11-05
- 设备：Xiaomi Mi 10 Pro，`ro.product.device=cmi`，`ro.product.model=Mi 10 Pro`，`ro.boot.hardware=qcom`
- 状态：TWRP recovery，`adb` 序列 `b7c8640e`
- 主机：`D:\platform-tools-latest-windows\platform-tools`

---

## 1. 身份

| 项 | 值 | 来源 |
| --- | --- | --- |
| 代号 | `cmi` | `getprop ro.product.device` |
| 型号串 | `Mi 10 Pro` | `getprop ro.product.model` |
| DT model | `Qualcomm Technologies, Inc. xiaomi cmi` | `/proc/device-tree/model` |
| `qcom,msm-id` | `0x00000164`（SoC 修订 `0x00020001`） | `/proc/device-tree/qcom,msm-id` |
| `qcom,board-id` | `0x24` / `0x0` | `/proc/device-tree/qcom,board-id` |
| SoC | SM8250（与 umi / cas / lmipro 同代） | msm-id 0x164 |

```sh
adb shell 'od -An -tx1 /proc/device-tree/qcom,msm-id'   # 00 00 01 64 00 02 00 01
adb shell 'od -An -tx1 /proc/device-tree/qcom,board-id' # 00 00 00 24 00 00 00 00
```

## 2. 存储几何

| 项 | 值 |
| --- | --- |
| 逻辑块大小 | `4096`（`lba_bytes = 4096`） |
| 设备容量 | `sda` = 254.7 GB（`497401856` × 512B 扇区） |
| `userdata` first_lba | `0x2C0000` |
| `userdata` last_lba | `0x3B4B7FA` |
| `userdata` 容量 | 226.18 GiB |

> 与 umi 的 `0x2C0000`–`0x3B51FFA` **不同**，`last_lba` 必须按本机读，不能抄。

GPT 读取方式（TWRP 无 `sgdisk`/`parted`/`fdisk`，用 `dd` + 主机解析）：

```sh
adb shell 'dd if=/dev/block/sda of=/tmp/gpt.bin bs=4096 count=8'
adb pull /tmp/gpt.bin probe/gpt.bin
# 主机：header @4096（"EFI PART"），entry_lba=2，64 项 × 128 B，名字为 UTF-16LE @+56
```

其他相关分区（`by-name` 实测）：`super` 8.5 GiB（动态分区）、`recovery` 0.125 GiB、`cache` 0.375 GiB。
**安装会替换 Android `userdata`**；要保留 Android 需先按[双系统分区](https://unixnu.com/zh/porting/dual-system-partition)准备独立分区。

## 3. DRAM

`/proc/device-tree/memory/reg` 三个 bank（大端 u64 对）：

| # | base | size |
| --- | --- | --- |
| 1 | `0x0000000080000000` | `0x000000003BB00000` |
| 2 | `0x0000000180000000` | `0x0000000100000000` |
| 3 | `0x00000000C0000000` | `0x00000000C0000000` |

**`dram_size` = `0x1FBB00000`**（三 bank 求和，≈7.93 GiB）

> 这是**本机 8 GB SKU** 的值。12 GB 机型会不同（umi 的 12 GB 实测为 `0x2F9900000`）。
> 求和口径与 umi 一致：`0x200000000 - 0x4500000`。

```sh
adb shell 'od -An -tx1 /proc/device-tree/memory/reg'
```

## 4. 保留区（`reserved-memory` 实测节点名）

`adsp_region cdsp_region cdsp_secure_heap cnss_wlan_region cont_splash_region@9c000000
dfps_data_region@9e300000 disp_rdump_region@9c000000 hyp_region linux,cma mailbox_region
mem_dump_region pil_adsp_region pil_camera_region pil_cdsp_region pil_cvp_region
pil_gpu_region pil_ipa_fw_region pil_ipa_gsi_region pil_npu_region pil_slpi_region
pil_spss_region pil_video_region pil_wlan_fw_region qseecom_region qseecom_ta_region
removed_region res_xbl_uefi_log_region sdsp_region secure_display_region smem_region
sp_region user_contig_region xbl_aop_region`

两个与显示交接触有关的：`cont_splash_region@9c000000`、`disp_rdump_region@9c000000`（同一基址，splash 交接）。

逐个节点的 `reg` 尚未采集（`od` 各取一遍即可），DTS 的零 RAM 范围要用。

## 5. 显示与输入（待取）

TWRP 的 `/proc/device-tree` 是 SoC 级基础树，已确认存在：

- `soc/mdss_mdp@ae00000`、`mdss_dsi_ctrl0@ae94000`、`mdss_dsi_phy0@ae94400`、`mdss_dsi_pll@ae94900`
- `soc/i2c@88c000` 等 20 个 Geni I²C、`soc/spi@*` 同址 SPI
- `dsi_panel_pwr_supply*` 一组供电节点

### 触摸：已确认（`st,fts`）

节点 `soc/i2c@a94000/fts@49`（`compatible = "st,fts"`）——**cmi 与 umi 同为 ST FTS 家族**，
此前"可能不是同一颗"的怀疑排除。

| 属性 | 值 |
| --- | --- |
| `reg` | `0x49` |
| `interrupts` | `<0x27 0x2008>`（hwirq 39，flags 边沿） |
| `interrupt-parent` | phandle `0x65`（tlmm） |
| `fts,reset-gpio` | `<&tlmm 0x26 0>` → GPIO 38 |
| `fts,irq-gpio` | `<&tlmm 0x27 0x2008>` → GPIO 39 |
| `fts,x-max` / `fts,y-max` | `0x438` (1080) / `0x924` (2340) |
| `fts,default-fw-name` | `st_fts_j1.ftb` |
| `fts,pwr-reg-name` / `bus-reg-name` | `avdd` / `vdd` |
| `fts,irq-gpio-name` / `reset-gpio-name` | `fts_irq` / `fts_rst` |
| `fts,config-array-size` | `1`（`cfg_0` 为空，固件由 `st_fts_j1.ftb` 提供） |
| `vdd-supply` / `avdd-supply` | phandle `0x38d` / `0x6f1` |
| 其他 | `fts,support-fod`、`fts,cfg_0`、cornerzone/deadzone/edgezone filter、`pinctrl-0/1` |

⚠ 仍需对比 umi 的实机做法：umi 第 80 版的关键是**在 FTS 启动前打开 PM8150B GPIO5 常开电源**，
cmi 的供电 rail 名与 GPIO 未核实，不能直接套用。

### 面板：已确认

从 TWRP 的 `chosen/bootargs` 读到 bootloader 的面板选择（TWRP 有 root，Android 侧读不到）：

```
msm_drm.dsi_display0=qcom,mdss_dsi_j2_p2_1_38_0c_0a_dsc_cmd:
```

| 属性 | 值 |
| --- | --- |
| 节点 | `qcom,mdss_dsi_j2_p2_1_38_0c_0a_dsc_cmd` |
| `qcom,mdss-dsi-panel-name` | `xiaomi 38 0c 0a cmd mode dsc dsi panel` |
| 类型 | `dsi_cmd_mode`（DSC 压缩） |
| 分辨率 / bpp | `0x438`×`0x924` = 1080×2340，24 bpp |
| `mi,panel-id` | `0x4a32` / `0x00380c00` |
| timing@0 | 60 Hz（`0x3c`），clock `0x28a67e80` = 681,489,024 Hz |
| timing@1 | 90 Hz（`0x5a`），同 clock |
| `qcom,platform-reset-gpio` | `<&tlmm 0x0c 0>` → GPIO 12 |
| `qcom,platform-te-gpio` | `<&tlmm 0x42 0>` → GPIO 66 |
| 面板供电 | `vci`=phandle `0x674`、`vddio`=`0x80`、`dvdd`=`0x38e`、`lab`=`0x675`、`ibb`=`0x676` |
| 其他 | `qcom,mdss-dsi-panel-hdr-enabled`、`mi,*` 一组小米私有亮度/FOD/白点属性 |

Android 侧 `dumpsys display` 交叉验证：1080×2340，60/90 Hz 双模式，density 440，
387 dpi，HDR 类型 1/2/3/4，峰值 420 nits，圆角 110，挖孔 90px。

⚠ **未采集**：`qcom,mdss-dsi-display-timings/*` 下的 DCS 初始化命令序列（二进制 blob），
以及 porch/clock 等 porch 参数。这些是点亮面板的必需内容，需要 `dtc` 反编译或原厂 dts。

### 保留区实测（22 个带 reg 的节点）

| 节点 | base | size |
| --- | --- | --- |
| `hyp_region` | `0x80000000` | `0x00600000` |
| `xbl_aop_region` | `0x80600000` | `0x00260000` |
| `reserved-memory`（自身） | `0x80860000` | `0x00020000` |
| `res_xbl_uefi_log_region` | `0x80880000` | `0x00014000` |
| `smem_region` | `0x80900000` | `0x00200000` |
| `removed_region` | `0x80b00000` | `0x05300000` |
| `pil_camera_region` | `0x86200000` | `0x00500000` |
| `pil_wlan_fw_region` | `0x86700000` | `0x00100000` |
| `pil_ipa_fw_region` | `0x86800000` | `0x00010000` |
| `pil_ipa_gsi_region` | `0x86810000` | `0x0000a000` |
| `pil_gpu_region` | `0x8681a000` | `0x00002000` |
| `pil_npu_region` | `0x86900000` | `0x00500000` |
| `pil_video_region` | `0x86e00000` | `0x00500000` |
| `pil_cvp_region` | `0x87300000` | `0x00500000` |
| `pil_cdsp_region` | `0x87800000` | `0x01400000` |
| `pil_slpi_region` | `0x88c00000` | `0x02f00000` |
| `pil_adsp_region` | `0x8bb00000` | `0x02500000` |
| `pil_spss_region` | `0x8e000000` | `0x00100000` |
| `cdsp_secure_heap` | `0x8e100000` | `0x04600000` |
| `cont_splash_region` | `0x9c000000` | `0x02300000` |
| `dfps_data_region` | `0x9e300000` | `0x00100000` |
| `disp_rdump_region` | `0xb0400000` | `0x01000000` |

`no-map` / `reusable` 属性未采集，需按原厂 DTS 核对后写入板级 DTS。

### 原厂 DTS 定位结果（2026-11-05）

`MiCode/Xiaomi_Kernel_OpenSource` 的 `umi-q-oss` 分支（commit `db67ca60`）：

| 路径 | 结果 |
| --- | --- |
| `arch/arm64/boot/dts/vendor/qcom/` | **不存在**（Contents API 404） |
| `arch/arm64/boot/dts/qcom/` | 存在，但只有上游 DT（`kona-mtp.dtsi` 等），**无 cmi/umi 板级 dts** |
| `sm8250-xiaomi-umi.dts`（两种路径） | 404 |

即该分支不包含小米板级 DTS，只有上游 kona 骨架。本机 `git ls-remote` 对该仓库无输出，
`raw.githubusercontent` 对疑似存在的路径返回 30 s 超时，**主机侧网络不可靠**。

下一步（二选一）：

- 在本机 `git clone --depth 1 -b <正确分支> --filter=blob:none --sparse` 后取
  `arch/arm64/boot/dts/vendor/qcom/sm8250-xiaomi-cmi.dts`；
- 或直接解本机 `dtbo` overlay（第 5 节第 2 条），不需要外网。


## 6. 缺失输入清单

| 输入 | 缺什么 | 影响的步骤 |
| --- | --- | --- |
| 触摸控制器 | 型号、I²C 地址、中断/复位 GPIO、供电 rail、固件（待第 5 节） | 输入适配、`[components]`、package |
| panel | DDIC、分辨率/时序、TE/复位脚、供电序列（待第 5 节） | 显示适配、UEFI 显示初始化 |
| `UniXNU-sm8250-common` | **仓库不存在**（SM8250 无共享 SoC 仓） | 格式 2 的 `feeds.toml`、`soc_source`、DTSI |
| `cmiPkg` | `uefi-umi` 无 `cmiPkg`（30+ 个 Xiaomi 包里没有 cmi） | `[firmware] dsc/fd`、点屏 |
| ADT `chip_id` | msm-id 已实测 `0x164`，但生成器要的十进制/十六进制形式待核 | `[payload.adt]` |
| 组件选择 | 需按[组件目录](https://unixnu.com/zh/reference/components)逐项核对硬件范围 | `[components] include`、`kernel.archives` |
| OS profile | `ipados-17.7.11-21H461` 已存在（umi 同款），可直接用 | — |

## 7. 结论

- 身份、存储几何、DRAM、保留区：**已取全，可直接进 `board.toml`**。
- 触摸与 panel：必须从原厂 DTS 取，不能凭 SoC 推断（umi 是 ST FTS，cmi 尚未证实）。
- 格式 2 的硬前提是 `UniXNU-sm8250-common` 先建起来（[SoC 支持步骤](https://unixnu.com/zh/porting/soc-support)第 3 节）；
  否则只能走 umi 那种独立仓（格式 1），无法通过[完成清单](https://unixnu.com/zh/porting/device-repository#completion)。

## 8. 固件侧输入（xbl_5，2026-11-05）

`xbl_5`（`/dev/block/sdb2`，7,340,032 字节）里嵌着 cmi 自己的 `uefiplat.cfg`（offset `0xc893c`），
已存档为 `probe/uefiplat.cmi.cfg`。

| 项 | 值 | 说明 |
| --- | --- | --- |
| `UnusableDDRMemoryStartAddr` / `Size` | `0x80000000` / `0x600000` | 与设备 DT 的 `hyp_region` 一致 |
| UEFI FD | `0x9FC00000` / `0x00300000` | `uefi_fd.base` / `size`，不能抄 umi 的值 |
| UEFI Stack | `0x9FF90000` / `0x00040000` | 即 `PcdCPUCoresStackBase` |
| `DloadCookieAddr` | `0x01FD3000` | — |

同一镜像里还有 10 个固件侧面板时序 XML，其中包含本机这颗面板：

```
<PanelName>J2 38_0C_0A AMOLED</PanelName>
<PanelDescription>J2 38 0C 0A Single DSI Command Mode Panel (1080x2340 24bpp)</PanelDescription>
```

已存档为 `probe/xbl-panel-j2-38_0c_0a.xml`（3068 字符），前 porch：
HFP 64 / HBP 64 / HSW 20，VFP 64 / VBP 64 / VSW 20。

这是 **UEFI/XBL 层的面板时序**（`GopFramebuffer` 依赖的固件初始化），与内核侧的
`qcom,mdss-dsi-*` DCS 序列是两套东西，都已取得。

```sh
adb shell 'dd if=/dev/block/by-name/xbl_5 of=/tmp/xbl5.bin bs=1M'
adb pull /tmp/xbl5.bin probe/xbl5.bin
```

## 9. 结论（更新）

- 固件侧所需的两项硬输入（FD 地址、面板时序）**都已从本机取得**，不再依赖 umi 的相似设备。
- 仍缺：`cmiPkg` 的按键映射（vol_up = tlmm GPIO6、电源 = PON1、音量下 = PON2 已测得，
  但 umiPkg 的 `UmiButtonsDxe` 源码未改）。
