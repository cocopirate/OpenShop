#!/usr/bin/env bash
set -euo pipefail

SERVICES=(
  "api-gateway:8080"
  "app-bff:8090"
  "admin-bff:8091"
  "order-orchestration:8100"
  "user-service:8001"
  "merchant-service:8002"
  "product-service:8003"
  "inventory-service:8004"
  "order-service:8005"
  "aftersale-service:8006"
  "promotion-service:8007"
  "location-service:8008"
  "notification-service:8009"
  "sms-service:8010"
  "virtual-number-service:8011"
)

echo "=== OpenShop Health Check ==="
PASS=0
FAIL=0

for entry in "${SERVICES[@]}"; do
  name="${entry%%:*}"
  port="${entry##*:}"
  url="http://localhost:${port}/health"

  if curl -sf --max-time 3 "${url}" > /dev/null 2>&1; then
    echo "  [OK]   ${name} (${url})"
    ((PASS++)) || true
  else
    echo "  [FAIL] ${name} (${url})"
    ((FAIL++)) || true
  fi
done

echo ""
echo "Result: ${PASS} healthy, ${FAIL} unreachable"
[ "${FAIL}" -eq 0 ] && exit 0 || exit 1
