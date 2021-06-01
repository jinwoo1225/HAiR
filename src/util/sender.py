import socket

import numpy as np


def recvall(sock: socket, count: int) -> bytes:
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return buf
        buf += newbuf
        count -= len(newbuf)
    return buf


class Sender:
    def __init__(self):
        self.client_socket: socket = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM
        )
        self.client_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )
        self.client_socket.connect(
            (
                '127.0.0.1',
                8080
            )
        )
        print('connected to 127.0.0.1:8080')

    def send_and_recv(self, datas: dict) -> np.ndarray:
        datas = datas
        for key, item in datas.items():
            payload: bytes = item.tostring()
            length: bytes = str(len(payload)).ljust(16).encode()
            print(f"sending {key} [size :{length}, shape :{item.shape} ]")
            self.client_socket.send(length)
            self.client_socket.send(payload)

        gen_length = recvall(self.client_socket, 16).decode()
        gen_payload = recvall(self.client_socket, int(gen_length))

        buffered_data = np.frombuffer(gen_payload, dtype="uint8")
        return np.resize(buffered_data, (512, 512, 3))
