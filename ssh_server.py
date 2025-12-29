import os
import socket
import threading
import subprocess
import select
import logging
import paramiko
from typing import Tuple

# =======================
# Configurações
# =======================

HOST = "0.0.0.0"
PORT = 3333
BACKLOG = 100
BANNER = "Bem-vindo ao servidor!\n"
SHELL_PATH = "/bin/bash"

SSH_PASSWORD = os.getenv("SSH_PASSWORD")
if not SSH_PASSWORD:
    raise RuntimeError("Variável de ambiente SSH_PASSWORD não definida")

HOST_KEY = paramiko.RSAKey.generate(2048)

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

# =======================
# Implementação do Servidor SSH
# =======================

class SSHServer(paramiko.ServerInterface):
    def __init__(self) -> None:
        self.event = threading.Event()

    def get_banner(self) -> Tuple[str, str]:
        return BANNER, "pt"

    def check_auth_password(self, username: str, password: str) -> int:
        return (
            paramiko.AUTH_SUCCESSFUL
            if password == SSH_PASSWORD
            else paramiko.AUTH_FAILED
        )

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *args, **kwargs) -> bool:
        return True

    def check_channel_shell_request(self, channel) -> bool:
        return True


# =======================
# Shell Interativo
# =======================

def handle_interactive_shell(channel: paramiko.Channel) -> None:
    master_fd, slave_fd = os.openpty()

    process = subprocess.Popen(
        [SHELL_PATH],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid
    )

    try:
        while True:
            readable, _, _ = select.select([channel, master_fd], [], [])

            if channel in readable:
                data = channel.recv(1024)
                if not data:
                    break
                os.write(master_fd, data)

            if master_fd in readable:
                output = os.read(master_fd, 1024)
                if not output:
                    break
                channel.send(output)

    except Exception as exc:
        logging.error(f"Erro no shell interativo: {exc}")

    finally:
        process.terminate()
        channel.close()
        os.close(master_fd)
        os.close(slave_fd)


# =======================
# Loop principal do servidor
# =======================

def start_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(BACKLOG)

        logging.info(f"Aguardando conexões em {HOST}:{PORT}")

        while True:
            client_socket, address = server_socket.accept()
            logging.info(f"Conexão recebida de {address}")

            try:
                transport = paramiko.Transport(client_socket)
                transport.add_server_key(HOST_KEY)

                server = SSHServer()
                transport.start_server(server=server)

                channel = transport.accept(20)
                if not channel:
                    logging.warning("Canal SSH não foi aberto")
                    continue

                handle_interactive_shell(channel)

            except Exception as exc:
                logging.error(f"Erro na conexão SSH: {exc}")

            finally:
                client_socket.close()


# =======================
# Entrada
# =======================

if __name__ == "__main__":
    start_server()
