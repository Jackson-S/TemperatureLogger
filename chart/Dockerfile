FROM alpine:3

RUN apk add py3-flask git

COPY . /app

WORKDIR /app/logger

ENTRYPOINT ["python3"]
CMD ["chart.py"]
