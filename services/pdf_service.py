from pdf2image import convert_from_path
import os

def pdf_to_images(pdf_path):
    images = convert_from_path(pdf_path, dpi=300)
    paths = []

    for i, img in enumerate(images):
        path = f"{pdf_path}_{i}.png"
        img.save(path)
        paths.append(path)

    return paths
