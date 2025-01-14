from threading import Thread
import json
from queue import Queue
import os

from openai import OpenAI

from .parsers import extract_json, extract_list, rectangle_corners
from .ocr_engines import (
    job_easy_ocr,
    job_easy_ocr_boxes,
    job_tesseract,
    job_tesseract_boxes,
)


def wrapper(func, args, queue):
    queue.put(func(args))


# custom error
class NoTextDetectedError(Exception):
    pass


def detect():
    """Unimplemented"""
    raise NotImplementedError


def detect_async():
    """Unimplemented"""
    raise NotImplementedError


def detect_text(
    image_path: str,
    lang: list[str],
    context: str = "",
    tesseract: dict = {},
    openai: dict = {"model": "gpt-4"},
):
    """Detect text from an image using EasyOCR and Tesseract, then combine and correct the results using OpenAI's LLM."""
    q1, q2 = Queue(), Queue()
    options = {
        "path": image_path,  # "demo.png",
        "lang": lang,  # ["ko", "en"]
        "context": context,
        "tesseract": tesseract,
        "openai": openai,
    }

    Thread(target=wrapper, args=(job_easy_ocr, options, q1)).start()
    Thread(target=wrapper, args=(job_tesseract, options, q2)).start()

    q1 = q1.get()
    q2 = q2.get()

    optional_context_prompt = (
        f"[context]: {options['context']}" if options["context"] else ""
    )

    prompt = f"""Combine and correct OCR results [0] and [1], using \\n for line breaks. Langauge is in {'+'.join(options['lang'])}. Remove unintended noise. Refer to the [context] keywords. Answer in the JSON format {{data:<output:string>}}:
    [0]: {q1}
    [1]: {q2}
    {optional_context_prompt}"""

    prompt = prompt.strip()

    print("=====")
    print(prompt)

    # Prioritize user-specified API_KEY
    api_key = options["openai"].get("API_KEY", os.environ.get("OPENAI_API_KEY"))

    # Make a shallow copy of the openai options and remove the API_KEY
    openai_options = options["openai"].copy()
    if "API_KEY" in openai_options:
        del openai_options["API_KEY"]

    client = OpenAI(
        api_key=api_key,
    )

    print("=====")

    completion = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt},
        ],
        **openai_options,
    )
    output = completion.choices[0].message.content
    print("[*] LLM", output)

    result = extract_json(output)
    print(result)

    if "data" in result:
        return result["data"]
    if isinstance(result, str):
        return result
    raise NoTextDetectedError("No text detected")


def detect_text_async():
    """Unimplemented"""
    raise NotImplementedError


def detect_boxes(
    image_path: str,
    lang: list[str],
    context: str = "",
    tesseract: dict = {},
    openai: dict = {"model": "gpt-4"},
):
    q1, q2 = Queue(), Queue()
    options = {
        "path": image_path,  # "demo.png",
        "lang": lang,  # ["ko", "en"]
        "context": context,
        "tesseract": tesseract,
        "openai": openai,
    }

    Thread(target=wrapper, args=(job_easy_ocr_boxes, options, q1)).start()
    Thread(target=wrapper, args=(job_tesseract_boxes, options, q2)).start()

    boxes_1 = q1.get()
    boxes_2 = q2.get()

    optional_context_prompt = (
        " " + "Please refer to the keywords and spelling in [context]"
        if options["context"]
        else ""
    )
    optional_context_prompt_data = (
        f"[context]: {options['context']}" if options["context"] else ""
    )

    boxes_1_json = json.dumps(boxes_1, ensure_ascii=False, default=int)
    boxes_2_json = json.dumps(boxes_2, ensure_ascii=False, default=int)

    prompt = f"""Combine and correct OCR data [0] and [1]. Include many items as possible. Langauge is in {'+'.join(options['lang'])} (Avoid arbitrary translations). Remove unintended noise.{optional_context_prompt} Answer in the JSON format. Ensure coordinates are integers (round based on confidence if necessary) and output in the same JSON format (indent=0): Array({{box:[[x,y],[x+w,y],[x+w,y+h],[x,y+h]],text:str}}):
    [0]: {boxes_1_json}
    [1]: {boxes_2_json}
    {optional_context_prompt_data}"""

    prompt = prompt.strip()

    print("=====")
    print(prompt)

    # Prioritize user-specified API_KEY
    api_key = options["openai"].get("API_KEY", os.environ.get("OPENAI_API_KEY"))

    # Make a shallow copy of the openai options and remove the API_KEY
    openai_options = options["openai"].copy()
    if "API_KEY" in openai_options:
        del openai_options["API_KEY"]

    client = OpenAI(
        api_key=api_key,
    )

    print("=====")

    completion = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt},
        ],
        **openai_options,
    )
    output = completion.choices[0].message.content
    output = output.replace("\n", "")
    print("[*] LLM", output)

    items = extract_list(output)

    for idx, item in enumerate(items):
        box = item["box"]

        # [x,y,w,h]
        if len(box) == 4 and isinstance(box[0], int):
            rect = rectangle_corners(box)
            items[idx]["box"] = rect

        # [[x,y],[w,h]]
        elif len(box) == 2 and isinstance(box[0], list) and len(box[0]) == 2:
            flattened = [i for sublist in box for i in sublist]
            rect = rectangle_corners(flattened)
            items[idx]["box"] = rect

    return items


def detect_boxes_async():
    """Unimplemented"""
    raise NotImplementedError
