# cmi 移植现状与下一步

小米 10 Pro（`cmi`，SM8250）。本文替代最早那版"派生 umi、格式 1"的迁移计划——
实际走的是**格式 2**：先建共享 SoC 仓库，再建板级仓库。

## 路线为什么变了

最初计划 fork [reAAAq/UniXNU-umi](https://github.com/reAAAq/UniXNU-umi)（小米 10，同 SM8250）。
读完文档和生成器源码后放弃：

| 依据 | 结论 |
|---|---|
| [设备仓库规范](https://unixnu.com/zh/porting/device-repository) | 新设备从 `examples/device` 复制，格式 2 要 `schema_version = 2`、`[components] include`、`[device_tree]`、`porting.toml` |
| [SoC 支持](https://unixnu.com/zh/porting/soc-support) | 格式 2 的 `soc_source` / `feeds.toml` 必须指向 `UniXNU-<soc>-common`，而 `UniXNU-sm8250-common` **不存在** |
| `scripts/unixnu/devicetree.py` | ADT 只导出带 `unixnu,adt-name` 的节点，属性走白名单；memory 必须单段且等于 `dram_size` |

umi 本身是独立仓、格式 1，抄它拿不到格式 2 的任何保证。

## 两个仓库的现状

### `D:\hos\sm8250-common`（共享 SoC 仓库）

| 文件 | 状态 |
| --- | --- |
| `soc.toml` | 已写；`source_revision` 待填已审查提交 |
| `dts/sm8250.dtsi` | cpus（8×MPIDR 0..0x700，`timebase-frequency`）、psci(smc)、GIC（`intc`）、UFS 主机（`ufshc`） |
| `configs/sm8250.config` | **刻意留空**：没有任何经真机验证的 SoC 级开关 |
| `patches/xnu/series` | 空，合法状态 |
| `kits/` | 占位 |
| `README.md` / `AGENTS.md` / `.gitignore` | 已写 |

### `D:\hos\cmi`（板级仓库）

| 文件 | 状态 |
| --- | --- |
| `board.toml` | 格式 2，实测值已填；含 `[[bootimg.dtb_node]]` splash 节点与 `chip_id = "164"` |
| `feeds.toml` | 指向 sm8250-common，`commit` 待固定 |
| `dts/cmi.dts` | 单段 memory + 22 个保留区（splash 带 `no-map`），`&ufs`/`&ufsphy` 启用；**dtc 编译通过** |
| `dts/panel-j2-p2-1-38-0c-0a.dtsi` | 面板节点 248 行（含 DCS 初始化序列），仅作参考，不参与编译 |
| `dts/touch-fts49.dtsi` | 触摸节点 54 行，仅作参考（触摸不走 ADT） |
| `configs/cmi_defconfig` | 已写，语法校验通过（8 条） |
| `porting.toml` | 14 个部分，全部 `planned`，组件覆盖与 board.toml 一致 |
| `README.md` / `AGENTS.md` / `.gitignore` / `local.toml.example` | 已写 |
| `patches/xnu/series` | 空 series（合法状态） |
| `scripts/package.sh` | 原样复制（各设备仓库相同，禁止修改） |
| `.github/workflows/porting-record.yml` | 调用 UniXNU 组织仓的复用工作流 |
| `.github/workflows/package.yml` | 按 sheng 改写，**从未运行**，`ref:` 仍是占位符 |
| `package/` / `proprietary-files.txt` | 占位（`.gitkeep` / 表头 + REQUIRED_） |
| `inputs.md` | 硬件输入实测记录 |

## 已验证到什么程度

```sh
# 编译（dtc 1.8.1，exit 0，无警告）
dtc -I dts -O dtb -i D:\hos\sm8250-common\dts \
    -o D:\hos\cmi\probe\hardware.dtb D:\hos\cmi\dts\cmi.dts

# 按生成器前置条件核对（复刻 devicetree.py 里会 raise 的检查）
python D:\hos\tools\check_adt.py D:\hos\cmi\probe\hardware.dtb \
       D:\hos\cmi\board.toml 0x1FBB00000
```

七项全过：memory 单段且 size 相等、8 CPU + timebase、psci、phandle 唯一、
导出节点名字唯一且属性在白名单、arm-io 窗口非零（`base=0x1000000 size=0x17000000`）。

**没有验证的**：ADT 实际生成（要 UniXNU 本地 checkout 的 `make-adt.py`）、
任何构建、任何真机启动。目前所有结论都停在"主机侧静态检查"。

## 未完成项（按文档的驱动适配顺序）

1. **显示与亮度**：`GopFramebuffer` 通过 `PE_current_console` 读**固件 GOP 交接的
   framebuffer**，不消费 DTS 节点——所以 dtsi 里不需要 `mdss`/`dsi`。面板初始化属于固件，
   落在 `cmiPkg`（见第 4 项）。启动镜像侧的 splash 节点已按
   [启动镜像设备树](https://unixnu.com/zh/porting/device-tree)加进 `[[bootimg.dtb_node]]`。
2. **输入**：**触摸不走 ADT**——参考设备仓库 `UniXNU-sheng` 的 `dts/sheng.dts` 里既没有
   触摸节点也没有 i2c，触摸通过 package 的板级状态绑定。所以原计划"给 dtsi 加 i2c/tlmm"
   是多余的；`dts/touch-fts49.dtsi` 只作硬件事实参考。真正要做的是
   `ShengHidInput` 的板级触控策略（FTM5 协议、供电时序）和 IOHIDFamily ABI 记录。
3. **UFS 组件不匹配**：板级用原厂 `compatible = "qcom,ufshc"`，ShengUfs 的 `IONameMatch`
   是 `qcom,sm8550-ufshc`，二者不会绑定。改 personality 属组件侧改动，需单独审核。
4. **`cmiPkg` 不存在**：`[firmware] dsc/fd` 指向的 `Platforms/Xiaomi/cmiPkg/cmi.dsc` 还没有，
   需要从 `uefi-umi` 的 `umiPkg` 派生（面板、按键、板 ID 全是 cmi 自己的）。
5. **`sm8250-common` 未发布**：`feeds.toml` 的 `commit` 现在只是占位符。
6. **收尾文件已补齐**（`porting.toml`、README、AGENTS.md、`package/`、`proprietary-files.txt`、
   `configs/cmi_defconfig`、`patches/xnu/series`、`scripts/package.sh`、两个工作流）。
   仍缺 `unixnu.lock`（由 `./unixnu fetch` 写入），且 `package.yml` 从未运行过——里面的
   `ref:` 还是占位符。
7. **安装方式未定**：UniXNU 会整块替换 226 GiB 的 `userdata`。要保留 Android 得先做
   [双系统分区](https://unixnu.com/zh/porting/dual-system-partition)。

## 关键实测值

完整记录见 [inputs.md](inputs.md)，摘要：

| 项 | 值 |
| --- | --- |
| `userdata` | first `0x2C0000` / last `0x3B4B7FA`，`lba_bytes = 4096` |
| DRAM | 三 bank，和 = `0x1FBB00000`（7.93 GiB，本机 8 GB SKU） |
| msm-id / board-id | `0x164` / `0x24` |
| 面板 | `qcom,mdss_dsi_j2_p2_1_38_0c_0a_dsc_cmd`（DSC cmd，1080×2340，60/90 Hz，reset GPIO12，TE GPIO66） |
| 触摸 | `st,fts` @ `i2c@a94000` 0x49，reset GPIO38 / irq GPIO39，固件 `st_fts_j1.ftb` |

## 工具（本机）

| 工具 | 用途 |
| --- | --- |
| `D:\hos\tools\dtc\ucrt64\bin\dtc.exe` | DTC 1.8.1（MSYS2 包解出，依赖 `libyaml-0-2.dll` 已补齐） |
| `D:\hos\tools\fdt2dts.py` | FDT → dts 转换（`fdtdump` 对 `fdt.cmi.dtb` 报 header invalid，自写解析器绕开） |
| `D:\hos\tools\check_adt.py` | 生成器前置条件核对 |
| `D:\hos\cmi\probe\fdt.cmi.dtb` / `.dts` | 设备合并 DT 的原始 blob 与 37,086 行可读版本 |
