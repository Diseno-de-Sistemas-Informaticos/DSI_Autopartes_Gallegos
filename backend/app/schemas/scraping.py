from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ScrapingSearchRequest(BaseModel):
    code: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    search_type: str = Field(default="Descripcion")

    @model_validator(mode="after")
    def validate_search_term(self):
        if self.search_type not in {"Codigo", "Descripcion"}:
            raise ValueError("search_type debe ser Codigo o Descripcion")

        term = self.code if self.search_type == "Codigo" else self.description
        if not term or not term.strip():
            raise ValueError("Debe proporcionar el término correspondiente")

        if self.search_type == "Codigo":
            self.code = term.strip()
        else:
            self.description = term.strip()
        return self


class CompareRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)


class ScrapingResult(BaseModel):
    id_external_product: Optional[int] = None
    provider: Optional[str] = None
    branch: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[Decimal] = None
    availability: Optional[bool] = None
    stock: Optional[int] = None
    captured_at: Optional[datetime] = None
    equivalence_confirmed: bool = False
