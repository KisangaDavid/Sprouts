import socket
from _thread import *
import pickle
import sys



server = "192.168.1.70"
port = 5555
p1_turn = True

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.bind((server, port))
except socket.error as e:
    str(e)

s.listen(2)
print("Server started, waiting for connection")

player_info = [99, 99]
p1_turn = True
setup_end = False

#receive  data from one client and send it to only the other
def threaded_client(conn, client_num):
    global setup_end
    global switch_turn
    print("this is where the stuff is")
    conn.send(pickle.dumps(client_num))
    reply = ""
    while True:
        try:
            data = pickle.loads(conn.recv(2048))
            #print(data)
            if data == 24:
                setup_end = True
            elif data == [True, 4]:
                player_info[client_num] == 99
                pass
            elif data == 12:
                player_info[0] = player_info[client_num]
                player_info[1] = player_info[client_num]
            else:
                player_info[client_num] = data
            if not data:
                print("Disconnected")
                break
            else:
                if client_num == 0:
                        reply = player_info[1]
                else:
                    if setup_end:
                        reply = 48
                        setup_end = False
                    else:
                        reply = player_info[0]
               # print("Received: ", data)
               # print("Sending to client: ", reply)
            conn.sendall(pickle.dumps(reply))
        except:
            break
    print("Lost connection")
    client_num -= 1
    conn.close()



# def threaded_client(conn, client_num):
#     conn.send(pickle.dumps("Connected"))
#     reply = ""
#     while True:
#         try:
#             data = pickle.loads(conn.recv(2048))
#             if not data:
#                 print("Disconnected")
#                 break
#             else:
#                 if data[0] == client_num:
#                    # print("Received: ", data)
#                     #print("Sending: ", data)
#                     print("Sending data, p1 = ", data[0])
#                     conn.sendall(pickle.dumps(data))
#         except:
#             break
#     print("Lost connection")
#     conn.close()

client_num = 0

while True:
    conn, addr = s.accept()
    print("Connected to:", addr)
    start_new_thread(threaded_client, (conn, client_num))
    client_num += 1