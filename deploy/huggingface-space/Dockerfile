FROM python:3.13-slim

RUN useradd --create-home --uid 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QQ_API_CORS_ORIGINS=https://exergyfactor.com,https://www.exergyfactor.com \
    QQ_API_REQUIRE_KEY=0 \
    QQ_MCP_HTTP_ENABLED=1

WORKDIR /home/user/app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
      "quantity-and-quality[api,mcp,fluids]==0.13.2"

COPY --chown=user app.py /home/user/app/app.py

EXPOSE 7860 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '7860') + '/v1/health', timeout=4)"]

CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips '*'"]
