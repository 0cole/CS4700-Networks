## Summary

This script supports communication with an FTP server. It can be invoked with `./4700ftp`, and it will automatically connect and communicate the ftp server that you pass in with the `ftp://` URL. 

This script allows the usage of 6 commands:

1. `ls <URL>`
2. `mkdir <URL>`
3. `rm <URL>`
4. `rmdir <URL>`
5. `cp <SRC> <DEST>`
6. `mv <SRC> <DEST>`

For `cp` and `mv`, the `ftp://` url can be the source or destination argument, and the other would be a path on your local machine. 

## Approach

Much of the communication is performed in runCommand. The command and paths are parsed using argparser. Since each command line input will include a ftp URL, the user, password, host, and port can all be parsed which are used to connect the initial socket.

Once this socket is created, it is passed into runCommand along wiht the command and parameters the user input. Within runCommand, if the command involves creating a data channel, than an additional socket is created that serves to send and receive data from the ftp server. This socket is referred to as `pasv_socket`. 

# Testing

All of the testing for this program was done using this course's ftp server. I have tested it throughout the development stages to make sure that every command works as expected.


## Notes for myself

Host - ftp://ftp.4700.network

Username - harvey.c

Password - e04fa0d3c760d01e0b2afa425be52d2da53fd944f0df069d35c656a28ee05e7f