#!/usr/bin/env python3
import argparse

SINGLE_PARAM_CMDS = ['ls', 'rm', 'rmdir', 'mkdir']
TWO_PARAM_CMDS = ['cp', 'mv']

def parser():
    # Initialize the variables that potentially get used
    cmd, path1, path2 = None, None, None

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

def main():
    args = parser()

    cmd = args.cmd

    # if cmd in SINGLE_PARAM_CMDS:
    #     runCommand(cmd, args.path)
    # else:
    #     runCommand(cmd, args.path, args.dest_path)

    

if __name__ == "__main__":
    main()