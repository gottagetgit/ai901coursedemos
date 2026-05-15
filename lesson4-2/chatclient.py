import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

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


def build_client() -> tuple[OpenAI, str]:
    endpoint = get_required("AZURE_FOUNDRY_ENDPOINT").rstrip("/")
    api_key = get_required("AZURE_FOUNDRY_API_KEY")
    model = get_required("AZURE_FOUNDRY_MODEL")
    client = OpenAI(
        base_url=f"{endpoint}",
        api_key=api_key,
    )
    return client, model


def main():
    load_config()
    client, model = build_client()

    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
    conversation = [{"role": "system", "content": system_prompt}]

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

        conversation.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=model,
                messages=conversation,
            )
            assistant_message = response.choices[0].message.content
            conversation.append({"role": "assistant", "content": assistant_message})
            print(f"\nAssistant: {assistant_message}\n")
        except Exception as e:
            print(f"\nError calling model: {e}\n")
            conversation.pop()


if __name__ == "__main__":
    main()



