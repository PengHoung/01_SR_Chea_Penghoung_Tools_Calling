import re
import database as db
from typing import Any, Union, List, Optional
from pydantic import BaseModel, Field, model_validator

class SearchProductsInput(BaseModel):
    query: str = Field(
        description="Specific item name or category keyword to look up (e.g., 'laptop', 'mouse')."
    )

class CheckStockInput(BaseModel):
  product_ids: Optional[Any] = Field(
      default=None,
      description=(
          "Product ID, list of IDs, or leave blank to check all inventory."
      ),
  )

class ListAllProductsInput(BaseModel):
    pass

class BuyProductInput(BaseModel):
  product_id: int = Field(
      description="The positive integer ID of the product to purchase."
  )
  quantity: int = Field(
      default=1,
      gt=0,
      description="Number of units to purchase. Must be a positive integer.",
  )

  @model_validator(mode="before")
  @classmethod
  def resolve_id_and_query(cls, data: Any) -> Any:
    if not isinstance(data, dict):
      return data

    target_id = None

    raw_pid = data.get("product_id")
    if raw_pid is not None and str(raw_pid).strip() != "":
      digits = re.findall(r"\d+", str(raw_pid))
      if digits:
        target_id = int(digits[0])

    if target_id is None:
      alt = (
          data.get("product_ids")
          or data.get("id")
          or data.get("item_id")
      )
      if alt is not None:
        digits = re.findall(r"\d+", str(alt))
        if digits:
          target_id = int(digits[0])

    if target_id is None:
      search_term = data.get("query")
      if not search_term and isinstance(raw_pid, str) and raw_pid != "search_products":
        search_term = raw_pid

      if search_term:
        rows = db.query_products_by_keyword(str(search_term).strip())
        if rows:
          target_id = rows[0][0]

    if target_id is not None:
      return {
          "product_id": target_id,
          "quantity": int(data.get("quantity", 1) or 1),
      }

    raise ValueError(
        f"Could not find a valid product ID or matched item name in: {data}"
    )


class DeleteProductInput(BaseModel):
    product_id: int = Field(
        gt=0, description="The positive integer ID of the product to delete."
    )