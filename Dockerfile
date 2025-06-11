# pakai python image
FROM python:3.11-slim

# set workdir
WORKDIR /app

# copy requirements dan install dulu (biar cache)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy semua file project
COPY . .

# set env kalo ada (biar bisa pakai .env)
ENV PYTHONUNBUFFERED=1

# run bot
CMD ["python", "main.py"]
