#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Starting OpenShop infrastructure ==="
docker-compose -f "${ROOT}/infra/docker-compose.yml" up -d
echo "Infrastructure started. Waiting 10s for services to be ready..."
sleep 10

SERVICES=(
  "orchestration/order-orchestration:8100"
  "services/user-service:8001"
  "services/merchant-service:8002"
  "services/product-service:8003"
  "services/inventory-service:8004"
  "services/order-service:8005"
  "services/aftersale-service:8006"
  "services/promotion-service:8007"
  "services/location-service:8008"
  "services/notification-service:8009"
  "services/sms-service:8010"
  "services/virtual-number-service:8011"
)

echo ""
echo "=== Starting domain services ==="
for entry in "${SERVICES[@]}"; do
  path="${entry%%:*}"
  port="${entry##*:}"
  svc="$(basename "${path}")"

  if [ -f "${ROOT}/${path}/requirements.txt" ]; then
    echo "Starting ${svc} on port ${port}..."
    (
      cd "${ROOT}/${path}"
      pip install -q -r requirements.txt
      uvicorn app.main:app --host 0.0.0.0 --port "${port}" --reload &
    )
  fi
done

echo ""
echo "All services starting. Run ./scripts/health-check.sh to verify."
