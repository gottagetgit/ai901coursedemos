import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
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


def build_clients():
    endpoint = get_required("AZURE_FOUNDRY_ENDPOINT")
    agent_name = get_required("AZURE_FOUNDRY_AGENT_NAME")
    agent_version = get_required("AZURE_FOUNDRY_AGENT_VERSION")

    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )
    openai_client = project_client.get_openai_client()
    return openai_client, agent_name, agent_version


def main():
    load_config()
    openai_client, agent_name, agent_version = build_clients()

    print(f"Chat client connected to agent: {agent_name} v{agent_version}")
    print("Type your message and press Enter. Press Ctrl+C to exit.\n")

    agent_reference = {
        "agent_reference": {
            "name": agent_name,
            "version": agent_version,
            "type": "agent_reference",
        }
    }
    previous_response_id = None

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        try:
            kwargs = {
                "input": [{"role": "user", "content": user_input}],
                "extra_body": agent_reference,
            }
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id

            response = openai_client.responses.create(**kwargs)
            previous_response_id = response.id

            print(f"\nAssistant: {response.output_text}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
