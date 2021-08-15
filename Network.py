import socket
import pickle

class Network:
    def __init__(self, ipv6):
        self.client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.server = ipv6
        self.port = 5050
        self.addr = (self.server, self.port)
        self.id = self.connect()
        print("self id = ", self.id, "\n")

    def connect(self):
        try:
            self.client.connect(self.addr)
            return pickle.loads(self.client.recv(2048))
        except:
            print("CONNECTION FAILED")
            return -1

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            return pickle.loads(self.client.recv(2048))
        except socket.error as e:
            print(e)
