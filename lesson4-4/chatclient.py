import os
import sys
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

CONFIG_FILE = "config.env"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file '{CONFIG_FILE}' not found.")
        print("Copy config.env.example to config.env and fill in your values.")
        sys.exit(1)
    load_dotenv(CONFIG_FILE)


def get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f"Error: '{key}' is not set in {CONFIG_FILE}")
        sys.exit(1)
    return value


def resolve_agent_id(client: AIProjectClient, agent_name: str) -> str:
    for agent in client.agents.list_agents():
        if agent.name == agent_name:
            return agent.id
    print(f"Error: no agent named '{agent_name}' found in this project.")
    sys.exit(1)


def build_client() -> tuple[AIProjectClient, str, str]:
    endpoint = get_required("AZURE_FOUNDRY_ENDPOINT")
    agent_name = get_required("AZURE_FOUNDRY_AGENT_NAME")
    agent_version = get_required("AZURE_FOUNDRY_AGENT_VERSION")
    client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )
    agent_id = resolve_agent_id(client, agent_name)
    return client, agent_name, agent_version, agent_id


def main():
    load_config()
    client, agent_name, agent_version, agent_id = build_client()

    thread = client.agents.create_thread()
    print(f"Chat client connected to agent: {agent_name} v{agent_version}")
    print("Type your message and press Enter. Press Ctrl+C to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        try:
            client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_input,
            )
            run = client.agents.create_and_process_run(
                thread_id=thread.id,
                assistant_id=agent_id,
            )
            if run.status == "failed":
                print(f"\nError: agent run failed — {run.last_error}\n")
                continue

            messages = client.agents.list_messages(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant":
                    print(f"\nAssistant: {msg.content[0].text.value}\n")
                    break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
