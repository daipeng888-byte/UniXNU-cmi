# 校验方法与剩余阻塞

本文件只做一件事：给出**可复现**的命令，说明每条命令证明什么、不证明什么。
所有命令都在 Windows 主机上、不接触设备的情况下跑过。

## 前置

| 项 | 位置 / 版本 |
| --- | --- |
| dtc | `D:\hos\tools\dtc\ucrt64\bin\dtc.exe`（DTC 1.8.1，MSYS2 包解出；依赖 `libyaml-0-2.dll` 已放在同目录） |
| python | 3.12（用到标准库 `tomllib`、`zstandard`） |
| 仓库 | `D:\hos\cmi`（板级）、`D:\hos\sm8250-common`（SoC） |
| 设备数据 | `D:\hos\cmi\probe\fdt.cmi.dtb`（TWRP 里 `adb pull /sys/firmware/fdt` 得到）/ `fdt.cmi.dts`（37,086 行） |

## 1. 编译设备树

```sh
dtc -I dts -O dtb -i D:\hos\sm8250-common\dts \
    -o D:\hos\cmi\probe\hardware.dtb D:\hos\cmi\dts\cmi.dts
```

**期望**：`exit 0`，无任何 warning。

证明：dts/dtsi 语法与引用（label、include、cell 宽度）自洽，`reg` 没被截断。
不证明：DTB 能被 XNU 接受；`timebase-frequency` 的数值正确。

## 2. ADT 生成器前置条件

```sh
python D:\hos\tools\check_adt.py D:\hos\cmi\probe\hardware.dtb \
       D:\hos\cmi\board.toml 0x1FBB00000
```

**期望**：7 项全 PASS，其中

```
memory: base=0x80000000 size=0x1fbb00000 (7.93 GiB)
cpus: 8 个, timebase-frequency=19200000
phandle: 1 个
arm-io: base=0x1000000 size=0x17000000 节点=['intc', 'ufshc']
```

证明：复刻 `scripts/unixnu/devicetree.py` 里会 `raise` 的检查——单段 memory、
`dram_size` 逐字节相等、`/cpus` 有 timebase、多 CPU 有 PSCI、phandle 唯一、
导出节点名字唯一且属性在白名单、arm-io 窗口非零。
不证明：真实 `make-adt.py` 能跑通（需要 UniXNU checkout）；驱动会绑定到这些节点。

## 3. 仓库结构与记录一致性

```sh
python D:\hos\tools\check_repo.py D:\hos\cmi
```

**期望**：全部 PASS，唯一 PEND 是 `unixnu.lock`。

证明：`board.toml`/`feeds.toml`/`porting.toml` 可解析、schema 版本正确（board 2 / record 1）、
身份一致、`cmi_defconfig` 语法正确、记录 14 个部分字段齐全且状态合法、
组件覆盖与 `board.toml` 的 `[components] include` 完全相等、
完成清单 15 项文件都在、两个工作流 YAML 可解析。
不证明：`porting-record.py check` 会通过（它有更严的路径归属与证据规则）；
`package.yml` 能跑。

## 4. 设备数据再转换（可选，验证工具链）

```sh
adb pull /sys/firmware/fdt D:\hos\cmi\probe\fdt.cmi.dtb      # 需在 TWRP 下
python D:\hos\tools\fdt2dts.py D:\hos\cmi\probe\fdt.cmi.dtb D:\hos\cmi\probe\fdt.cmi.dts
```

**期望**：`wrote 37087 lines`。

## 5. 官方检查器（需要 UniXNU 检出，本机未做）

```sh
cd <UniXNU checkout>
./unixnu defconfig cmi_defconfig -D D:/hos/cmi
./unixnu fetch      -D D:/hos/cmi
./unixnu status --json -D D:/hos/cmi
./unixnu tree       -D D:/hos/cmi
python scripts/porting-record.py check --device D:/hos/cmi
```

**这些一条都没跑过**——没有 UniXNU 本地检出，也没有 `UniXNU-sm8250-common` 的已发布提交。
跑之前 `feeds.toml` 的 `commit` 必须换成 40 位真实提交。

## 剩余阻塞

| # | 阻塞 | 影响 | 下一步 |
| --- | --- | --- | --- |
| 1 | `UniXNU-sm8250-common` 未发布，`feeds.toml` 的 `commit` 是占位符 | 解析器无法固定 SoC 源码 | 建仓、加 `unixnu` topic、固定提交 |
| 2 | `cmiPkg` 不存在 | 无法出固件，无法上机 | 从 `umiPkg` 派生：换 `PLATFORM_NAME`/`OUTPUT_DIRECTORY`/GUID、SMBIOS 改 "Mi 10 Pro"/"cmi"、按键 GPIO 用 cmi 值；`InheritedFbDxe`、`UmiRamPayloadDxe`、SPMI/RPMH 库可复用（DSC 已 `!include KonaPkg/KonaPkg.dsc.inc`） |
| 3 | ShengUfs 只认 `qcom,sm8550-ufshc`，cmi 报 `qcom,ufshc` | 存储驱动不绑定 | 组件侧扩展 personality，或确认 SM8250 常量后再选 |
| 4 | 保留区只有 splash 设了 `no-map` | 其余 21 个可能被内核当可用内存 | 逐区从原厂 DTS 读 `no-map`/`reusable` |
| 5 | `timebase-frequency = 19200000` 未实测 | 定时器频率错会导致时钟漂移 | 从启动日志或硬件测量确认 |
| 6 | `package.yml` 从未运行，`ref:` 是占位符 | CI 打包不可用 | 固定 UniXNU/uefi-cmi 提交后跑一次 |
| 7 | 安装会整块替换 226 GiB `userdata` | Android 数据全清 | 决定是否先做双系统分区 |
| 8 | 无任何构建、无任何真机启动 | 全部结论停在主机侧静态检查 | 完成 1、2 后跑第 5 节的命令 |

## 未验证事项的诚实边界

- 面板 DCS 初始化序列是从设备 DT 原样导出的，但**没有在 cmiPkg 里被使用过**。
- 触摸节点只作硬件事实参考：参考设备仓库 `UniXNU-sheng` 的板级 dts 里既无触摸节点也无 i2c，
  触摸走 package 的板级状态。
- `dram_size` 取三 bank 之和（`0x1fbb00000`）而非 `0x200000000` 跨度，洞（69 MiB）不计入 DRAM。
- 本机 8 GB SKU 的实测值；12 GB 机型需重新求和。
