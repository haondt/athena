# Use an official Python runtime as a parent image
FROM python:3.11-slim

RUN pip install flask

WORKDIR /app

ENTRYPOINT ["python3"]
