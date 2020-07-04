FROM alpine:3

RUN apk add py3-flask

COPY ./chart.py /app/chart.py
COPY ./templates /app/templates
COPY ./static /app/static

WORKDIR /app

ENTRYPOINT ["python3"]
CMD ["chart.py"]
