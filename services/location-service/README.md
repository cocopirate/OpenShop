# location-service（地址服务）

负责收货地址管理与地理编码服务。

## 职责

- 用户收货地址 CRUD
- 地址地理编码（经纬度）
- 行政区划数据维护

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/locations/addresses` | GET | 获取用户地址列表 |
| `POST /api/v1/locations/addresses` | POST | 新增收货地址 |
| `GET /api/v1/locations/regions` | GET | 获取行政区划 |

## 数据模型

- Address
- GeoCode
- Region

## 依赖服务

- user-service（用户身份校验）

## 端口

- 服务端口: **8008**
