"""API router for product-service v1."""
from fastapi import APIRouter

from app.api.v1.admin_products import router as admin_products_router
from app.api.v1.admin_skus import router as admin_skus_router
from app.api.v1.admin_categories import router as admin_categories_router
from app.api.v1.admin_attributes import router as admin_attributes_router
from app.api.v1.admin_groups import router as admin_groups_router
from app.api.v1.products import router as products_router
from app.api.v1.groups import router as groups_router

router = APIRouter()

# Admin routes
router.include_router(admin_products_router, prefix="/admin/products", tags=["admin-products"])
router.include_router(admin_skus_router, prefix="/admin/skus", tags=["admin-skus"])
router.include_router(admin_categories_router, prefix="/admin/categories", tags=["admin-categories"])
router.include_router(admin_attributes_router, prefix="/admin/attributes", tags=["admin-attributes"])
router.include_router(admin_groups_router, prefix="/admin/groups", tags=["admin-groups"])

# Public routes (App/BFF)
router.include_router(products_router, prefix="/products", tags=["products"])
router.include_router(groups_router, prefix="/groups", tags=["groups"])
