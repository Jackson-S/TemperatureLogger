FROM alpine:3

RUN apk add py3-paho-mqtt

COPY ./logger.py /app/logger.py

WORKDIR /app

ENTRYPOINT ["python3"]
CMD ["logger.py"]
