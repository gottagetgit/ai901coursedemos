import os
import sys
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

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


def main():
    load_config()
    endpoint = get_required("AZURE_SPEECH_ENDPOINT")
    speech_key = get_required("AZURE_SPEECH_KEY")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=endpoint)
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )

    def on_recognizing(evt):
        print(f"\r... {evt.result.text}", end="", flush=True)

    def on_recognized(evt):
        if evt.result.text:
            print(f"\r>>> {evt.result.text}")

    recognizer.recognizing.connect(on_recognizing)
    recognizer.recognized.connect(on_recognized)

    recognizer.start_continuous_recognition()
    print("Listening... speak into the microphone. Press Enter to stop.")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        recognizer.stop_continuous_recognition()
        print("\nStopped.")


if __name__ == "__main__":
    main()
