from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import re
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


def preprocess_image(image_path):
    image = Image.open(image_path)

    image = image.convert('L')

    return image


def second_preprocess_image(image_path):
    image = Image.open(image_path).convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    return image


def fix_ocr_errors(text):
    corrections = {
        'В': '8', 'У': '9', 'Т': '7', 'Ь': '1', 'Ч': '4',
        'З': '3', 'О': '0', 'Ю': '0', '?': '3',
        'Д': '0', 'А': '4', 'С': '5', 'Е': '6', 'К': '6', 'М': '1',
        'И': '1', 'Л': '1', 'П': '1', 'Р': '2', 'Х': '4', 'Ц': '7',
        'Щ': '9', 'Ъ': '1', 'Ы': '1', 'Э': '3', 'Я': '9'
    }

    for wrong_char, correct_char in corrections.items():
        text = text.replace(wrong_char, correct_char)
    return text


def clean_activation_code(code):
    parts = code.split()
    cleaned_parts = []
    for part in parts:
        if len(part) > 7:
            part = part[1:]
        cleaned_parts.append(part)
    return " ".join(cleaned_parts)


def correct_first_two_digits(code):
    if code.startswith('44'):
        return '11' + code[2:]
    return code


def extract_activation_code(image_path):
    image = preprocess_image(image_path)

    text = pytesseract.image_to_string(image, lang='rus')

    corrected_text = fix_ocr_errors(text)

    header_pattern = r'Шаг\s*2\.\s*Когда\s*потребуется,\s*сообщите\s*этот\s*код\s*установки:'
    header_match = re.search(header_pattern, corrected_text)

    if header_match:
        code_text = corrected_text[header_match.end():]
    else:
        code_text = corrected_text

    activation_code_pattern = r'(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})'
    match = re.search(activation_code_pattern, code_text)

    if match:
        activation_code = ' '.join(match.groups())

        activation_code = correct_first_two_digits(activation_code)

        return activation_code
    else:
        return 'Код установки не найден.'


def second_extract_activation_code(image_path):
    image = second_preprocess_image(image_path)

    custom_config = r'--oem 3 --psm 4'
    extracted_text = pytesseract.image_to_string(image, config=custom_config, lang='rus')

    corrected_text = fix_ocr_errors(extracted_text)

    match = re.search(r'Шаг\s*2.*?сообщите.*?код\s*установки[:\-]?\s*([\d\s]+)', corrected_text,
                      re.IGNORECASE | re.DOTALL)
    if match:
        code = match.group(1).strip()
        return clean_activation_code(code)

    numbers = re.findall(r'\b(?:\d{7,8}\s+){7,8}\d{7,8}\b', corrected_text)
    if numbers:
        return clean_activation_code(numbers[0])

    activation_code_pattern = r'(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})\s(\d{7})'
    match = re.search(activation_code_pattern, corrected_text)
    if match:
        activation_code = ' '.join(match.groups())
        return activation_code

    return 'Код установки не найден.'


def main(image_path):
    result = extract_activation_code(image_path)

    if result == 'Код установки не найден.':
        result = second_extract_activation_code(image_path)

    return result


@app.post("/extract-code")
async def extract_code(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
            temp.write(await file.read())
            temp_path = temp.name

        result = main(temp_path)

        os.unlink(temp_path)

        return {"code": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))