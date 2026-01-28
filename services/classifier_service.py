from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import torch

processor = AutoImageProcessor.from_pretrained("google/vit-base-patch16-224")
model = AutoModelForImageClassification.from_pretrained(
    "google/vit-base-patch16-224"
)

def classify(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(image, return_tensors="pt")
    outputs = model(**inputs)
    return outputs.logits.argmax(-1).item()
