FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY blueprint ./blueprint
COPY sample ./sample
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "blueprint.api:app", "--host", "0.0.0.0", "--port", "8000"]
