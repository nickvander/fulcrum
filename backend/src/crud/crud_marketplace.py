from src.crud.base import CRUDBase
from src.models.marketplace import Marketplace
from src.schemas.marketplace import MarketplaceCreate, MarketplaceUpdate

class CRUDMarketplace(CRUDBase[Marketplace, MarketplaceCreate, MarketplaceUpdate]):
    pass

marketplace = CRUDMarketplace(Marketplace)
