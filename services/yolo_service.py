from ultralytics import YOLO
import easyocr
import cv2

# Global variables for lazy loading
yolo = None
reader = None

def load_models():
    global yolo, reader
    if yolo is None or reader is None:
        print("Loading YOLO and EasyOCR models...")
        yolo = YOLO("yolov8n.pt")
        reader = easyocr.Reader(["en", "ar"], gpu=False)  # Changed to CPU for stability
        print("YOLO and EasyOCR models loaded successfully!")

def yolo_easyocr(image_path):
    load_models()  # Load models only when needed
    img = cv2.imread(image_path)
    results = yolo(img)
    texts, confs = [], []

    for r in results:
        for box in r.boxes.xyxy:
            x1,y1,x2,y2 = map(int, box)
            crop = img[y1:y2, x1:x2]
            ocr = reader.readtext(crop)
            for _, txt, conf in ocr:
                texts.append(txt)
                confs.append(conf)

    avg_conf = sum(confs)/max(len(confs),1)
    return "\n".join(texts), avg_conf
