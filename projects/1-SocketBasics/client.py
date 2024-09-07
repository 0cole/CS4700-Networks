#!/usr/bin/python3
import socket
import json

SERVER_HOST = "proj1.4700.network"
SERVER_PORT = 27993
USER_NAME = "harvey.c"

def createWordlist():
    word_list = []
    file = open("wordlist.txt", "r")
    line = file.readline()
    while line:
        word_list.append(line.replace('\n', ''))
        line = file.readline()

    return word_list

def connect():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f'Trying to connect to {SERVER_HOST}:{SERVER_PORT}')
        client.connect((SERVER_HOST, SERVER_PORT))
        print("Successfully connected to server")
    except socket.error as e:
        print(f"ERROR: {e}")
        return
    return client

def sendMessage(socket, message):
    msg_str = json.dumps(message) + '\n'
    socket.sendall(msg_str.encode('ascii'))

def receiveMessage(socket: socket.socket):
    buf = ''
    while True:
        try:
            chunk = socket.recv(4096).decode('ascii')
            if chunk is None:
                break
            buf += chunk

            try:
                res_json = json.loads(buf)
                return res_json
            except json.JSONDecodeError as e:
                continue
            
        except socket.error as e:
            print(f"Socket error: {e}")
            break

    print("Something went wrong parsing the json")
    return None
    
def run():
    s = connect()
    words = createWordlist()
    final = [] * 5
    include = [] * 5
    exclude = []

    init_msg = {"type": "hello", "northeastern_username": USER_NAME}
    sendMessage(s, init_msg)

    msg = receiveMessage(s)
    id = msg['id']

    for word in words:
        # Check if any characters in word are excluded
        skip = False
        for c in word:
            if c in exclude:
                skip = True
        if skip:
            break

        # Guess word
        guess_msg = {"type": "guess", "id": id, "word": word}
        sendMessage(s, guess_msg)

        msg = receiveMessage(s)
        print(msg)
        break


    s.close()

if __name__ == "__main__":
    run()
