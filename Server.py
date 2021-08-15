import socket
import threading
import pickle
import urllib.request

player_info = [99, 99]
setup_end = False
clients_connected = [False, False]

#receive  data from one client and send it to only the other
def threaded_client(conn, client_num):
    global setup_end
    global switch_turn
    clients_connected[client_num] = True
    conn.send(pickle.dumps(client_num))
    reply = ""
    while True:
        try:
            data = pickle.loads(conn.recv(2048))
            if data == 24:
                setup_end = True
            elif data == [True, 4]:
                player_info[client_num] == 99
            elif data == 12:
                player_info[0] = player_info[client_num]
                player_info[1] = player_info[client_num]
            elif data == 4:
                pass
            elif data == 22:
                player_info[0] = 0
                player_info[1] = 0
               # break
            else:
                player_info[client_num] = data
            if not data:
                print("Disconnected")
                break
            else:
                if client_num == 0:
                    if data == 4:
                        reply = clients_connected[1]
                    else:
                        reply = player_info[1]
                else:
                    if setup_end:
                        reply = 48
                        setup_end = False
                    else:
                        reply = player_info[0]
            conn.sendall(pickle.dumps(reply))
        except:
            break
    print("Lost connection")
    client_num -= 1
    conn.close()

def start_server(external_ip):
    SERVER = external_ip
    PORT = 5050
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        s.bind((SERVER, PORT))
    except socket.error as e:
        str(e)
    s.listen(2)
    print("Server started, waiting for connection")
    client_num = 0
    while True:
        conn, addr = s.accept()
        print("Connected to:", addr)
        thread = threading.Thread(target=threaded_client, args = (conn, client_num))
        thread.start()
        client_num += 1

if __name__ == '__main__':
    start_server(urllib.request.urlopen('https://ident.me').read().decode('utf8'))