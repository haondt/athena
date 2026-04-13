# Use an official Python runtime as a parent image
FROM python:3.14-slim

RUN pip install flask

WORKDIR /app

ENTRYPOINT ["python3"]
