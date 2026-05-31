# External Data Notes

放置外部数据库的下载说明、授权说明、字段索引、轻量元数据，以及可公开共享的外部参考数据。

## 可提交

- `price_trade/`: WITS、EITI、价格清单、企业报告和公开贸易/价格参考材料。
- `project_inventory/`: 可协作维护的项目级资产清单、公开项目资料和受限商业源元数据。

## 不提交

- 需要订阅、账号授权或禁止再分发的原始文件。
- 商业数据库导出文件，例如 S&P Global / Capital IQ 原始导出。
- 未脱敏访谈材料、联系人、账号、token、cookie 或私钥。

受限原件统一放在仓库本地 `_private/` 目录，由 `.gitignore` 排除。
