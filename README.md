# Trabalho 1: Servidor HTTP/1.1 sobre Sockets TCP

**Laboratório de Redes de Computadores**  
**Escola Politécnica — PUCRS**  
**Protocolo:** HTTP/1.1 sobre sockets TCP puros (API de sockets BSD)

---

## 📌 Visão Geral

Este repositório contém a implementação completa de um **servidor HTTP/1.1 construído do zero diretamente sobre sockets TCP**, sem o uso de qualquer biblioteca ou framework de alto nível de HTTP (como `http.server`, `Flask`, `Express`, etc.). O parsing das mensagens, o gerenciamento de conexões persistentes, o controle de fluxo de bytes do TCP e a geração de respostas HTTP foram desenvolvidos artesanalmente.

O projeto foi projetado para ser **100% turnkey**: basta clonar ou baixar o repositório em qualquer computador com Python 3 instalado e executar. Nenhuma dependência externa (`pip`) é necessária, garantindo funcionamento imediato na VDI da universidade ou em qualquer sistema operacional (Windows, Linux, macOS).

---

## ⚡ Início Rápido com 1 Clique (Windows)

Você pode configurar e rodar tudo automaticamente dando **duplo clique** no arquivo:
```cmd
setup_ambiente.bat
```
ou executando no terminal:
```cmd
.\setup_ambiente.bat
```

### O que o script faz:
1. **Verifica o Python**: detecta se o Python já está instalado. Se não estiver, baixa automaticamente o **Python 3.11** oficial e instala em modo de usuário (*sem precisar de privilégios de administrador*).
2. **Pergunta sobre o VS Code**: se o VS Code não for detectado, pergunta se você deseja baixá-lo e instalá-lo automaticamente para visualizar e editar o projeto.
3. **Verifica a integridade dos arquivos**: gera automaticamente quaisquer arquivos de teste (`www/`), capturas para Wireshark (`capturas/`) e versão HTML do relatório (`RELATORIO.html`).
4. **Abre um menu interativo**:
   - `[1]` Rodar a bateria completa de 48 testes automatizados (`test_server.py`)
   - `[2]` Iniciar o servidor HTTP/1.1 (`server.py`)
   - `[3]` Rodar o benchmark comparativo C1 vs C2 (`benchmark.py`)
   - `[4]` Abrir a pasta do projeto no VS Code (`code .`)
   - `[5]` Visualizar o Relatório Técnico no navegador
   - `[0]` Sair

---

## 📁 Estrutura do Repositório

```text
├── server.py                 # Código-fonte principal do servidor HTTP/1.1
├── test_server.py            # Bateria automatizada de testes (valida tudo em 1 máquina só)
├── benchmark.py              # Script de medição de desempenho comparando C1 vs C2
├── generate_captures.py      # Gerador de arquivos .pcap de tráfego de rede para Wireshark
├── setup_www.py              # Gerador dos arquivos de teste e teste de interoperabilidade
├── RELATORIO.md              # Relatório técnico completo (cobre todos os 10 tópicos exigidos)
├── RELATORIO.html            # Versão HTML estilizada do relatório (Ctrl+P -> Salvar em PDF)
├── gerar_relatorio_html.py   # Utilitário para regenerar RELATORIO.html
├── README.md                 # Este documento de instruções
├── www/                      # Diretório raiz com arquivos servidos e teste de interoperabilidade
│   ├── index.html            # Página completa para teste de interoperabilidade
│   ├── style.css             # Folha de estilos CSS (text/css)
│   ├── app.js                # Script JavaScript interativo (application/javascript)
│   ├── dados.json            # Dados JSON para testes e medições (application/json)
│   ├── exemplo.txt           # Documento de texto (text/plain)
│   ├── imagem.png            # Imagem PNG binária válida (image/png)
│   ├── foto.jpg              # Foto JPEG binária válida (image/jpeg)
│   ├── documento.pdf         # Arquivo PDF binário válido (application/pdf)
│   ├── desconhecido.xyz      # Arquivo para validação de application/octet-stream
│   └── subpasta/sub.html     # Recurso em subdiretório
└── capturas/                 # Arquivos de captura de tráfego de rede para o Wireshark
    ├── c1.pcap (e .pcapng)   # Cenário C1: 10 conexões não-persistentes (Connection: close)
    ├── c2.pcap (e .pcapng)   # Cenário C2: 1 conexão persistente única (Keep-Alive)
    └── transacao_completa.*  # Captura detalhada de 1 transação GET completa
```

---

## 🚀 Como Executar o Servidor

O servidor executa com qualquer versão do Python 3 (3.8+) utilizando apenas módulos da biblioteca padrão.

### Comando Básico
```bash
python server.py --port 8080 --root ./www
```

### Argumentos de Linha de Comando Suportados
| Argumento | Forma Curta | Padrão | Descrição |
| :--- | :---: | :---: | :--- |
| `--port` | `-p` | `8080` | Porta TCP na qual o servidor escutará |
| `--root` | `-r` | `./www` | Caminho do diretório raiz de arquivos a ser servido |
| `--host` | | `0.0.0.0` | Endereço IP de *bind* (escuta em todas as interfaces) |
| `--timeout` | `-t` | `5.0` | Timeout de conexão ociosa em segundos (Keep-Alive) |

Exemplo de execução customizada:
```bash
python server.py --port 9090 --root ./www --timeout 5.0
```

---

## 🧪 Bateria de Testes Automatizada (Em uma Máquina Só)

Para validar todos os requisitos mesmo quando não se tem acesso a uma segunda máquina na rede, foi desenvolvida uma **bateria completa de testes automatizados**:

```bash
python test_server.py
```

### O que a bateria de testes valida automaticamente:
1. **Status 200 OK e Cabeçalhos Obrigatórios:** Valida `Date` (IMF-fixdate GMT conforme RFC 9110), `Server`, `Content-Length`, `Content-Type` e resolução de `/` para `index.html`.
2. **Todos os Tipos MIME Exigidos:** Testa extensões `.html`, `.css`, `.js`, `.json`, `.txt`, `.png`, `.jpg`, `.pdf` e arquivos sem extensão reconhecida (`application/octet-stream`).
3. **Método HEAD:** Valida que a resposta contém status 200 e exatamente os mesmos cabeçalhos do GET correspondente (mesmo `Content-Length`), **sem corpo** (0 bytes recebidos).
4. **Status 405 Method Not Allowed:** Testa envio de `POST`, `PUT`, `DELETE`, validando o retorno do status 405 e do cabeçalho obrigatório `Allow: GET, HEAD`.
5. **Status 404 Not Found:** Requisita arquivos inexistentes e diretórios sem `index.html`.
6. **Status 400 Bad Request:** Testa requisições malformadas, request-line inválida e cabeçalhos sem dois-pontos (`:`).
7. **Segurança (Directory Traversal - 403 Forbidden):**
   - Tentativa 1: Caminho relativo clássico (`/../../Windows/...`).
   - Tentativa 2: *Percent-encoding* simples (`/%2e%2e/%2e%2e/...`).
   - Tentativa 3: *Percent-encoding* misto com subdiretórios (`/subpasta/%2e%2e/%2e%2e/...`).
   - Tentativa 4: *Percent-encoding* de barras (`/%2e%2e%2f%2e%2e%2f...`).
8. **Conexões Persistentes (Cenário C2):** Executa 10 requisições sequenciais usando **a mesma conexão TCP** sem reconectar.
9. **Encerramento de Conexão (Cenário C1):** Envia `Connection: close`, confirmando que o servidor responde com `Connection: close` e encerra o socket TCP.
10. **Timeout de Conexão Ociosa:** Abre uma conexão, faz uma requisição e aguarda o tempo de inatividade para validar o fechamento automático pelo servidor.
11. **Fluxo Contínuo e Fragmentação TCP:** Envia bytes fragmentados byte-a-byte e duas requisições coladas no mesmo buffer, testando a resiliência do buffer acumulador.
12. **Concorrência Simultânea:** Dispara 10 conexões cliente concorrentes disparadas no mesmo milissegundo, validando que todas são atendidas em paralelo sem bloqueio mútuo.

---

## 📊 Medição de Desempenho e Comparação (C1 vs C2)

O script `benchmark.py` realiza a medição dos dois cenários da Parte 2:
- **C1:** 10 conexões consecutivas (1 conexão por requisição com `Connection: close`).
- **C2:** 1 conexão persistente única (reutilizada para as 10 requisições).

### Como Rodar Localmente
Em um terminal com o servidor em execução:
```bash
python benchmark.py --port 8080
```

### Como Rodar Entre Máquinas Distintas (No Lab da PUCRS)
Na máquina cliente, aponte para o IP do servidor:
```bash
python benchmark.py --host 192.168.1.50 --port 8080
```

O script exibirá no terminal a tabela comparativa formatada com:
- Número de Handshakes TCP completos
- Estimativa de pacotes TCP de controle e dados
- Bytes totais trafegados
- Tempo total decorrido em milissegundos
- Economia percentual de tempo e pacotes proporcionada pelo Keep-Alive

---

## 🌐 Teste de Interoperabilidade com Outro Grupo

Durante a apresentação em aula:
1. Conecte sua máquina e a máquina do outro grupo na mesma rede local.
2. Descubra o IP da sua máquina (`ipconfig` no Windows ou `ip a` no Linux).
3. Inicie o servidor:
   ```bash
   python server.py --port 8080 --root ./www
   ```
4. Na máquina do outro grupo, abra o navegador e acesse:
   ```text
   http://<SEU_IP>:8080/
   ```
5. A página `www/index.html` carregará automaticamente:
   - Folha de estilos CSS (`style.css`)
   - Script JavaScript interativo (`app.js`)
   - Imagens binárias PNG e JPEG referenciadas
   - Botão interativo para carregar `dados.json` dinamicamente via Fetch/AJAX na mesma conexão persistente
   - Links para download e visualização do PDF (`documento.pdf`) e texto (`exemplo.txt`).

---

## 🦈 Capturas Wireshark

O diretório `capturas/` já contém as capturas de tráfego de rede salvas:
- `capturas/c1.pcap` / `c1.pcapng`: Cenário C1 (10 conexões não-persistentes com 10 handshakes e encerramentos).
- `capturas/c2.pcap` / `c2.pcapng`: Cenário C2 (1 conexão persistente única para 10 requisições).
- `capturas/transacao_completa.pcap` / `.pcapng`: Transação completa isolada de um GET bem-sucedido.

Para abrir e inspecionar no Wireshark:
1. Abra o arquivo desejado no Wireshark.
2. Utilize o filtro de exibição:
   ```text
   tcp.port == 8080
   ```
   ou
   ```text
   http
   ```

Se desejar regenerar os arquivos de captura:
```bash
python generate_captures.py
```

---

## 📄 Relatório Técnico

O documento completo com todas as 10 seções exigidas pelo trabalho está disponível em:
- [RELATORIO.md](file:///c:/Users/diego.mello.ENERGPOWER/Documents/trabredes/RELATORIO.md)
- [RELATORIO.html](file:///c:/Users/diego.mello.ENERGPOWER/Documents/trabredes/RELATORIO.html)

Para gerar o **Relatório em PDF**:
1. Dê um duplo clique ou abra `RELATORIO.html` em qualquer navegador (Chrome, Edge ou Firefox).
2. Pressione `Ctrl + P` (Imprimir).
3. Selecione a opção **"Salvar como PDF"** e clique em **Salvar**.
