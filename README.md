# SSH em Python

- Funciona apenas em Linux. Depende do `paramiko` Tem suporte a senhas e PTY

### Configura o ambiente
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### Definir a senha
```export SSH_PASSWORD='senha123'```

### Sobe o servidor

```python3 ssh_server_python.py```