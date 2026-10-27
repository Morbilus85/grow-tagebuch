ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GROW_DATA_DIR=/data \
    GROW_FRONTEND_DIR=/app/frontend/dist

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend/dist /app/frontend/dist
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
