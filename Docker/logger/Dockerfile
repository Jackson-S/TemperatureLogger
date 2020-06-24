FROM alpine:3

RUN apk add py3-requests py3-paho-mqtt git

COPY . /app

RUN git clone https://github.com/Jackson-S/TemperatureLogger /app/logger

WORKDIR /app/logger

ENTRYPOINT ["python3"]
CMD ["logger.py"]
