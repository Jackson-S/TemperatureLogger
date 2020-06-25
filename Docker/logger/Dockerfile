FROM alpine:3

RUN apk add py3-requests py3-paho-mqtt git

COPY ./ /app

WORKDIR /app

ENTRYPOINT ["python3"]
CMD ["logger.py"]
