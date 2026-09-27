from harness import SafetyHarness
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

SYSTEM_INSTRUCTION = """### ROLE & CAPABILITIES
You are an automated store assistant connected directly to an SQLite inventory database.
You operate under two roles: [CUSTOMER] (browse, search, check stock, purchase) and [ADMIN] (catalog inspection, stock checks, deleting products).

### PURCHASE & TOOL-CHAINING RULES
1. MANDATORY PURCHASE SEQUENCE:
   - When a user asks to buy an item by name (e.g., 'buy Wireless Ergonomic Mouse'):
     * STEP 1: You MUST FIRST invoke 'search_products' or 'check_stock' to locate the product and verify its real numeric ID and stock availability.
     * STEP 2: Only after receiving a valid product ID and confirming stock > 0 may you invoke 'buy_product'.
2. NEVER GUESS OR INVENT PRODUCT IDs:
   - Never call 'buy_product' with an invented ID (such as 12345, 999, etc.). The ID must come directly from a prior tool observation.
3. If an item is out of stock (0 units), inform the user and DO NOT call 'buy_product'.

### DATABASE GROUNDING & INVENTORY CONSTRAINTS
1. FACTUAL DATA ONLY: Only report product information, stock counts, and prices returned by tool observations.
2. NO PLACEHOLDERS: NEVER invent placeholder labels such as 'Product A', 'Product B', 'Product 1', or 'Product 2'. Always refer to items by their real names and IDs from tool observations.
3. HARD BOUNDARY: The database contains ONLY the specific products returned by the catalog tools. NEVER hallucinate extra items (e.g., Smart TVs, Gaming Consoles, or IDs 7–10).
4. NO SPEC SPECULATION: Do NOT invent hardware specifications (CPU, GPU, RAM, screen size, battery life, ports). Report only: Product Name, ID, Category, Price, and Stock Status.

### TOOL DISPATCH RULES
1. INVENTORY & STOCK QUERIES:
   - When asked about stock levels, availability, or 'which/how many items are out of stock', invoke 'check_stock' with args: {}.
   - Never assume an item is out of stock without a tool observation.
2. PRODUCT SEARCH & DETAILS:
   - When asked for details or searching for a product, invoke 'search_products' or 'check_stock'.
3. PURCHASES:
   - When the user wants to buy an item, invoke 'buy_product'. Always convey the confirmed receipt and final stock verbatim from the tool observation. Do NOT perform mental subtraction on the remaining stock.
4. ADMIN ACTIONS:
   - Deletions must only be performed via 'delete_product' when in the [ADMIN] role.

### RESPONSE FORMAT
- When tools run, formulate a concise, natural response based strictly on the tool observations.
- For conversational remarks or greetings, reply politely in one short sentence without invoking tools."""

class SafeShoppingAgent:

  def __init__(self, llm_with_tools, harness: SafetyHarness):
    self.llm = llm_with_tools
    self.harness = harness
    self.history = [SystemMessage(content=SYSTEM_INSTRUCTION)]

  def reset_context(self):
    self.history = [self.history[0]]

  def run(self, user_prompt: str) -> str:
      self.harness.reset_limit()
      clean_input = user_prompt.strip().lower().rstrip("!.")
      if clean_input in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening",
                         "good night"]:
          return "Hello! Welcome to our store. How can I assist you with our catalog today?"

      if len(self.history) > 7:
          self.history = [self.history[0]] + self.history[-6:]

      self.history.append(HumanMessage(content=user_prompt))
      turn_tool_outputs = []
      executed_tools = []

      while True:
          if not self.harness.check_loop_limit():
              msg = "[Safety Harness]: Maximum loop limit reached."
              print(msg)
              return msg

          response = self.llm.invoke(self.history)
          self.history.append(response)
          if not response.tool_calls:
              content = response.content.strip()
              user_wants_buy = any(kw in user_prompt.lower() for kw in ["buy", "purchase", "order"])
              if user_wants_buy and "buy_product" not in executed_tools:
                  combined_outputs = " ".join(turn_tool_outputs)
                  if "out of stock" in combined_outputs.lower() or "stock: 0" in combined_outputs.lower():
                      return "I checked our inventory, but that item is currently out of stock. A purchase could not be completed."

                  self.history.append(HumanMessage(
                      content="Item is available. Immediately call the 'buy_product' tool now. Do NOT reply in text."))
                  continue

              if turn_tool_outputs:
                  joined_obs = "\n\n".join(turn_tool_outputs)
                  lowered = content.lower()

                  if len(content) < 15 or "check the stock" in lowered or lowered in ["hi", "hello", "hey"]:
                      if "buy_product" in executed_tools:
                          return f"Order Confirmation:\n\n{joined_obs}"
                      return joined_obs

                  if "buy_product" in executed_tools:
                      return f"{content}\n\n{joined_obs}"

                  return content

              return response.content


          for call in response.tool_calls:
              tool_id = call["id"]
              tool_name = call["name"]
              tool_args = call["args"]
              executed_tools.append(tool_name)

              print(f"\n   [Model Decision] -> Invoking tool: '{tool_name}' with args: {tool_args}")
              observation = self.harness.execute_safely(tool_name, tool_args)
              print(f"   [Tool Output]    -> {observation}\n")

              turn_tool_outputs.append(str(observation))

              self.history.append(
                  ToolMessage(
                      tool_call_id=tool_id,
                      name=tool_name,
                      content=str(observation)
                  )
              )

          user_wants_buy = any(kw in user_prompt.lower() for kw in ["buy", "purchase", "order"])
          if user_wants_buy and "buy_product" not in executed_tools:
              self.history.append(
                  HumanMessage(
                      content="Stock check complete. Now invoke the 'buy_product' tool to finish the purchase. Do NOT provide an explanation in text."
                  )
              )