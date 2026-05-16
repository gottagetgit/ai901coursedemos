import os
import sys
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures

CONFIG_FILE = "config.env"

# Image files we expect to find next to this script. Put your own pictures
# here with these names before running.
SINGLE_OBJECT_IMAGE = "example1.png"   # one main object to identify
MULTI_OBJECT_IMAGE = "example2.png"    # several objects to detect + locate
OCR_IMAGE = "example3.png"             # an image containing text to read


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


def build_client() -> ImageAnalysisClient:
    endpoint = get_required("AZURE_VISION_ENDPOINT").rstrip("/")
    key = get_required("AZURE_VISION_KEY")
    return ImageAnalysisClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )


def read_image(path: str) -> bytes:
    if not os.path.exists(path):
        print(f"Error: image file '{path}' not found next to this script.")
        sys.exit(1)
    with open(path, "rb") as f:
        return f.read()


def identify_single_object(client: ImageAnalysisClient):
    print(f"=== Identifying the main object in '{SINGLE_OBJECT_IMAGE}' ===")
    image = read_image(SINGLE_OBJECT_IMAGE)
    result = client.analyze(
        image_data=image,
        visual_features=[VisualFeatures.CAPTION, VisualFeatures.TAGS],
    )

    if result.caption is not None:
        print(
            f"  It looks like: {result.caption.text} "
            f"(confidence {result.caption.confidence:.2f})"
        )

    if result.tags is not None:
        print("  Top tags:")
        for tag in result.tags.list[:5]:
            print(f"    - {tag.name} (confidence {tag.confidence:.2f})")
    print()


def detect_objects(client: ImageAnalysisClient):
    print(f"=== Detecting all objects in '{MULTI_OBJECT_IMAGE}' ===")
    image = read_image(MULTI_OBJECT_IMAGE)
    result = client.analyze(
        image_data=image,
        visual_features=[VisualFeatures.OBJECTS],
    )

    if result.objects is None or not result.objects.list:
        print("  No objects detected.")
        print()
        return

    for obj in result.objects.list:
        name = obj.tags[0].name if obj.tags else "object"
        confidence = obj.tags[0].confidence if obj.tags else 0.0
        box = obj.bounding_box
        print(
            f"  - {name} (confidence {confidence:.2f}) "
            f"at x={box.x}, y={box.y}, width={box.width}, height={box.height}"
        )
    print()


def extract_text(client: ImageAnalysisClient):
    print(f"=== Extracting text (OCR) from '{OCR_IMAGE}' ===")
    image = read_image(OCR_IMAGE)
    result = client.analyze(
        image_data=image,
        visual_features=[VisualFeatures.READ],
    )

    if result.read is None or not result.read.blocks:
        print("  No text found in the image.")
        print()
        return

    for block in result.read.blocks:
        for line in block.lines:
            print(f"  {line.text}")
    print()


def main():
    load_config()
    client = build_client()

    try:
        identify_single_object(client)
        detect_objects(client)
        extract_text(client)
    except AzureError as e:
        print(f"\nError calling the Azure AI Vision service: {e}")
        print("Double-check AZURE_VISION_ENDPOINT and AZURE_VISION_KEY in config.env.")
        sys.exit(1)


if __name__ == "__main__":
    main()
