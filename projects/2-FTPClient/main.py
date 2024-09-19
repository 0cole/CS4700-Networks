#!/usr/bin/env python3
import argparse
import socket

SINGLE_PARAM_CMDS = ['ls', 'rm', 'rmdir', 'mkdir']
TWO_PARAM_CMDS = ['cp', 'mv']

HOST = "ftp.4700.network"
USER = "harvey.c"
PASSWORD = "e04fa0d3c760d01e0b2afa425be52d2da53fd944f0df069d35c656a28ee05e7f"

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

def connectPasv():
    pass

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
        sendMessage(socket, 'MKD', param1)
    elif cmd == 'rmdir':
        sendMessage(socket, 'RMD', param1)
    elif cmd == 'ls':
        recv_msg = sendMessage(socket, 'PASV')
        pasv_addr = recv_msg.split('(')[1].split(')')[0].split(',')
        pasv_ip = pasv_addr[0]
        for i in range(1,4):
            pasv_ip += ('.' + pasv_addr[i])
        pasv_port = (int(pasv_addr[4]) << 8) + int(pasv_addr[5])
        pasv_socket = connect(pasv_ip, pasv_port)
        sendMessage(socket, 'LIST', param1)
        dir_list = receiveMessage(pasv_socket)
        print(dir_list)

    return

def main():

    socket = connect(HOST)
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