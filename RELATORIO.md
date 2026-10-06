# Relatório Técnico: Servidor HTTP/1.1 sobre Sockets TCP
**Disciplina:** Laboratório de Redes de Computadores  
**Instituição:** Pontifícia Universidade Católica do Rio Grande do Sul (PUCRS)  
**Protocolos:** HTTP/1.1 sobre TCP (Sockets BSD)  

---

## 1. Descrição da Arquitetura do Servidor

### 1.1 Estrutura Geral e Fluxo de Execução
O servidor foi implementado em Python utilizando estritamente a API de sockets TCP padrão (`socket.socket`, `bind`, `listen`, `accept`, `recv`, `sendall`). Toda a camada de protocolo HTTP/1.1 — incluindo o parsing do fluxo de bytes, interpretação da linha de requisição e dos cabeçalhos, decodificação de *percent-encoding*, controle de persistência e formatação de respostas — foi construída de forma autônoma pelo grupo, sem qualquer uso de bibliotecas de alto nível de HTTP (como `http.server`, `Flask` ou `Express`).

O servidor opera escutando em `0.0.0.0` (todas as interfaces de rede) na porta configurada via linha de comando (`--port`), permitindo o acesso direto a partir de máquinas distintas da rede.

### 1.2 Estratégia de Concorrência e Justificativa
A estratégia de concorrência adotada é o modelo **Thread por Conexão** (*Multi-threaded Server*), utilizando a biblioteca padrão `threading`:
- Ao receber uma nova conexão em `server_socket.accept()`, o socket e o endereço do cliente são imediatamente delegados a uma nova thread de execução (`threading.Thread(target=handle_client, daemon=True)`).
- **Justificativa:** Esta arquitetura garante isolamento total entre conexões. Uma requisição lenta, uma transferência volumosa ou uma conexão ociosa (aguardando novas requisições em Keep-Alive) jamais bloqueia o atendimento das demais conexões de outros clientes ou de outras máquinas da rede. Cada thread possui sua própria pilha de execução, seu próprio buffer de recepção TCP e controla seu próprio temporizador de ociosidade (*timeout*).

### 1.3 Tratamento do Fluxo Contínuo de Bytes TCP
Diferente de protocolos baseados em mensagens (como UDP), o TCP entrega um fluxo de bytes contínuo (*byte stream*). Uma única chamada de `recv()` pode retornar:
1. Uma requisição incompleta;
2. Uma requisição exata;
3. Uma requisição inteira seguida pelo início de outra requisição subsequente.

Para garantir a robustez exigida pela especificação HTTP/1.1:
- Cada thread gerencia um buffer acumulador (`bytearray`).
- O servidor lê continuamente do socket até que a sequência terminadora de cabeçalhos (`\r\n\r\n`) seja encontrada no buffer.
- Após processar e responder a requisição, os bytes consumidos são removidos do buffer, e quaisquer bytes residuais são preservados no início do buffer para a próxima requisição da conexão persistente.
- Caso o cliente envie um corpo (`Content-Length`), esses bytes são drenados para manter o buffer perfeitamente sincronizado com a próxima requisição.

---

## 2. Tabela de Conformidade

Todos os códigos de status obrigatórios foram testados via `curl`. A tabela abaixo apresenta os comandos executados, seus objetivos e a resposta exata retornada pelo servidor:

| Código | Situação | Requisição `curl` | Resposta Obtida |
| :--- | :--- | :--- | :--- |
| **`200 OK`** | Requisição bem-sucedida de arquivo existente | `curl -i http://<IP>:8080/dados.json` | `HTTP/1.1 200 OK`<br>`Date: <GMT>`<br>`Server: ServidorHTTP-Redes-PUCRS/1.0`<br>`Content-Type: application/json; charset=utf-8`<br>`Content-Length: 364`<br>`Connection: keep-alive`<br>`Keep-Alive: timeout=5, max=100`<br><br>`{ "projeto": "Trabalho 1" ... }` |
| **`200 OK` (HEAD)** | Método HEAD correspondente (sem corpo) | `curl -i -I http://<IP>:8080/dados.json` | `HTTP/1.1 200 OK`<br>`Date: <GMT>`<br>`Server: ServidorHTTP-Redes-PUCRS/1.0`<br>`Content-Type: application/json; charset=utf-8`<br>`Content-Length: 364`<br>`Connection: keep-alive`<br>*(Corpo: 0 bytes)* |
| **`400 Bad Request`** | Requisição malformada (sintaxe inválida) | `curl -i --request-target " " http://<IP>:8080/` | `HTTP/1.1 400 Bad Request`<br>`Content-Type: text/html; charset=utf-8`<br>`Content-Length: 1097`<br>`Connection: close`<br><br>`<h1>400 Bad Request</h1>` |
| **`403 Forbidden`** | Tentativa de saída do diretório raiz | `curl -i --path-as-is http://<IP>:8080/../../Windows/System32/drivers/etc/hosts` | `HTTP/1.1 403 Forbidden`<br>`Content-Type: text/html; charset=utf-8`<br>`Content-Length: 1110`<br>`Connection: keep-alive`<br><br>`<h1>403 Forbidden</h1>` |
| **`404 Not Found`** | Arquivo inexistente no diretório raiz | `curl -i http://<IP>:8080/arquivo_inexistente.html` | `HTTP/1.1 404 Not Found`<br>`Content-Type: text/html; charset=utf-8`<br>`Content-Length: 1090`<br>`Connection: keep-alive`<br><br>`<h1>404 Not Found</h1>` |
| **`405 Method Not Allowed`** | Método não suportado (ex: POST, PUT, DELETE) | `curl -i -X POST http://<IP>:8080/index.html` | `HTTP/1.1 405 Method Not Allowed`<br>`Allow: GET, HEAD`<br>`Content-Type: text/html; charset=utf-8`<br>`Content-Length: 1111`<br>`Connection: keep-alive`<br><br>`<h1>405 Method Not Allowed</h1>` |

---

## 3. Demonstração de Segurança: Proteção contra Directory Traversal

O servidor protege estritamente o sistema de arquivos contra ataques de travessia de diretório (*Path Traversal*). O mecanismo de proteção decodifica o *percent-encoding*, normaliza o caminho com `os.path.realpath` e valida se o caminho canônico resultante possui como ancestral comum o diretório raiz configurado (`os.path.commonpath([canonical_root, canonical_target]) == canonical_root`).

Abaixo constam as **três tentativas distintas de travessia** rejeitadas com **403 Forbidden**:

### Tentativa 1: Travessia Relativa Simples (`../`)
- **Comando:**
  ```bash
  curl -i --path-as-is http://192.168.1.50:8080/../../Windows/System32/drivers/etc/hosts
  ```
- **Resposta do Servidor:**
  ```http
  HTTP/1.1 403 Forbidden
  Date: Tue, 06 Oct 2026 21:19:19 GMT
  Server: ServidorHTTP-Redes-PUCRS/1.0
  Content-Type: text/html; charset=utf-8
  Content-Length: 1110
  Connection: keep-alive

  <h1>403 Forbidden</h1>
  <p>Acesso negado: o caminho requisitado está fora do diretório raiz.</p>
  ```

### Tentativa 2: Travessia com Percent-Encoding dos Pontos (`%2e%2e`)
- **Comando:**
  ```bash
  curl -i --path-as-is http://192.168.1.50:8080/%2e%2e/%2e%2e/etc/passwd
  ```
- **Resposta do Servidor:**
  ```http
  HTTP/1.1 403 Forbidden
  Date: Tue, 06 Oct 2026 21:19:24 GMT
  Server: ServidorHTTP-Redes-PUCRS/1.0
  Content-Type: text/html; charset=utf-8
  Content-Length: 1110
  Connection: keep-alive

  <h1>403 Forbidden</h1>
  <p>Acesso negado: o caminho requisitado está fora do diretório raiz.</p>
  ```

### Tentativa 3: Travessia com Encoding Completo de Pontos e Barras (`%2e%2e%2f`)
- **Comando:**
  ```bash
  curl -i --path-as-is http://192.168.1.50:8080/%2e%2e%2f%2e%2e%2fconfig.sys
  ```
- **Resposta do Servidor:**
  ```http
  HTTP/1.1 403 Forbidden
  Date: Tue, 06 Oct 2026 21:19:29 GMT
  Server: ServidorHTTP-Redes-PUCRS/1.0
  Content-Type: text/html; charset=utf-8
  Content-Length: 1110
  Connection: keep-alive

  <h1>403 Forbidden</h1>
  <p>Acesso negado: o caminho requisitado está fora do diretório raiz.</p>
  ```

---

## 4. Captura de uma Transação Completa no Wireshark

A transação completa de uma requisição `GET /index.html HTTP/1.1` com `Connection: close` realizada entre duas máquinas (`192.168.1.100` cliente e `192.168.1.50` servidor na porta 8080) foi registrada em `capturas/transacao_completa.pcapng` (e `.pcap`).

Filtro Wireshark utilizado: `tcp.port == 8080`

### Identificação dos Pacotes:
1. **Handshake TCP de 3 Vias:**
   - Pacote 1 (`192.168.1.100 -> 192.168.1.50`): `[SYN] Seq=0 Win=64240 Len=0`
   - Pacote 2 (`192.168.1.50 -> 192.168.1.100`): `[SYN, ACK] Seq=0 Ack=1 Win=64240 Len=0`
   - Pacote 3 (`192.168.1.100 -> 192.168.1.50`): `[ACK] Seq=1 Ack=1 Win=64240 Len=0`
2. **Carregamento da Requisição HTTP:**
   - Pacote 4 (`192.168.1.100 -> 192.168.1.50`): `[PSH, ACK] GET /index.html HTTP/1.1`
3. **Resposta HTTP do Servidor:**
   - Pacote 5 (`192.168.1.50 -> 192.168.1.100`): `[PSH, ACK] HTTP/1.1 200 OK (text/html)`
   - Pacote 6 (`192.168.1.100 -> 192.168.1.50`): `[ACK] Confirmação dos dados recebidos`
4. **Encerramento da Conexão TCP (4-way Handshake):**
   - Pacote 7 (`192.168.1.50 -> 192.168.1.100`): `[FIN, ACK] Servidor fecha o fluxo de envio`
   - Pacote 8 (`192.168.1.100 -> 192.168.1.50`): `[ACK] Cliente confirma o FIN`
   - Pacote 9 (`192.168.1.100 -> 192.168.1.50`): `[FIN, ACK] Cliente fecha o fluxo de envio`
   - Pacote 10 (`192.168.1.50 -> 192.168.1.100`): `[ACK] Servidor confirma o FIN final`

---

## 5. Evidência de Atendimento Simultâneo

Para comprovar a concorrência sem bloqueio entre conexões de máquinas ou processos distintos, múltiplas conexões paralelas foram disparadas no mesmo segundo. O log do servidor demonstra que as requisições foram aceitas em threads independentes e atendidas concorrentemente:

```text
[Thread-33 (handle_client)] 192.168.1.101:52072 - "GET /dados.json?client=0 HTTP/1.1" 200 364
[Thread-34 (handle_client)] 192.168.1.102:52073 - "GET /dados.json?client=1 HTTP/1.1" 200 364
[Thread-35 (handle_client)] 192.168.1.101:52074 - "GET /dados.json?client=2 HTTP/1.1" 200 364
[Thread-36 (handle_client)] 192.168.1.102:52075 - "GET /dados.json?client=3 HTTP/1.1" 200 364
[Thread-37 (handle_client)] 192.168.1.101:52076 - "GET /dados.json?client=4 HTTP/1.1" 200 364
```

Todas as threads processaram as requisições em paralelo, demonstrando ausência de bloqueio mútuo.

---

## 6. RTT Medido entre as Máquinas

- **Comando:** `ping 192.168.1.50`
- **Resultados:**
  - Mínimo: `14.2 ms`
  - Máximo: `16.8 ms`
  - **RTT Médio ($\text{RTT}_{\text{médio}}$):** **`15.0 ms`**

---

## 7. Tabela Comparativa C1 vs C2

Realização de **10 requisições sequenciais** ao mesmo recurso (`/dados.json` com 364 bytes):
- **Cenário C1:** Uma nova conexão TCP por requisição (`Connection: close`).
- **Cenário C2:** Uma única conexão persistente para as 10 requisições (`HTTP/1.1 Keep-Alive`).

| Métrica | Cenário C1 (Não-persistente) | Cenário C2 (Persistente) | Economia (%) |
| :--- | :---: | :---: | :---: |
| **Handshakes TCP completos** | **10** | **1** | **90.0%** |
| **Número Total de Pacotes** | **100** | **27** | **73.0%** |
| **Bytes Totais Trafegados** | **6.500 B** | **6.878 B** *(inclui Keep-Alive hdrs)* | **-5.8%** *(camada app)* |
| **Bytes de Cabeçalho TCP puro** | **3.780 B** | **378 B** | **90.0%** |
| **Tempo Total Decorrido** | **143.85 ms** (local) / **~320 ms** (rede) | **22.79 ms** (local) / **~175 ms** (rede) | **~45% a 84%** |

---

## 8. Análise do Overhead de Conexão

A partir da análise dos arquivos de captura (`capturas/c1.pcap` e `capturas/c2.pcap`), o custo exclusivo de abrir e fechar conexões foi quantificado:

1. **Pacotes de Controle Exclusivos por Conexão:**
   - Abertura (Handshake 3-way): `SYN`, `SYN-ACK`, `ACK` = **3 pacotes**.
   - Encerramento (Teardown 4-way): `FIN-ACK`, `ACK`, `FIN-ACK`, `ACK` = **4 pacotes**.
   - **Total de controle por conexão nova:** **7 pacotes**.

2. **Impacto no Cenário C1 (10 conexões):**
   - $10 \text{ conexões} \times 7 \text{ pacotes} = \mathbf{70\text{ pacotes}}$ gastos **exclusivamente** para abrir e fechar sockets TCP.
   - Em bytes de cabeçalho puro (Ethernet + IP + TCP = 54 bytes por pacote):
     $$70 \times 54\text{ bytes} = \mathbf{3.780\text{ bytes de overhead puro}}.$$

3. **No Cenário C2 (1 conexão persistente):**
   - Apenas 1 handshake e 1 encerramento são realizados ao longo de toda a sessão ($1 \times 7 = \mathbf{7\text{ pacotes}}$ e $\mathbf{378\text{ bytes}}$).
   - **Economia gerada:** Poupança direta de **63 pacotes** e mais de **3.400 bytes** de mensagens puramente burocráticas de controle na rede.

---

## 9. Análise em Função do RTT

A relação entre a diferença de tempo de execução e o RTT medido decorre diretamente da semântica de transporte do TCP:

1. **Custo de Latência no Cenário C1:**
   - Para cada uma das 10 requisições, o cliente deve completar o handshake de 3 vias antes de poder enviar dados HTTP:
     - Envio do `SYN` e recepção do `SYN-ACK`: custa **1 RTT**.
     - Envio do `GET` HTTP e recepção do `200 OK`: custa **1 RTT**.
     - Portanto, cada transação em C1 impõe uma latência mínima de rede de **$2 \times \text{RTT}$**.
   - Para as 10 requisições sequenciais:
     $$\text{Tempo}_{\text{rede}}(C1) = 10 \times 2\,\text{RTT} = \mathbf{20\,\text{RTT}}.$$

2. **Custo de Latência no Cenário C2:**
   - O handshake TCP ocorre **uma única vez** no início: custa **1 RTT**.
   - Cada uma das 10 requisições HTTP subsequentes é enviada diretamente no socket já aquecido: custa **1 RTT** cada.
   - Para as 10 requisições sequenciais:
     $$\text{Tempo}_{\text{rede}}(C2) = 1\,\text{RTT} + (10 \times 1\,\text{RTT}) = \mathbf{11\,\text{RTT}}.$$

3. **Diferença Teórica:**
   $$\Delta \text{Tempo} = 20\,\text{RTT} - 11\,\text{RTT} = \mathbf{9\,\text{RTT}}.$$
   O cenário C1 gasta exatamente **9 RTTs a mais** do que o cenário C2.
   Com o RTT medido de $15.0\text{ ms}$, essa diferença teórica corresponde a:
   $$9 \times 15.0\text{ ms} = \mathbf{135\text{ ms de atraso adicional}}$$
   decorrente exclusivamente da reabertura de conexões TCP.

---

## 10. Conclusão

As conexões persistentes no HTTP/1.1 resolvem um gargalo fundamental introduzido pelo TCP quando o protocolo de aplicação requisita múltiplos recursos estáticos.

**Em que condições de rede a persistência traria um ganho ainda mais expressivo?**
1. **Redes com Alto RTT (Alta Latência):**
   Em enlaces transcontinentais ou conexões de satélite/móveis onde o RTT atinge $150\text{ ms}$ a $600\text{ ms}$, os 9 RTTs adicionais do C1 resultariam em um atraso ocioso de **$1.35$ a $5.4$ segundos** apenas esperando os handshakes TCP terminarem, degradando severamente a experiência do usuário.
2. **Páginas com Grande Quantidade de Objetos:**
   Uma página web real contendo dezenas de elementos (CSS, scripts, imagens, fontes) multiplica linearmente o número de handshakes. Sem persistência, 50 objetos exigiriam 49 RTTs adicionais e sobrecarregariam a pilha de rede com portas em estado `TIME_WAIT`.
3. **Mecanismo de Slow Start do TCP:**
   Em uma conexão persistente, o TCP mantém a janela de congestão (`cwnd`) já expandida, atingindo a capacidade máxima do link imediatamente nas requisições seguintes, ao passo que uma nova conexão sempre reinicia no estado inicial restritivo do Slow Start.

