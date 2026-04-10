# Use a imagem base oficial do Python
FROM python:3.11-slim

# Evite que o Python gere arquivos .pyc e garanta que o log apareça imediatamente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho no container
WORKDIR /app

# Instala dependências do sistema necessárias para algumas bibliotecas (ex: grpcio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta que o Cloud Run usará (o Cloud Run define a variável de ambiente PORT)
EXPOSE 8080

# Comando para rodar a aplicação usando o uvicorn
CMD ["uvicorn", "main.py:app", "--host", "0.0.0.0", "--port", "8080"]
