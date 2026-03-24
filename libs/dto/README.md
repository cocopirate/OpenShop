# Libs - DTO

## 职责

定义跨服务调用时共享的数据传输对象（Data Transfer Object），避免各服务重复定义相同结构体。

## 规范

- 命名以 `Request` / `Response` / `DTO` 结尾
- 不包含任何业务逻辑
- 字段注释完整