# 好太太晾衣架 D10-ZM

Home Assistant 自定义集成：根据 [Xiaomi Home](https://github.com/XiaoMi/ha_xiaomi_home) 里的 **好太太晾衣架 D10-ZM**（`hotata.airer.d10zm`）再创建一个方向校正后的窗帘实体。米家原始实体不会被隐藏或改动。

米家把晾衣架映射成 Cover（百叶/窗帘）后，常见现象是：

- 点 **下降**，杆子却在升
- 点 **上升**，杆子却在降
- 开合状态相反（全开显示成全关）
- 位置百分比相反（0% 和 100% 对调）

本集成会另建一个反向窗帘实体：

| 操作 / 状态 | 米家原实体 | 本集成实体 |
| --- | --- | --- |
| 上升键（open） | `cover.open_cover` | 改为调用 `cover.close_cover` |
| 下降键（close） | `cover.close_cover` | 改为调用 `cover.open_cover` |
| 暂停 | `cover.stop_cover` | 原样转发 |
| 位置百分比 | `current_position` | `100 - current_position` |
| 上升中 | `opening` | 显示为 `closing` |
| 下降中 | `closing` | 显示为 `opening` |
| 全关 / 全开 | 位置 0 / 100 | 对调 |

## 安装

1. 确认已安装并登录 **Xiaomi Home（米家）** 集成，且 D10-ZM 已出现窗帘实体。
2. 将本仓库的 `custom_components/hotata_airer` 复制到 Home Assistant 的 `config/custom_components/hotata_airer`。
3. 也可以在 HACS 中以自定义仓库方式添加本仓库，类别选 Integration。
4. 重启 Home Assistant。
5. 前往 **设置 → 设备与服务 → 添加集成**，搜索 **Hotata Airer D10-ZM** / **好太太晾衣架 D10-ZM**。
6. 选择米家里 D10-ZM 对应的窗帘实体（配置流程会优先匹配该型号）。

灯、故障等其它米家实体不会改动。新实体名称默认为 **晾衣架（反向）**，方便和原窗帘区分。

## 要求

- Home Assistant 2024.1 及以上
- 已配置 Xiaomi Home 自定义集成
- 设备型号 `hotata.airer.d10zm`（好太太晾衣架 D10-ZM）

D10-ZM 规格里只有上升 / 下降 / 暂停和当前位置，没有目标开合度，因此中间百分比通常只能显示、不能精确停在某一档。这是设备限制，不是本集成额外限制。
