#!/usr/bin/env python3
import argparse

def main():

    parser = argparse.ArgumentParser
    parser.add_argument('ls', type='string')
    parser.add_argument('rm', type='string')
    parser.add_argument('rmdir', type='string')
    parser.add_argument('mkdir', type='string')
    parser.add_argument('cp', type='string')
    parser.add_argument('mv', type='string')

        

if __name__ == "__main__":
    main()