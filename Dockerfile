FROM python:3.13-alpine

# Variables para no generar archivos .pyc y salida sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apk add --no-cache gcc musl-dev libffi-dev

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copiar el resto del código
COPY . .

# Exponer el puerto que usará Flask
EXPOSE 5000

# Comando por defecto para arrancar la app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
