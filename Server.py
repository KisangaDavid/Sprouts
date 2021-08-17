import socket
import threading
import pickle

player_info = [99, 99]
setup_end = False
new_game = False
clients_connected = [False, False]

def threaded_client(conn, client_num):
    global clients_connected
    global setup_end
    global new_game 
    clients_connected[client_num] = True
    conn.send(pickle.dumps(client_num))
    reply = ""
    while True:
        try:
            data = pickle.loads(conn.recv(4096))
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
            elif data == 33:
                new_game = True
                player_info[0] == 99
                player_info[1] == 99
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
                    elif new_game:
                        reply = 33
                        new_game = False
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
    client_num = 0
    while True:
        conn, addr = s.accept()
        thread = threading.Thread(target=threaded_client, args = (conn, client_num))
        thread.start()
        client_num += 1
