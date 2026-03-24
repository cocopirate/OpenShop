# Privacy Number Service

## 职责

提供隐私号码的绑定与中转能力，保护买卖双方真实手机号不互相暴露。

## 依赖

- 第三方隐私号平台（如阿里云隐私号、腾讯隐私通话）

## 接口

详见 [API Contract](../../docs/api-contract.md)

## 目录结构

```
privacy-number/
├── src/
│   ├── controller/
│   ├── service/
│   └── provider/       # 第三方隐私号 SDK 封装
├── test/
└── README.md
```