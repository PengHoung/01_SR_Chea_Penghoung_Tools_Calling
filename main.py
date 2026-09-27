from langchain_ollama import ChatOllama
from tools import TOOL_REGISTRY
from harness import SafetyHarness
from agent import SafeShoppingAgent


def main():
    print("=" * 60)
    print("      SAFE SHOPPING AGENT - INTERACTIVE CONSOLE")
    print("=" * 60)

    print("Select your active role:")
    print("  1) Customer (can search & check stock)")
    print("  2) Admin (can search, check stock, and delete products)")
    role_choice = input("Enter choice (1/2, default 1): ").strip()
    role = "admin" if role_choice == "2" else "customer"

    print("\nLoading local model 'llama3.2:3b'...")
    llm = ChatOllama(model="llama3.2:3b", temperature=0)
    llm_with_tools = llm.bind_tools(list(TOOL_REGISTRY.values()))

    harness = SafetyHarness(role=role, max_iterations=5)
    agent = SafeShoppingAgent(llm_with_tools=llm_with_tools, harness=harness)

    print(f"Agent ready. Active Role: [{role.upper()}]")
    print("Commands: type 'switch' to toggle role, 'exit' to quit.\n")

    while True:
        try:
            user_input = input(f"[{agent.harness.role.upper()}] You: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break

            if user_input.lower() == "switch":
                new_role = "admin" if agent.harness.role == "customer" else "customer"
                agent.harness.role = new_role
                print(f"Switched role to: [{new_role.upper()}]")
                continue

            if user_input.isdigit():
                print(
                    f"\nAgent: You entered '{user_input}'. Did you mean to perform an action on product ID {user_input}?\n"
                    f"Please specify your request (e.g., 'delete product {user_input}' or 'check stock for item {user_input}').\n"
                )
                print("-" * 60)
                continue

            answer = agent.run(user_input)
            print(f"\nAgent: {answer}\n")
            print("-" * 60)

        except KeyboardInterrupt:
            print("\nExiting session.")
            break


if __name__ == "__main__":
    main()