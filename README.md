# 好太太晾衣架 D10-ZM

Home Assistant 自定义集成：根据 [Xiaomi Home](https://github.com/XiaoMi/ha_xiaomi_home) 里的 **好太太晾衣架 D10-ZM**（`hotata.airer.d10zm`）创建一个独立设备，上面是方向校正后的窗帘实体。米家原始设备与实体不会被隐藏或改动。

米家把晾衣架映射成 Cover（百叶/窗帘）后，常见现象是：

- 点 **下降**，杆子却在升
- 点 **上升**，杆子却在降
- 开合状态相反（全开显示成全关）
- 位置百分比相反（0% 和 100% 对调）

本集成会在 **设置 → 设备与服务 → 设备** 中新增一台设备（名称带「反向」），而不是出现在辅助元素里：

| 操作 / 状态 | 米家原实体 | 本集成实体 |
| --- | --- | --- |
| 上升键（open） | `cover.open_cover` | 改为调用 `cover.close_cover` |
| 下降键（close） | `cover.close_cover` | 改为调用 `cover.open_cover` |
| 暂停 | `cover.stop_cover` | 原样转发 |
| 位置百分比 | `current_position` | `100 - current_position`，并提供滑块 / 0% 25% 75% 100% |
| 上升中 | `opening` | 显示为 `closing` |
| 下降中 | `closing` | 显示为 `opening` |
| 全关 / 全开 | 位置 0 / 100 | 对调 |

## 安装

1. 确认已安装并登录 **Xiaomi Home（米家）** 集成，且 D10-ZM 已出现窗帘实体。
2. 将本仓库的 `custom_components/hotata_airer` 复制到 Home Assistant 的 `config/custom_components/hotata_airer`。
3. 也可以在 HACS 中以自定义仓库方式添加本仓库，类别选 Integration。
4. 重启 Home Assistant。
5. 前往 **设置 → 设备与服务 → 添加集成**（不要走「辅助元素 → 创建辅助元素」），搜索 **Hotata Airer D10-ZM** / **好太太晾衣架 D10-ZM**。
6. 选择米家里 D10-ZM 对应的窗帘实体（配置流程会优先匹配该型号）。

如果当前还显示在「辅助元素」里：

1. 先在辅助元素里 **删除** 旧条目。
2. 用本仓库最新的 `custom_components/hotata_airer` 覆盖后，**完全重启** Home Assistant（只重载集成不够，`integration_type` 要重启才会更新）。
3. 再从 **添加集成** 重新添加。完成后应出现在 **设置 → 设备与服务 → 设备**，设备名带「（反向）」。

## 要求

- Home Assistant 2024.1 及以上
- 已配置 Xiaomi Home 自定义集成
- 设备型号 `hotata.airer.d10zm`（好太太晾衣架 D10-ZM）

D10-ZM 规格里没有可写的目标开合度。反向设备上的窗帘仍会打开 Home Assistant 的百分比滑块：若米家原实体支持 `set_cover_position`，则把目标取反后转发；否则根据当前位置驱动上升/下降，接近目标后自动暂停。全开（100%）和全关（0%）会一直走到限位。中间档位依赖设备上报的当前位置，可能和设定值有几个百分点偏差。
