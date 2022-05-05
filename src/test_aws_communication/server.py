import socket

def main():
    host = '127.0.0.1'
    port = 12345
    s = socket.socket()
    s.bind((host, port))
    s.listen()
    c, addr = s.accept()

    incoming = c.recv(1024).decode()
    print(incoming)

    msg = "hello from server"
    c.send(msg.encode())

    c.close()

if __name__ == "__main__":
    main()