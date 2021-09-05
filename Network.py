import socket
import pickle

class Network:
    def __init__(self, ipv4):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = ipv4
        self.port = 14400
        self.addr = (self.server, self.port)
        self.id = self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)
            return pickle.loads(self.client.recv(4096))
        except Exception as e:
            print(e)
            return -1

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            return pickle.loads(self.client.recv(4096))
        except socket.error as e:
            print(e)