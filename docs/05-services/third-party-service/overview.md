# 第三方服务集成

## 短信供应商

sms-service 支持以下短信供应商：

| 供应商 | 标识符 | API 地址 |
|--------|--------|---------|
| 阿里云短信 | `aliyun` | dysmsapi.aliyuncs.com |
| 腾讯云短信 | `tencent` | sms.tencentcloudapi.com |
| 创蓝短信 | `chuanglan` | smssh1.253.com |

### 供应商切换

```bash
# 环境变量配置（启动时生效）
SMS_PROVIDER=aliyun
SMS_PROVIDER_FALLBACK=tencent

# 运行时切换（通过管理 API，重启后恢复）
PUT /api/v1/admin/sms/config
{"sms_provider": "tencent", "sms_provider_fallback": "chuanglan"}
```

## 地图服务

location-service（:8008）集成第三方地图 API，提供：

- 地址解析（Geocoding）
- 逆地址解析（Reverse Geocoding）
- 配送距离计算

支持的供应商：高德地图、百度地图（通过环境变量配置）

## Elasticsearch

product-service 使用 Elasticsearch 8 进行商品全文检索：

- 索引：`products`
- 字段：`name`、`description`、`category`
- 支持中文分词（IK 分词器）

本地 Elasticsearch 地址：http://localhost:9200

## RabbitMQ

所有异步事件通过 RabbitMQ 传递：

- 本地管理 UI：http://localhost:15672（用户名/密码：openshop/openshop123）
- Exchange 类型：Topic
- 消息持久化：开启

详见 [事件驱动架构](../../04-architecture/event-driven.md)。
