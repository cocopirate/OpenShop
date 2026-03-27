#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------------------------------------------------------------------------
# Prerequisite: uv must be installed
# Install: curl -LsSf https://astral.sh/uv/install.sh | sh
# ---------------------------------------------------------------------------
if ! command -v uv &>/dev/null; then
  echo "ERROR: uv is not installed."
  echo "  Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  Then re-run this script."
  exit 1
fi

echo "=== Starting OpenShop infrastructure ==="
docker-compose -f "${ROOT}/infra/docker-compose.yml" up -d
echo "Infrastructure started. Waiting 10s for services to be ready..."
sleep 10

# Format: "<relative-path>:<port>"
SERVICES=(
  "orchestration/order-orchestration:8100"
  "services/consumer-service:8001"
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

  if [ ! -f "${ROOT}/${path}/requirements.txt" ]; then
    continue
  fi

  echo "[${svc}] Preparing on port ${port}..."
  (
    cd "${ROOT}/${path}"

    # 1. Create virtual environment if not present
    if [ ! -d ".venv" ]; then
      uv venv --python 3.11
    fi

    # 2. Install / sync dependencies
    uv pip install -q -r requirements.txt

    # 3. Bootstrap .env from template when .env is absent
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
      cp .env.example .env
      echo "  [${svc}] .env created from .env.example — review and update secrets before use"
    fi

    # 4. Run database migrations when alembic is configured
    if [ -f "alembic.ini" ]; then
      echo "  [${svc}] Running alembic migrations..."
      .venv/bin/alembic upgrade head
    fi

    # 5. Start the service in the background
    echo "  [${svc}] Starting uvicorn on port ${port}..."
    .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${port}" --reload &
  )
done

echo ""
echo "All services are starting up."
echo "Run ./scripts/health-check.sh to verify that each service is healthy."
