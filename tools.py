import re
from typing import Any, Optional, Union
from langchain_core.tools import tool
from schemas import (
    SearchProductsInput,
    ListAllProductsInput,
    CheckStockInput,
    BuyProductInput,
    DeleteProductInput,
)
import database as db

@tool("list_all_products", args_schema=ListAllProductsInput)
def list_all_products() -> str:
    """Lists all products and their prices across the entire catalog. Use this when the user asks to see everything, find the most expensive or cheapest items, or compare prices."""
    rows = db.get_all_products()
    if not rows:
        return "The store catalog is currently empty."
    results = [f"[ID: {r[0]}] {r[1]} ({r[2]}) - ${r[3]:.2f}" for r in rows]
    return "All catalog products:\n" + "\n".join(results)

@tool("search_products", args_schema=SearchProductsInput)
def search_products(query: str) -> str:
  """Searches products by keyword in name or category."""
  clean_query = str(query).strip().lower()

  if clean_query in [
      "details",
      "detail",
      "info",
      "information",
      "all",
      "catalog",
      "products",
      "everything",
  ]:
    return list_all_products()

  rows = db.query_products_by_keyword(clean_query)
  if not rows:
    return f"No products found matching keyword '{query}'."
  results = []
  for r in rows:
    pid, name, cat, price, stock = r[0], r[1], r[2], r[3], r[4]
    results.append(
        f"• Product: {name} (ID: {pid})\n  Category: {cat}\n  Price:"
        f" ${price:.2f}\n  Availability: {stock} units in stock"
    )

  return f"Found {len(rows)} product(s):\n\n" + "\n\n".join(results)

@tool("check_stock", args_schema=CheckStockInput)
def check_stock(product_ids: Optional[Any] = None, **kwargs) -> str:
  """Checks stock levels for given product ID(s), or scans the entire catalog if none are provided."""
  raw_input = (
      product_ids
      if product_ids is not None
      else kwargs.get("product_id") or kwargs.get("id")
  )

  clean_ids = []
  if raw_input is not None:
    digits = re.findall(r"\d+", str(raw_input))
    for d in digits:
      clean_ids.append(int(d))
  clean_ids = sorted(list(set(clean_ids)))

  if not clean_ids:
    all_items = db.get_all_products()
    if not all_items:
      return "The store catalog is currently empty."

    out_of_stock = []
    in_stock = []

    for row in all_items:
      pid, name, category, price = row
      stock_rows = db.get_products_by_ids([pid])
      stock = stock_rows[0][2] if stock_rows else 0

      if stock == 0:
        out_of_stock.append(f"'{name}' (ID: {pid})")
      else:
        in_stock.append(f"'{name}' (ID: {pid}, stock: {stock})")

    lines = [
        f"Inventory Status: {len(out_of_stock)} item(s) are currently out of"
        " stock."
    ]
    if out_of_stock:
      lines.append(f"Out of stock items: {', '.join(out_of_stock)}")
    else:
      lines.append("All items currently have stock available.")
    lines.append(f"In-stock items: {', '.join(in_stock)}")

    return "\n".join(lines)

  rows = db.get_products_by_ids(clean_ids)
  if not rows:
    return (
        f"Database error: None of the products {clean_ids} exist in the"
        " catalog."
    )

  results = []
  for r in rows:
    pid, name, stock, price = r
    status = f"{stock} units in stock" if stock > 0 else "OUT OF STOCK"
    results.append(f"[ID: {pid}] {name} | Status: {status}")

  return "\n".join(results)

@tool("delete_product", args_schema=DeleteProductInput)
def delete_product(product_id: Union[int, str]) -> str:
  """Deletes a product from the database catalog (Admin only)."""
  try:
    pid = int(product_id)
  except (ValueError, TypeError):
    return f"Invalid product ID: {product_id}"

  success = db.remove_product_by_id(pid)
  if success:
    return f"Successfully deleted product ID {pid} from the database."
  return f"Product ID {pid} could not be found or removed."

@tool("buy_product", args_schema=BuyProductInput)
def buy_product(product_id: int, quantity: int = 1) -> str:
  """Purchases a specified quantity of a product, reducing its inventory stock."""
  success, message = db.buy_product_from_db(
      product_id=int(product_id), quantity=int(quantity)
  )
  return message

TOOL_REGISTRY = {
    "list_all_products": list_all_products,
    "search_products": search_products,
    "check_stock": check_stock,
    "buy_product": buy_product,
    "delete_product": delete_product,
}