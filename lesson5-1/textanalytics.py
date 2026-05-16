import os
import sys
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.ai.textanalytics import TextAnalyticsClient

CONFIG_FILE = "config.env"

# A sample article we will analyze. In a real app this text would come from
# a user, a file, a database, etc.
SAMPLE_TEXT = (
    "Contoso Travel launched its new mobile app in Seattle last March. "
    "The app helps travelers book flights, hotels, and rental cars in one place. "
    "CEO Maria Gonzalez said the company saw a forty percent increase in bookings "
    "within the first month. Customers praised the simple design and fast support. "
    "Contoso plans to expand the service to Europe and Asia by the end of the year."
)


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


def build_client() -> TextAnalyticsClient:
    endpoint = get_required("AZURE_LANGUAGE_ENDPOINT").rstrip("/")
    key = get_required("AZURE_LANGUAGE_KEY")
    return TextAnalyticsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )


def show_summary(client: TextAnalyticsClient, documents: list[str]):
    print("=== Extractive Summarization ===")
    # begin_extract_summary is a long-running operation: it returns a poller
    # that we wait on with .result().
    poller = client.begin_extract_summary(documents)
    for result in poller.result():
        if result.is_error:
            print(f"Error: {result.error.message}")
            continue
        # Sentences come back ranked; print them in their original order.
        for sentence in sorted(result.sentences, key=lambda s: s.offset):
            print(f"  - {sentence.text}")
    print()


def show_entities(client: TextAnalyticsClient, documents: list[str]):
    print("=== Named Entity Recognition ===")
    for result in client.recognize_entities(documents):
        if result.is_error:
            print(f"Error: {result.error.message}")
            continue
        for entity in result.entities:
            print(
                f"  - {entity.text} "
                f"({entity.category}, confidence {entity.confidence_score:.2f})"
            )
    print()


def show_key_phrases(client: TextAnalyticsClient, documents: list[str]):
    print("=== Key Phrase Extraction ===")
    for result in client.extract_key_phrases(documents):
        if result.is_error:
            print(f"Error: {result.error.message}")
            continue
        for phrase in result.key_phrases:
            print(f"  - {phrase}")
    print()


def main():
    load_config()
    client = build_client()

    documents = [SAMPLE_TEXT]

    print("Analyzing the following text:\n")
    print(SAMPLE_TEXT)
    print()

    try:
        show_summary(client, documents)
        show_entities(client, documents)
        show_key_phrases(client, documents)
    except AzureError as e:
        print(f"\nError calling the Azure AI Language service: {e}")
        print("Double-check AZURE_LANGUAGE_ENDPOINT and AZURE_LANGUAGE_KEY in config.env.")
        sys.exit(1)


if __name__ == "__main__":
    main()
