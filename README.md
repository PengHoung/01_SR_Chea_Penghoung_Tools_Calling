# Safe Shopping & Inventory Management Agent

An interactive store assistant and inventory management agent powered by llama3.2:3b and an SQLite database (shop.db). The system incorporates Role-Based Access Control (RBAC), structured Pydantic tool schemas, execution loop limits, and deterministic output grounding to prevent hallucinations and maintain factual consistency.

---

## 1. Project Overview

The Safe Shopping Agent is a local AI assistant that handles catalog browsing, stock verification, and order processing for an electronics and accessories retail store.

Key capabilities include:
- Customer Mode: Enables customers to list catalog items, search products by keyword, check real-time stock levels, and execute purchases with direct stock deductions in SQLite.
- Admin Mode: Enables store managers to perform full-catalog stock audits, identify out-of-stock items, and permanently delete products.
- Deterministic Grounding: Bypasses small-model attention drift and eliminates placeholder hallucinations (Product A, Product 1, or invented hardware specs) by linking responses directly to verified database observations.

---

## 2. Available Tools

The agent interacts with the SQLite database through modular tools defined in tools.py and validated by schemas in schemas.py:

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| list_all_products | None ({}) | Scans the SQLite database and returns the full product catalog with ID, name, category, and price. |
| search_products | query: str | Queries products by keyword across names and categories, returning product details and current stock availability. |
| check_stock | product_ids: Optional[Any] | Checks stock levels for given product IDs. If called with empty arguments ({}), it scans the entire store and returns total counts and names of in-stock and out-of-stock items. |
| buy_product | product_id: int, quantity: int = 1 | Checks stock availability, decrements quantity directly in SQLite, and generates an official purchase confirmation receipt with remaining stock. |
| delete_product | product_id: int | Permanently deletes a product from the database catalog. Restricted strictly to the Admin role. |

---

## 3. Agent Loop

The agent runs on an augmented ReAct (Reason + Act) loop managed by SafeShoppingAgent.run() in agent.py:

User Input
    |
    v
[1. DECISION] --> Model evaluates prompt, role permissions, and context
    |             to generate conversational text or invoke a tool call.
    v
[2. ACTION]   --> SafetyHarness.execute_safely() validates:
    |             - Loop count (checks circuit breaker limit)
    |             - User role permissions (Customer vs. Admin)
    |             - Input arguments against Pydantic schemas
    |             Then dispatches execution to database.py.
    v
[3. OBSERVATION] > Tool output returns from SQLite as a ToolMessage
    |             and is appended to conversation history.
    v
[4. SYNTHESIS] --> Model processes observation to deliver the final response.
                  Deterministic synthesis ensures purchase receipts and
                  catalog listings are displayed accurately.

---

## 4. Permission Rules

The application uses an allowlist mechanism in harness.py to enforce Role-Based Access Control (RBAC):

                       +------------------+
                       |   Active Role    |
                       +--------+---------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
          [CUSTOMER]                          [ADMIN]
     - list_all_products                 - list_all_products
     - search_products                   - search_products
     - check_stock                       - check_stock
     - buy_product                       - delete_product

- CUSTOMER Role: Restricted to non-destructive actions (list_all_products, search_products, check_stock, buy_product). Calls to administrative tools are blocked before execution:
  [PERMISSION DENIED] Role 'customer' is not authorized to use tool 'delete_product'.
- ADMIN Role: Retains privileges for auditing inventory, reviewing stockouts, and executing catalog management tasks (delete_product).
- Role Switching: The user can toggle between roles dynamically in the interactive console using the switch command.

---

## 5. Safety & Guardrails

To run local small language models reliably without runtime failures, three protective layers are implemented:

1. Loop Limit Circuit Breaker:
   SafetyHarness tracks the tool execution depth per turn (MAX_TURNS). If the agent enters an unresolvable tool invocation loop, the harness interrupts execution with:
   [Safety Harness]: Maximum loop limit reached.
2. Defensive Error Handling & Schema Validation:
   Database operations in database.py return structured status tuples (bool, message) instead of raising unhandled SQL exceptions. Input schemas in schemas.py sanitize parameters using regex, safely handling integers, lists, or empty inputs (args: {}).
3. Sliding Context Window (Anti-Drift):
   agent.py trims multi-turn history past 7 messages, retaining the initial SystemMessage and the 6 most recent messages. This prevents context pollution and stops deleted items from affecting subsequent queries.

---

## 6. Example Runs

### Example 1: Store-Wide Stock Inspection

[CUSTOMER] You: which items that out of stock?

   [Model Decision] -> Invoking tool: 'check_stock' with args: {'product_ids': ''}
   [Tool Output]    -> Inventory Status: 2 item(s) are currently out of stock.
Out of stock items: 'Office Ultrabook Laptop' (ID: 2), 'Mechanical RGB Keyboard' (ID: 4)
In-stock items: 'Pro Gaming Laptop' (ID: 1, stock: 3), 'Wireless Ergonomic Mouse' (ID: 3, stock: 2), 'USB-C Fast Charger 65W' (ID: 5, stock: 20)

Agent: The items 'Office Ultrabook Laptop' (ID: 2) and 'Mechanical RGB Keyboard' (ID: 4) are currently out of stock.


### Example 2: Product Purchase

[CUSTOMER] You: I want to buy 1 Wireless Ergonomic Mouse

   [Model Decision] -> Invoking tool: 'buy_product' with args: {'product_id': 3, 'quantity': 1}
   [Tool Output]    -> PURCHASE CONFIRMED: 1x 'Wireless Ergonomic Mouse' bought for $55.29. The new updated stock in the database is EXACTLY 3 units.

Agent: Purchase Processed:

PURCHASE CONFIRMED: 1x 'Wireless Ergonomic Mouse' bought for $55.29. The new updated stock in the database is EXACTLY 3 units.