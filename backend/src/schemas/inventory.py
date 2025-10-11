from pydantic import BaseModel

class StockAdjustment(BaseModel):
    adjustment: int
