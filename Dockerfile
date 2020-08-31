FROM python:3

RUN apt update
RUN apt install -y ffmpeg

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY .env ./
COPY converter_bot.py ./

RUN pip3 install --no-cache-dir -r requirements.txt

CMD [ "python3", "./converter_bot.py"]
