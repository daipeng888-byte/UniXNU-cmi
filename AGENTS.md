# AGENTS.md — UniXNU-cmi

## 职责

小米 10 Pro（`cmi`，SM8250）的板级仓库。只放**这一块板**特有的内容：板级连接、
组件选择、内存与保留区、固件选择、分区与电源策略。

共享 SoC 资源放 [UniXNU-sm8250-common](https://github.com/REQUIRED_OWNER/UniXNU-sm8250-common)；
可复用驱动放组件仓库，不进本仓库的 `package/`。

## 必读

- [移植设备](https://unixnu.com/zh/porting/steps)
- [设备仓库规范](https://unixnu.com/zh/porting/device-repository)
- [设备树](https://unixnu.com/zh/porting/device-tree)
- [适配记录](https://unixnu.com/zh/porting/records)
- [组件目录](https://unixnu.com/zh/reference/components)
- 本仓库 `porting.toml`（权威记录）与 `inputs.md`（实测输入）

## 规则

1. 硬件值必须有来源：目标设备观测或原厂 DTS，写进注释并更新 `inputs.md`。
2. `porting.toml` 与 `board.toml` 的设备身份必须一致；改了硬件输入就同步改记录。
3. 不虚报完成等级：`host-verified` 和 `device-verified` 需要命令、完整 40 位提交和日志。
4. 数组会替换继承值：改 `components`/`config_fragments`/`patch_series`/`archives` 时写全列表。
5. 未选中的组件写在 `limits` 里，不要放进 `components`。
6. 提交前缀：`feat(<area>)`、`fix(<area>)`、`docs`、`build(<area>)`、`chore`。
