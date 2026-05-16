import os
import sys
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AudioVisualContent

CONFIG_FILE = "config.env"

# Files we expect to find next to this script. Drop your own samples in with
# these names before running.
INVOICE_PDF = "example1.pdf"   # an invoice as a PDF document
INVOICE_IMAGE = "example2.jpg"  # an invoice as an image
AUDIO_FILE = "example3.mp3"     # a recorded course lesson
VTT_OUTPUT = "example3.vtt"     # subtitles we generate from the audio

# Content Understanding GA API version.
API_VERSION = "2025-11-01"

# Prebuilt analyzers provided by the service (no training required).
# prebuilt-invoice extracts structured invoice fields from PDFs *and* images.
# prebuilt-callCenter transcribes speech into timed phrases (with speakers)
# and produces a summary -- this is the analyzer Microsoft's own samples use
# for audio, and it returns the transcript inline in the result.
INVOICE_ANALYZER = "prebuilt-invoice"
AUDIO_ANALYZER = "prebuilt-callCenter"


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


def build_client() -> ContentUnderstandingClient:
    endpoint = get_required("AZURE_CONTENT_UNDERSTANDING_ENDPOINT").rstrip("/")
    key = get_required("AZURE_CONTENT_UNDERSTANDING_KEY")
    return ContentUnderstandingClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
        api_version=API_VERSION,
    )


def read_file(path: str) -> bytes:
    if not os.path.exists(path):
        print(f"Error: file '{path}' not found next to this script.")
        sys.exit(1)
    with open(path, "rb") as f:
        return f.read()


def analyze_file(client: ContentUnderstandingClient, analyzer_id: str, path: str):
    """Send a local file to a prebuilt analyzer and wait for the result.

    Content Understanding analysis is a long-running operation. The SDK's
    begin_analyze_binary() returns a poller; calling .result() blocks
    until the service is done and hands back an AnalysisResult.
    """
    file_bytes = read_file(path)
    poller = client.begin_analyze_binary(analyzer_id, binary_input=file_bytes)
    return poller.result()


def print_invoice_fields(label: str, result):
    print(f"=== Extracted invoice data from '{label}' ===")
    if not result.contents:
        print("  No content returned.")
        print()
        return

    fields = result.contents[0].fields or {}
    if not fields:
        print("  No fields extracted.")
        print()
        return

    for name, field in fields.items():
        # Every field exposes a generic .value regardless of its type
        # (string, number, date, ...).
        if field.value not in (None, "", [], {}):
            print(f"  {name}: {field.value}")
    print()


def format_timestamp(ms: int) -> str:
    """Convert milliseconds to a WebVTT timestamp: HH:MM:SS.mmm"""
    total_seconds, milliseconds = divmod(int(ms), 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def get_audio_content(result):
    for content in result.contents or []:
        # The model is dict-like; match on the 'kind' discriminator rather
        # than isinstance, and also accept anything carrying a transcript.
        if isinstance(content, AudioVisualContent):
            return content
        if str(content.get("kind", "")) == "audioVisual":
            return content
        if content.get("transcriptPhrases") or getattr(
            content, "transcript_phrases", None
        ):
            return content
    return None


def dump_contents(result):
    """Print what the service actually returned so we can see its shape."""
    import json

    contents = result.contents or []
    print(f"  (diagnostic) analyzer returned {len(contents)} content item(s)")
    print(f"  (diagnostic) warnings: {result.warnings}")
    try:
        print("  (diagnostic) full result:")
        print(json.dumps(result.as_dict(), indent=2, default=str))
    except Exception as e:
        print(f"  (diagnostic) could not serialize result: {e}")


def write_vtt(audio, out_path: str):
    phrases = audio.transcript_phrases or []
    if not phrases:
        print("  No transcript phrases returned; cannot build subtitles.")
        return

    lines = ["WEBVTT", ""]
    for phrase in phrases:
        start = format_timestamp(phrase.start_time_ms)
        end = format_timestamp(phrase.end_time_ms)
        text = phrase.text or ""
        cue_text = f"<v {phrase.speaker}>{text}" if phrase.speaker else text
        lines.append(f"{start} --> {end}")
        lines.append(cue_text)
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Wrote {len(phrases)} subtitle cues to '{out_path}'")


def print_audio_summary(audio):
    fields = audio.fields or {}
    summary = fields.get("Summary")
    if summary and summary.value:
        print(f"  Summary: {summary.value}")


def main():
    load_config()
    client = build_client()

    try:
        # 1. Invoice as a PDF document.
        pdf_result = analyze_file(client, INVOICE_ANALYZER, INVOICE_PDF)
        print_invoice_fields(INVOICE_PDF, pdf_result)

        # 2. Invoice as an image.
        img_result = analyze_file(client, INVOICE_ANALYZER, INVOICE_IMAGE)
        print_invoice_fields(INVOICE_IMAGE, img_result)

        # 3. Recorded course lesson -> transcript + subtitles.
        print(f"=== Transcribing audio '{AUDIO_FILE}' ===")
        audio_result = analyze_file(client, AUDIO_ANALYZER, AUDIO_FILE)
        audio = get_audio_content(audio_result)
        if audio is None:
            print("  No audio content returned.")
            dump_contents(audio_result)
        else:
            print_audio_summary(audio)
            write_vtt(audio, VTT_OUTPUT)
        print()
    except AzureError as e:
        print(f"\nError calling Azure AI Content Understanding: {e}")
        print("Check AZURE_CONTENT_UNDERSTANDING_ENDPOINT / _KEY in config.env.")
        sys.exit(1)


if __name__ == "__main__":
    main()
