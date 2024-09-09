#!/usr/bin/python3
import socket
import json
import sys
import argparse

def createWordlist():
    word_list = []
    file = open('wordlist.txt', 'r')
    line = file.readline()
    while line:
        word_list.append(line.replace('\n', ''))
        line = file.readline()

    return word_list

def connect(host, port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, port))
    except socket.error as e:
        print(f'ERROR: {e}')
        return
    return client

def sendMessage(socket, message):
    msg_str = json.dumps(message) + '\n'
    socket.sendall(msg_str.encode('ascii'))

def receiveMessage(socket: socket.socket):
    """
    Retrieves the message in increments of 4096 bytes and stores it in a
    string buffer. Once there is no more text to read, convert buffer to json.
    """
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
            
        except Exception as e:
            print(f'Socket error: {e}')
            break

    print('Something went wrong parsing the json')
    return None
    
def run(s, user):
    # Send initial hello message to retrieve id
    init_msg = {'type': 'hello', 'northeastern_username': user}
    sendMessage(s, init_msg)
    msg = receiveMessage(s)
    id = msg['id']

    words = createWordlist()

    while words:
        guess = words.pop(0)
        guess_msg = {'type': 'guess', 'id': id, 'word': guess}
        sendMessage(s, guess_msg)
        msg = receiveMessage(s)

        if msg['type'] == 'bye':
            # Correct guess
            print(msg['flag'])
            break
        elif msg['type'] == 'retry':
            # Incorrect guess, filter out rest of words
            marks = msg['guesses'][-1]['marks']
            filtered_words = []

            for word in words:
                valid = True
                for i, letter in enumerate(guess):
                    if marks[i] == 2 and word[i] != letter:
                        valid = False
                        break
                    elif marks[i] == 1 and (word[i] == letter or letter not in word):
                        valid = False
                        break
                    elif marks[i] == 0 and letter in word[i]:
                        valid = False
                        break
                if valid:
                    filtered_words.append(word)
            
            words = filtered_words

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=27993, type=int)
    # parser.add_argument('-s')
    # parser.add_argument('hostname')
    # parser.add_argument('username')
    args = parser.parse_args()
    
    if args.p:
        port = args.p

    host = 'proj1.4700.network'
    user = 'harvey.c'

    s = connect(host, port)
    run(s, user)
    s.close()

if __name__ == '__main__':
    main()
