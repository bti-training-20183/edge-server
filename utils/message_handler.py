import pika
import config
import sys
import os
import socket
import time

sys.path.append(os.getcwd())


class MessageHandler:
    def __init__(self, host):
        isreachable = False
        while isreachable is False:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(('rabbitmq', 5672))
                print("Connected to RabbitMQ")
                isreachable = True
            except socket.error as e:
                print("Not connected to RabbitMQ")
                time.sleep(2)
            s.close()
        if isreachable:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(config.RABBITMQ_CONNECTION))
            self.channel = self.connection.channel()
            self.channel.queue_declare('from_client')
            self.channel.queue_declare('from_creator')
            self.channel.queue_declare('from_preprocessor')
            self.channel.queue_declare('from_deployer')

    def sendMessage(self, queue, body):
        self.channel.basic_publish(
            exchange='', routing_key=queue, body=body)
        print(f" [x] Sent {body} to queue: {queue}")

    def consumeMessage(self, queue, callback):
        self.channel.basic_consume(
            queue=queue, on_message_callback=callback, auto_ack=True)
        print(f' [*] Waiting for messages from {queue}. To exit press CTRL+C')
        self.channel.start_consuming()

    def close(self):
        self.connection.close()

# Message_Handler = MessageHandler(config.RABBITMQ_CONNECTION)