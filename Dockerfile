FROM python:3.9

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]