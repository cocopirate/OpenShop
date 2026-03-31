"""Product-service Pydantic schemas."""
from app.schemas.spu import SpuCreate, SpuUpdate, SpuResponse, SpuListResponse  # noqa: F401
from app.schemas.sku import SkuCreate, SkuBatchCreate, SkuUpdate, SkuResponse  # noqa: F401
from app.schemas.category import (  # noqa: F401
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTreeNode,
)
from app.schemas.attribute import (  # noqa: F401
    AttributeCreate,
    AttributeResponse,
    CategoryAttributeCreate,
    CategoryAttributeResponse,
)
from app.schemas.product_group import (  # noqa: F401
    ProductGroupCreate,
    ProductGroupUpdate,
    ProductGroupResponse,
    GroupItemCreate,
    GroupItemBatchCreate,
    GroupItemResponse,
)
