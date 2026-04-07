import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://openshop.vsxul.com',
  integrations: [
    starlight({
      title: 'OpenShop 文档',
      description: 'OpenShop 微服务电商平台文档',
      defaultLocale: 'root',
      locales: {
        root: {
          label: '简体中文',
          lang: 'zh-CN',
        },
      },
      social: {
        github: 'https://github.com/cocopirate/OpenShop',
      },
      sidebar: [
        {
          label: '概览',
          items: [
            { label: '项目介绍', slug: '00-overview/introduction' },
            { label: '业务流程', slug: '00-overview/business-flow' },
            { label: '术语表', slug: '00-overview/glossary' },
          ],
        },
        {
          label: '快速开始',
          items: [
            { label: '快速启动', slug: '01-getting-started/quick-start' },
            { label: '本地开发', slug: '01-getting-started/local-dev' },
            { label: 'Docker 运行', slug: '01-getting-started/docker-run' },
          ],
        },
        {
          label: '用户指南',
          items: [
            { label: '商家入驻', slug: '02-user-guide/merchant-onboarding' },
            { label: '下单流程', slug: '02-user-guide/order-process' },
            { label: '通知系统', slug: '02-user-guide/notification' },
          ],
        },
        {
          label: 'API 参考',
          items: [
            { label: 'API 契约', slug: '03-api-reference/api-contract' },
            { label: '认证', slug: '03-api-reference/auth' },
            { label: '用户管理', slug: '03-api-reference/users' },
            { label: '商家管理', slug: '03-api-reference/merchants' },
            { label: '订单管理', slug: '03-api-reference/orders' },
            { label: '短信服务', slug: '03-api-reference/sms' },
          ],
        },
        {
          label: '架构设计',
          items: [
            { label: '系统架构总览', slug: '04-architecture/system-overview' },
            { label: '领域模型', slug: '04-architecture/domain-model' },
            { label: '微服务设计', slug: '04-architecture/microservices' },
            { label: 'API 网关', slug: '04-architecture/gateway' },
            { label: '事件驱动', slug: '04-architecture/event-driven' },
            { label: 'Saga 编排', slug: '04-architecture/saga' },
            { label: '短信通知链路', slug: '04-architecture/sms-notification-chain' },
            { label: '安全设计', slug: '04-architecture/security' },
          ],
        },
        {
          label: '服务详情',
          items: [
            { label: '认证服务', slug: '05-services/auth-service/overview' },
            { label: '认证服务 API', slug: '05-services/auth-service/api' },
            { label: '管理员服务 RBAC', slug: '05-services/admin-service/rbac' },
            { label: '管理员服务', slug: '05-services/admin-service/overview' },
            { label: '管理员服务 API', slug: '05-services/admin-service/api' },
            { label: '管理员服务数据模型', slug: '05-services/admin-service/schema' },
            { label: '消费者服务', slug: '05-services/consumer-service/overview' },
            { label: '消费者服务 API', slug: '05-services/consumer-service/api' },
            { label: '消费者服务数据模型', slug: '05-services/consumer-service/schema' },
            { label: '消费者服务事件', slug: '05-services/consumer-service/events' },
            { label: '商家服务', slug: '05-services/merchant-service/overview' },
            { label: '订单服务', slug: '05-services/order-service/overview' },
            { label: '短信服务', slug: '05-services/sms-service/overview' },
            { label: '第三方服务集成', slug: '05-services/third-party-service/overview' },
          ],
        },
        {
          label: '需求文档',
          items: [
            { label: '认证服务 PRD', slug: '11-requirements/auth-service' },
            { label: '管理员服务 PRD', slug: '11-requirements/admin-service' },
            { label: '消费者服务 PRD', slug: '11-requirements/consumer-service' },
            { label: '商家服务 PRD', slug: '11-requirements/merchant-service' },
            { label: '商品服务 PRD', slug: '11-requirements/product-service' },
            { label: '订单服务 PRD', slug: '11-requirements/order-service' },
            { label: '短信服务 PRD', slug: '11-requirements/sms-service' },
            { label: '第三方服务 PRD', slug: '11-requirements/third-party-service' },
          ],
        },
        {
          label: '开发指南',
          items: [
            { label: '项目结构', slug: '06-development/project-structure' },
            { label: '编码规范', slug: '06-development/coding-style' },
            { label: 'API 设计规范', slug: '06-development/api-design' },
            { label: '错误处理', slug: '06-development/error-handling' },
            { label: '日志规范', slug: '06-development/logging' },
          ],
        },
        {
          label: '部署',
          items: [
            { label: 'Kubernetes 部署', slug: '07-deployment/k8s-deploy' },
            { label: '环境变量', slug: '07-deployment/env' },
            { label: 'CI/CD', slug: '07-deployment/ci-cd' },
          ],
        },
        {
          label: '可观测性',
          items: [
            { label: '日志', slug: '08-observability/logging' },
            { label: '链路追踪', slug: '08-observability/tracing' },
            { label: '指标监控', slug: '08-observability/metrics' },
          ],
        },
        {
          label: '最佳实践',
          items: [
            { label: '幂等性设计', slug: '09-best-practices/idempotency' },
            { label: '重试策略', slug: '09-best-practices/retry' },
            { label: '服务拆分', slug: '09-best-practices/service-splitting' },
          ],
        },
        {
          label: 'FAQ',
          items: [
            { label: '常见问题', slug: '10-faq/common' },
            { label: '故障排查', slug: '10-faq/troubleshooting' },
          ],
        },
      ],
    }),
  ],
});
