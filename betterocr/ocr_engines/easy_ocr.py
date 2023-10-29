import easyocr


def job_easy_ocr(_options):
    reader = easyocr.Reader(_options["lang"])
    result = reader.readtext(_options["path"], output_format="dict")
    text = [item["text"] for item in result]
    text = "".join(text)
    print("[*] job_easy_ocr", text)
    return [text, result]


def job_easy_ocr_boxes(_options):
    reader = easyocr.Reader(_options["lang"])
    boxes = reader.readtext(_options["path"], output_format="dict")
    for box in boxes:
        box["box"] = box.pop("boxes")
    return boxes
