# sms-service（短信能力服务）

对接第三方短信供应商（如阿里云、腾讯云），提供统一短信发送能力。

## 职责

- 验证码短信发送
- 营销短信群发
- 短信发送状态回调

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/sms/send` | POST | 发送短信 |
| `GET /api/v1/sms/records/{phone}` | GET | 查询发送记录 |
| `POST /api/v1/sms/verify` | POST | 验证短信验证码 |

## 数据模型

- SmsRecord
- SmsTemplate

## 依赖服务

- notification-service（被调用）

## 端口

- 服务端口: **8010**
