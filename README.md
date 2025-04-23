# ollama-wsl2

Este repositório fornece um tutorial passo a passo para configurar e executar um servidor XML-RPC com uma LLM local utilizando o Ollama em um ambiente Linux (como o WSL2).

O exemplo de código implementa um agente capaz de gerar consultas SQL com base em perguntas em linguagem natural, utilizando como contexto um esquema de banco de dados em formato JSON.

---

## Requisitos

Antes de iniciar, verifique se você possui:

1. Uma máquina Linux com:
   - GPU NVIDIA (arquitetura **Maxwell** ou superior)
   - Mínimo de **8 GB de VRAM**
   - Drivers atualizados

2. Conta no [Ngrok](https://dashboard.ngrok.com/get-started/your-authtoken) com token de autenticação válido

3. Python 3 instalado com suporte a ambientes virtuais (`venv`)  
   - Recomendado: **Python 3.12.3**

---

## Instalação e Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/luiz-bcardoso/ollama-wsl2
cd ollama-wsl2
```

### 2. Crie e ative um ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências do Python

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Instale as dependências do sistema

```bash
sudo apt update
sudo apt install pciutils
```

### 5. Instale o Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 6. Configure o token do Ngrok

```bash
ngrok authtoken <SEU_TOKEN_AQUI>
```

### 7. Execute o servidor

```bash
python main.py
```

Você verá uma saída semelhante a:

```
...
URL Pública: <COPIE_ESSA_URL>
Servidor XML-RPC em execução...
```
