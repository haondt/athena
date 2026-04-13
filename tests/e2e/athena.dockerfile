# Use an official Python runtime as a parent image
FROM python:3.14-slim

RUN apt update
RUN apt install -y curl
RUN pip install -U pytest flask flit


WORKDIR /app

COPY ./pyproject.toml /app
COPY ./LICENSE /app
RUN touch /app/README.md
RUN mkdir /app/athena

ENV FLIT_ROOT_INSTALL=1
RUN python3 -m flit install --only-deps

COPY . /app
RUN pip install .

WORKDIR /tests

ENTRYPOINT ["pytest"]

