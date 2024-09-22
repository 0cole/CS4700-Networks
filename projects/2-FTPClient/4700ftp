#!/usr/bin/env python3
import argparse
import socket

SINGLE_PARAM_CMDS = ['ls', 'rm', 'rmdir', 'mkdir']
TWO_PARAM_CMDS = ['cp', 'mv']

HOST = "ftp.4700.network"
PORT = 21
USER = "harvey.c"
PASSWORD = "e04fa0d3c760d01e0b2afa425be52d2da53fd944f0df069d35c656a28ee05e7f"
SERVER_LOCATION = "ftp://harvey.c:e04fa0d3c760d01e0b2afa425be52d2da53fd944f0df069d35c656a28ee05e7f@ftp.4700.network:21"

def parser():

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd', required=True)

    # Add commands that require only 1 parameter
    for command in SINGLE_PARAM_CMDS:
        subparser = subparsers.add_parser(command)
        subparser.add_argument('path', type=str)

    # Add commands that require 2 parameters
    for command in TWO_PARAM_CMDS:
        subparser = subparsers.add_parser(command)
        subparser.add_argument('path', type=str)
        subparser.add_argument('dest_path', type=str)
    
    args = parser.parse_args()

    return args

def connect(host, port = 21):
    """
    Create a connection to the 'host' server socket. By default,
    the port is set to 21. Catch any errors that may occur
    during the connection.
    """
    try:
        # init socket
        ftp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ftp_socket.connect((host, port))
        return ftp_socket
    
    except (socket.error) as e:
        print(f'ERROR: {e}')
        return None

def connectPasv(socket):
    recv_msg = sendMessage(socket, 'PASV')
    # Grab the data from the pasv received message and store 
    # it in an array delimited by ,
    # Should look like [192,168,0,1,1,1]
    pasv_addr = recv_msg.split('(')[1].split(')')[0].split(',')
    pasv_ip = '.'.join(pasv_addr[:4])
    pasv_port = (int(pasv_addr[4]) << 8) + int(pasv_addr[5])  # Convert to real port using bitshift
    pasv_socket = connect(pasv_ip, pasv_port)
    return pasv_socket

def sendMessage(s, command, param1 = None, param2 = None):
    msg = f'{command}'
    if param1: msg += f' {param1}'
    if param2: msg += f' {param2}'
    msg += '\r\n'
    s.sendall(msg.encode('ascii'))

    return receiveMessage(s)

def receiveMessage(s):
    message = s.recv(1024).decode('ascii')
    # print(message)
    return message

def login(socket, user = 'anonymous', password = None):
    sendMessage(socket, 'USER', user)
    sendMessage(socket, 'PASS', password)
    sendMessage(socket, 'TYPE', 'I')
    sendMessage(socket, 'STRU', 'F')
    sendMessage(socket, 'MODE', 'S')

def close(socket):
    sendMessage(socket, 'QUIT')
    receiveMessage(socket)
    socket.close()

def runCommand(socket, cmd, param1 = None, param2 = None):
    if cmd == 'mkdir':
        print(sendMessage(socket, 'MKD', param1))
    elif cmd == 'rmdir':
        print(sendMessage(socket, 'RMD', param1))
    elif cmd == 'ls':
        ftp_path = param1.split(f'{HOST}:{PORT}/')[1]
        pasv_socket = connectPasv(socket)
        sendMessage(socket, 'LIST', ftp_path)
        print(receiveMessage(pasv_socket))
        close(pasv_socket)
    elif cmd == 'rm':
        print(sendMessage(socket, 'DELE', param1))
    elif cmd == 'cp':
        if param1.startswith('ftp'):
            # cp from ftp server to local
            local_file = param2
            ftp_file = param1.split(f'{HOST}:{PORT}/')[1]

            pasv_socket = connectPasv(socket)
            sendMessage(socket, 'RETR', ftp_file)

            with open(local_file, "wb") as f:
                while True:
                    data = pasv_socket.recv(1024)
                    if not data:
                        break
                    f.write(data)
            close(pasv_socket)
            print(receiveMessage(socket))
        else:
            # cp from local to ftp server
            local_file = param1
            ftp_file = param2.split(f'{HOST}:{PORT}/')[1]

            pasv_socket = connectPasv(socket)
            sendMessage(socket, 'STOR', ftp_file)

            with open(local_file, 'r') as file:
                buffer = file.read()
            pasv_socket.sendall(buffer.encode('ascii'))
            close(pasv_socket)
            print(receiveMessage(socket))

def main():

    socket = connect(HOST, PORT)
    login(socket, USER, PASSWORD)

    args = parser()
    cmd = args.cmd

    # print(f'Command: {args.cmd} Path: {args.path}')

    if cmd in SINGLE_PARAM_CMDS:
        runCommand(socket, cmd, args.path)
    else:
        runCommand(socket, cmd, args.path, args.dest_path)

    close(socket)

    

if __name__ == "__main__":
    main()