import socket

def main():
    host = '54.242.58.91'
    port = 12345
    s = socket.socket()
    try:
        s.connect((host, port))

        msg = "hello from client"
        s.send(msg.encode())

        incoming = s.recv(1024).decode()
        print(incoming)

        s.close()
    except ConnectionRefusedError:
        print("host unavailable")

if __name__ == "__main__":
    main()