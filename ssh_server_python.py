import socket
import threading
import paramiko
import subprocess
import os
import select

CUSTOM_BANNER = "Bem-vindo ao servidor!\n"

SENHA = "senha123"

host_key = paramiko.RSAKey.generate(2048)

class SSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def get_banner(self):
        return CUSTOM_BANNER, "pt"

    def check_auth_password(self, username, password):
        if password == SENHA:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True  # ✅ Aceita requisição de PTY

    def check_channel_shell_request(self, channel):
        return True  # ✅ Aceita requisição de shell

def lidar_com_shell_interativo(chan):
    # Cria um par de pseudo-terminals
    master_fd, slave_fd = os.openpty()

    # Inicia o shell interativo
    shell = subprocess.Popen(
        ["/bin/bash"],
        preexec_fn=os.setsid,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        universal_newlines=True
    )

    # Redireciona entrada/saída entre o canal SSH e o shell
    try:
        while True:
            rlist, _, _ = select.select([chan, master_fd], [], [])
            if chan in rlist:
                data = chan.recv(1024)
                if not data:
                    break
                os.write(master_fd, data)
            if master_fd in rlist:
                output = os.read(master_fd, 1024)
                if not output:
                    break
                chan.send(output)
    except Exception as e:
        print(f"[-] Erro no shell interativo: {e}")
    finally:
        chan.close()
        shell.terminate()
        os.close(master_fd)
        os.close(slave_fd)

def iniciar_servidor():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", 3333))
    sock.listen(100)
    print("[+] Aguardando conexão na porta 3333...")

    while True:
        client, addr = sock.accept()
        print(f"[+] Conexão recebida de {addr}")

        try:
            transport = paramiko.Transport(client)
            transport.add_server_key(host_key)
            server = SSHServer()
            transport.start_server(server=server)

            chan = transport.accept(20)
            if chan is None:
                print("[-] Canal não aberto")
                continue

            lidar_com_shell_interativo(chan)

        except Exception as e:
            print(f"[-] Erro: {e}")
        finally:
            client.close()

if __name__ == "__main__":
    iniciar_servidor()

