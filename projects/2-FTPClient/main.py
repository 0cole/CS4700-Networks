#!/usr/bin/env python3
import argparse
import socket

SINGLE_PARAM_CMDS = ['ls', 'rm', 'rmdir', 'mkdir']
TWO_PARAM_CMDS = ['cp', 'mv']

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
    
def sendMessage(s, command, param1 = None, param2 = None):
    msg = f'{command}'
    if param1: msg += f' {param1}'
    if param2: msg += f' {param2}'
    msg += '\r\n'
    s.sendall(msg.encode('ascii'))

def receiveMessage(s):
    message = s.recv(1024).decode('ascii')
    print(message)

def login(socket, user = 'anonymous', password = None):
    sendMessage(socket, 'USER', user)
    receiveMessage(socket)
    sendMessage(socket, 'PASS', password)
    receiveMessage(socket)
    sendMessage(socket, 'TYPE', 'I')
    receiveMessage(socket)
    sendMessage(socket, 'STRU', 'F')
    receiveMessage(socket)
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
    receiveMessage(socket)


def main():
    host = "ftp.4700.network"
    user = "harvey.c"
    password = "e04fa0d3c760d01e0b2afa425be52d2da53fd944f0df069d35c656a28ee05e7f"

    socket = connect(host)
    login(socket, user, password)

    args = parser()
    cmd = args.cmd

    print(f'Command: {args.cmd} Path: {args.path}')


    if cmd in SINGLE_PARAM_CMDS:
        runCommand(socket, cmd, args.path)
    else:
        runCommand(socket, cmd, args.path, args.dest_path)

    close(socket)

    

if __name__ == "__main__":
    main()