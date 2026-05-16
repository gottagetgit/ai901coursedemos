import os
import sys
import time
from dotenv import load_dotenv
import requests

CONFIG_FILE = "config.env"

# Content Understanding GA API version.
API_VERSION = "2025-11-01"

# Files we expect to find next to this script. Drop your own samples in with
# these names before running.
INVOICE_PDF = "example1.pdf"   # an invoice as a PDF document
INVOICE_IMAGE = "example2.png"  # an invoice as an image
AUDIO_FILE = "example3.mp3"     # a recorded course lesson
VTT_OUTPUT = "example3.vtt"     # subtitles we generate from the audio

# Prebuilt analyzers provided by the service (no training required).
# prebuilt-invoice extracts structured invoice fields from PDFs *and* images.
# prebuilt-audioSearch returns a transcript (with timing) and a summary.
INVOICE_ANALYZER = "prebuilt-invoice"
AUDIO_ANALYZER = "prebuilt-audioSearch"

# How long to wait for an analysis to finish before giving up.
POLL_INTERVAL_SECONDS = 2
POLL_MAX_ATTEMPTS = 60


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


def read_file(path: str) -> bytes:
    if not os.path.exists(path):
        print(f"Error: file '{path}' not found next to this script.")
        sys.exit(1)
    with open(path, "rb") as f:
        return f.read()


def analyze_file(endpoint: str, key: str, analyzer_id: str, path: str) -> dict:
    """Send a local file to a prebuilt analyzer and wait for the result.

    Content Understanding is asynchronous: the first POST returns a
    202 with an Operation-Location header; we then poll that URL until
    the status is 'succeeded'.
    """
    file_bytes = read_file(path)

    analyze_url = (
        f"{endpoint}/contentunderstanding/analyzers/"
        f"{analyzer_id}:analyzeBinary?api-version={API_VERSION}"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream",
    }

    response = requests.post(analyze_url, headers=headers, data=file_bytes)
    response.raise_for_status()

    operation_location = response.headers.get("operation-location")
    if not operation_location:
        raise RuntimeError("Service did not return an Operation-Location header.")

    poll_headers = {"Ocp-Apim-Subscription-Key": key}
    for _ in range(POLL_MAX_ATTEMPTS):
        poll = requests.get(operation_location, headers=poll_headers)
        poll.raise_for_status()
        body = poll.json()
        status = body.get("status", "").lower()
        if status == "succeeded":
            return body
        if status == "failed":
            raise RuntimeError(f"Analysis failed: {body}")
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Timed out waiting for the analysis to finish.")


def field_value(field: dict):
    """Pull the human-readable value out of a Content Understanding field.

    Each field looks like {"type": "string", "valueString": "Contoso"} —
    the value key always starts with 'value'.
    """
    for name, value in field.items():
        if name.startswith("value"):
            return value
    return None


def print_invoice_fields(label: str, result: dict):
    print(f"=== Extracted invoice data from '{label}' ===")
    contents = result.get("result", {}).get("contents", [])
    if not contents:
        print("  No content returned.")
        print()
        return

    fields = contents[0].get("fields", {})
    if not fields:
        print("  No fields extracted.")
        print()
        return

    for name, field in fields.items():
        value = field_value(field)
        if value not in (None, "", [], {}):
            print(f"  {name}: {value}")
    print()


def format_timestamp(ms: int) -> str:
    """Convert milliseconds to a WebVTT timestamp: HH:MM:SS.mmm"""
    total_seconds, milliseconds = divmod(int(ms), 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def find_transcript_phrases(result: dict) -> list:
    for content in result.get("result", {}).get("contents", []):
        phrases = content.get("transcriptPhrases")
        if phrases:
            return phrases
    return []


def write_vtt(result: dict, out_path: str):
    phrases = find_transcript_phrases(result)
    if not phrases:
        print("  No transcript phrases returned; cannot build subtitles.")
        return

    lines = ["WEBVTT", ""]
    for phrase in phrases:
        start = format_timestamp(phrase.get("startTimeMs", 0))
        end = format_timestamp(phrase.get("endTimeMs", 0))
        speaker = phrase.get("speaker")
        text = phrase.get("text", "")
        cue_text = f"<v {speaker}>{text}" if speaker else text
        lines.append(f"{start} --> {end}")
        lines.append(cue_text)
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Wrote {len(phrases)} subtitle cues to '{out_path}'")


def print_audio_summary(result: dict):
    for content in result.get("result", {}).get("contents", []):
        fields = content.get("fields", {})
        summary = fields.get("Summary")
        if summary:
            print(f"  Summary: {field_value(summary)}")
            return


def main():
    load_config()
    endpoint = get_required("AZURE_CONTENT_UNDERSTANDING_ENDPOINT").rstrip("/")
    key = get_required("AZURE_CONTENT_UNDERSTANDING_KEY")

    try:
        # 1. Invoice as a PDF document.
        pdf_result = analyze_file(endpoint, key, INVOICE_ANALYZER, INVOICE_PDF)
        print_invoice_fields(INVOICE_PDF, pdf_result)

        # 2. Invoice as an image.
        img_result = analyze_file(endpoint, key, INVOICE_ANALYZER, INVOICE_IMAGE)
        print_invoice_fields(INVOICE_IMAGE, img_result)

        # 3. Recorded course lesson -> transcript + subtitles.
        print(f"=== Transcribing audio '{AUDIO_FILE}' ===")
        audio_result = analyze_file(endpoint, key, AUDIO_ANALYZER, AUDIO_FILE)
        print_audio_summary(audio_result)
        write_vtt(audio_result, VTT_OUTPUT)
        print()
    except requests.HTTPError as e:
        print(f"\nError calling Azure AI Content Understanding: {e}")
        print("Check AZURE_CONTENT_UNDERSTANDING_ENDPOINT / _KEY in config.env.")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"\nNetwork error calling Azure AI Content Understanding: {e}")
        print("Check AZURE_CONTENT_UNDERSTANDING_ENDPOINT in config.env.")
        sys.exit(1)


if __name__ == "__main__":
    main()
