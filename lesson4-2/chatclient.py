import os
import sys
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential

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


def build_client() -> tuple[ChatCompletionsClient, str]:
    endpoint = get_required("AZURE_FOUNDRY_ENDPOINT")
    api_key = get_required("AZURE_FOUNDRY_API_KEY")
    model = get_required("AZURE_FOUNDRY_MODEL")
    api_version = os.getenv("AZURE_FOUNDRY_API_VERSION", "2024-05-01-preview")
    client = ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
        api_version=api_version,
    )
    return client, model


def main():
    load_config()
    client, model = build_client()

    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
    conversation = [SystemMessage(content=system_prompt)]

    print(f"Chat client connected to model: {model}")
    print("Type your message and press Enter. Press Ctrl+C to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        conversation.append(UserMessage(content=user_input))

        try:
            response = client.complete(
                messages=conversation,
                model=model,
            )
            assistant_message = response.choices[0].message.content
            conversation.append(AssistantMessage(content=assistant_message))
            print(f"\nAssistant: {assistant_message}\n")
        except Exception as e:
            print(f"\nError calling model: {e}\n")
            conversation.pop()


if __name__ == "__main__":
    main()
