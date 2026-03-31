"""Product-service ORM models."""
from app.models.spu import Spu, SpuStatus  # noqa: F401
from app.models.sku import Sku, SkuStatus  # noqa: F401
from app.models.category import Category, CategoryStatus  # noqa: F401
from app.models.attribute import Attribute, AttributeType, CategoryAttribute  # noqa: F401
from app.models.product_group import ProductGroup, ProductGroupItem, GroupType, GroupStatus  # noqa: F401
