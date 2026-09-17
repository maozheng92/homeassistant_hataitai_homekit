# 好太太晾衣架 D10-ZM HomeKit

Home Assistant 自定义集成：把 [Xiaomi Home](https://github.com/XiaoMi/ha_xiaomi_home) 里的 **好太太晾衣架 D10-ZM**（`hotata.airer.d10zm`）窗帘实体方向校正后再给 HomeKit / 仪表盘使用。

米家把晾衣架映射成 Cover（百叶/窗帘）后，常见现象是：

- 点 **下降**，杆子却在升
- 点 **上升**，杆子却在降
- 开合状态相反（全开显示成全关）
- 位置百分比相反（0% 和 100% 对调）

本集成会包一层反向窗帘实体：

| 操作 / 状态 | 米家原实体 | 本集成实体 |
| --- | --- | --- |
| 上升键（open） | `cover.open_cover` | 改为调用 `cover.close_cover` |
| 下降键（close） | `cover.close_cover` | 改为调用 `cover.open_cover` |
| 暂停 | `cover.stop_cover` | 原样转发 |
| 位置百分比 | `current_position` | `100 - current_position` |
| 上升中 | `opening` | 显示为 `closing` |
| 下降中 | `closing` | 显示为 `opening` |
| 全关 / 全开 | 位置 0 / 100 | 对调 |

默认会隐藏米家原始窗帘实体，并把原先暴露给 HomeKit 的设置挪到新实体上，避免桥接里出现两个方向相反的晾衣架。

## 安装

1. 确认已安装并登录 **Xiaomi Home（米家）** 集成，且 D10-ZM 已出现窗帘实体。
2. 将本仓库的 `custom_components/hotata_airer` 复制到 Home Assistant 的 `config/custom_components/hotata_airer`。
3. 也可以在 HACS 中以自定义仓库方式添加本仓库，类别选 Integration。
4. 重启 Home Assistant。
5. 前往 **设置 → 设备与服务 → 添加集成**，搜索 **Hotata Airer D10-ZM** / **好太太晾衣架 D10-ZM**。
6. 选择米家里 D10-ZM 对应的窗帘实体（配置流程会优先匹配该型号）。

## HomeKit

1. 在本集成里保持「隐藏米家原始窗帘实体」开启。
2. 将新的窗帘实体暴露给 **HomeKit Bridge**（若原实体已经暴露，集成会尽量把暴露开关一并迁移过来）。
3. 若 iPhone 家庭 App 里还是旧配件，重载一次 HomeKit 桥接，或从桥接中排除米家原窗帘、只包含校正后的实体。

灯、故障等其它米家实体不会改动，仍留在原设备上。

## 要求

- Home Assistant 2024.1 及以上
- 已配置 Xiaomi Home 自定义集成
- 设备型号 `hotata.airer.d10zm`（好太太晾衣架 D10-ZM）

D10-ZM 规格里只有上升 / 下降 / 暂停和当前位置，没有目标开合度，因此中间百分比通常只能显示、不能精确停在某一档。这是设备限制，不是本集成额外限制。
