FROM btiintern/python
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD python server.py