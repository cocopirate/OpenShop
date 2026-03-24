# Libs - Common

## 职责

所有微服务共享的公共模块，包括：

- 统一响应体封装（`Result<T>`）
- 全局异常处理（`GlobalExceptionHandler`）
- 基础常量与枚举定义

## 使用方式

在各服务的 `pom.xml` 或 `package.json` 中引入此模块作为本地依赖。