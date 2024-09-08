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
            print(f'Socket error: {e}')
            break

    print('Something went wrong parsing the json')
    return None
    
def run(s, user):
    words = createWordlist()
    found = ['_'] * 5
    wrong_pos = ['_'] * 5
    exclude = set()
    flag = None

    init_msg = {'type': 'hello', 'northeastern_username': user}
    sendMessage(s, init_msg)

    msg = receiveMessage(s)
    id = msg['id']

    while True:
        word = words[0]
        guess_msg = {'type': 'guess', 'id': id, 'word': word}
        sendMessage(s, guess_msg)
        msg = receiveMessage(s)

        if msg['type'] == 'bye':
            # Guessed correctly
            flag = msg['flag']
            print(flag)
            found = True
            break
        elif msg['type'] == 'retry':
            # Guessed incorrectly
            marks = msg['guesses'][-1]['marks']
            for i in range(5):
                letter = word[i]
                if marks[i] == 0:
                    if letter not in found:
                        exclude.add(letter)
                elif marks[i]  == 1:
                    wrong_pos[i] = letter
                elif marks[i]  == 2:
                    if letter in wrong_pos:
                        idx = wrong_pos.index(letter)
                        wrong_pos[idx] = '_'
                    found[i] = letter

        filtered_words = []
        for potential_word in words:
            if any(potential_word[i] != found[i] for i in range(5) if found[i] != '_'):
                continue
            if any(potential_word[i] == wrong_pos[i] for i in range(5) if wrong_pos[i] != '_'):
                continue
            if any(letter not in potential_word for letter in wrong_pos if letter != '_'):
                continue
            if any(letter in potential_word for letter in exclude):
                continue
            filtered_words.append(potential_word)

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
