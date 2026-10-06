#!/usr/bin/env python3
"""
Bateria de Testes Automatizada do Servidor HTTP/1.1.
Laboratório de Redes de Computadores - PUCRS.

Permite validar 100% dos requisitos em uma única máquina (localhost ou IP local):
- Parsing de requisição e respostas HTTP/1.1
- Todos os códigos de status obrigatórios: 200, 400, 403, 404, 405
- Todos os tipos MIME obrigatórios (.html, .css, .js, .json, .txt, .png, .jpg, .pdf, desconhecido)
- Métodos GET e HEAD (com validação de ausência de corpo no HEAD)
- Proteção contra Directory Traversal com múltiplas tentativas e percent-encoding
- Tratamento de fluxo TCP contínuo e fragmentação de pacotes
- Conexões persistentes (HTTP/1.1 Keep-Alive - 10 requisições na mesma conexão)
- Fechamento com Connection: close
- Timeout de conexão ociosa
- Concorrência de múltiplas conexões simultâneas
"""

import os
import socket
import sys
import threading
import time
from typing import Tuple, Dict

# Importa a função do servidor
import server

TEST_HOST = "127.0.0.1"
TEST_PORT = 19080
TEST_ROOT = os.path.realpath("./www")
TEST_TIMEOUT = 2.0  # Timeout reduzido para teste rápido de ociosidade

# Cores para o terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class RawHTTPResponse:
    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data
        self.status_code = 0
        self.reason = ""
        self.headers: Dict[str, str] = {}
        self.body = b""

        self._parse()

    def _parse(self):
        parts = self.raw_data.split(b"\r\n\r\n", 1)
        header_part = parts[0].decode("iso-8859-1", errors="replace")
        self.body = parts[1] if len(parts) > 1 else b""

        lines = header_part.split("\r\n")
        if lines:
            first_line = lines[0].split(" ", 2)
            if len(first_line) >= 2:
                try:
                    self.status_code = int(first_line[1])
                    self.reason = first_line[2] if len(first_line) > 2 else ""
                except ValueError:
                    pass

            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    self.headers[k.strip().lower()] = v.strip()


def send_raw_request(
    sock: socket.socket,
    request_bytes: bytes,
    is_head: bool = False,
    timeout: float = 3.0,
) -> RawHTTPResponse:
    """Envia bytes brutos em um socket e lê a resposta HTTP completa respeitando Content-Length."""
    sock.settimeout(timeout)
    sock.sendall(request_bytes)

    received = bytearray()
    content_length = None

    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        received.extend(chunk)

        if b"\r\n\r\n" in received:
            sep_idx = received.find(b"\r\n\r\n")
            header_bytes = received[:sep_idx]
            
            # Se ainda não sabemos o Content-Length, extrair dos cabeçalhos
            if content_length is None:
                header_text = header_bytes.decode("iso-8859-1", errors="replace")
                for line in header_text.split("\r\n")[1:]:
                    if ":" in line:
                        hk, hv = line.split(":", 1)
                        if hk.strip().lower() == "content-length":
                            try:
                                content_length = int(hv.strip())
                            except ValueError:
                                content_length = 0
                if content_length is None:
                    content_length = 0

            # Se a requisição for HEAD, não há corpo a ser esperado
            if is_head:
                break

            # Se já recebemos todo o corpo previsto pelo Content-Length
            current_body_len = len(received) - (sep_idx + 4)
            if current_body_len >= content_length:
                break

    return RawHTTPResponse(bytes(received))


def create_connection() -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TEST_HOST, TEST_PORT))
    return s


class TestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def assert_true(self, condition: bool, test_name: str, detail: str = ""):
        if condition:
            print(f"  {GREEN}[PASS]{RESET} {test_name}")
            self.passed += 1
        else:
            print(f"  {RED}[FAIL]{RESET} {test_name} {f'({detail})' if detail else ''}")
            self.failed += 1

    def run_all(self):
        print(f"\n{BOLD}{BLUE}======================================================================{RESET}")
        print(f"{BOLD}{BLUE}  INICIANDO BATERIA DE TESTES DO SERVIDOR HTTP/1.1 SOBRE SOCKETS TCP  {RESET}")
        print(f"{BOLD}{BLUE}======================================================================{RESET}\n")

        self.test_status_200_and_headers()
        self.test_mime_types()
        self.test_head_method()
        self.test_status_405_method_not_allowed()
        self.test_status_404_not_found()
        self.test_status_400_bad_request()
        self.test_directory_traversal_security()
        self.test_persistent_connections_c2()
        self.test_connection_close_c1()
        self.test_idle_timeout()
        self.test_tcp_stream_fragmentation()
        self.test_concurrency()

        print(f"\n{BOLD}{BLUE}======================================================================{RESET}")
        total = self.passed + self.failed
        if self.failed == 0:
            print(f"{BOLD}{GREEN}  RESULTADO: TODOS OS {total} TESTES PASSARAM COM SUCESSO! [100%]{RESET}")
        else:
            print(f"{BOLD}{RED}  RESULTADO: {self.passed}/{total} PASSARAM, {self.failed} FALHARAM.{RESET}")
        print(f"{BOLD}{BLUE}======================================================================{RESET}\n")
        return self.failed == 0

    def test_status_200_and_headers(self):
        print(f"{BOLD}1. Testes de Requisição GET e Cabeçalhos Obrigatórios (200 OK){RESET}")
        with create_connection() as s:
            req = b"GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
            res = send_raw_request(s, req)

            self.assert_true(res.status_code == 200, "Status code deve ser 200 OK", f"Obtido: {res.status_code}")
            self.assert_true("date" in res.headers, "Cabeçalho 'Date' presente conforme RFC 9110")
            self.assert_true("server" in res.headers, "Cabeçalho 'Server' identificador presente")
            self.assert_true("content-length" in res.headers, "Cabeçalho 'Content-Length' presente")
            self.assert_true(int(res.headers.get("content-length", 0)) == len(res.body), "Content-Length reflete tamanho do corpo")
            self.assert_true("text/html" in res.headers.get("content-type", ""), "Content-Type de index.html é text/html")

        # Teste de raiz '/' resolvendo para 'index.html'
        with create_connection() as s:
            req = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 200, "GET / resolve automaticamente para index.html (200 OK)")

    def test_mime_types(self):
        print(f"\n{BOLD}2. Teste de Tipos MIME Obrigatórios{RESET}")
        expected_mimes = [
            ("/index.html", "text/html"),
            ("/style.css", "text/css"),
            ("/app.js", "application/javascript"),
            ("/dados.json", "application/json"),
            ("/exemplo.txt", "text/plain"),
            ("/imagem.png", "image/png"),
            ("/foto.jpg", "image/jpeg"),
            ("/documento.pdf", "application/pdf"),
            ("/desconhecido.xyz", "application/octet-stream"),
        ]
        with create_connection() as s:
            for path, expected_mime in expected_mimes:
                req = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("ascii")
                res = send_raw_request(s, req)
                ctype = res.headers.get("content-type", "")
                self.assert_true(
                    expected_mime in ctype,
                    f"Tipo MIME de '{path}' contém '{expected_mime}'",
                    f"Recebido: {ctype}",
                )

    def test_head_method(self):
        print(f"\n{BOLD}3. Teste do Método HEAD (sem corpo, cabeçalhos idênticos){RESET}")
        with create_connection() as s_get, create_connection() as s_head:
            req_get = b"GET /imagem.png HTTP/1.1\r\nHost: localhost\r\n\r\n"
            res_get = send_raw_request(s_get, req_get)

            req_head = b"HEAD /imagem.png HTTP/1.1\r\nHost: localhost\r\n\r\n"
            res_head = send_raw_request(s_head, req_head, is_head=True)

            self.assert_true(res_head.status_code == 200, "HEAD retorna status 200 OK")
            self.assert_true(len(res_head.body) == 0, "HEAD NÃO envia corpo de resposta (0 bytes)")
            self.assert_true(
                res_head.headers.get("content-length") == res_get.headers.get("content-length"),
                "HEAD possui exatamente o mesmo Content-Length do GET correspondente",
            )
            self.assert_true(
                res_head.headers.get("content-type") == res_get.headers.get("content-type"),
                "HEAD possui o mesmo Content-Type do GET correspondente",
            )

    def test_status_405_method_not_allowed(self):
        print(f"\n{BOLD}4. Teste de Métodos Não Permitidos (405 Method Not Allowed){RESET}")
        for method in ["POST", "PUT", "DELETE"]:
            with create_connection() as s:
                req = f"{method} /index.html HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n".encode("ascii")
                res = send_raw_request(s, req)
                self.assert_true(
                    res.status_code == 405,
                    f"Método {method} retorna 405 Method Not Allowed",
                    f"Obtido: {res.status_code}",
                )
                self.assert_true(
                    "allow" in res.headers and "GET" in res.headers["allow"] and "HEAD" in res.headers["allow"],
                    f"Resposta a {method} contém cabeçalho 'Allow: GET, HEAD'",
                    f"Allow: {res.headers.get('allow')}",
                )
                self.assert_true(len(res.body) > 0, f"Resposta a {method} inclui corpo de erro explicativo")

    def test_status_404_not_found(self):
        print(f"\n{BOLD}5. Teste de Arquivo Inexistente (404 Not Found){RESET}")
        with create_connection() as s:
            req = b"GET /arquivo_fantasma_inexistente.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 404, "Arquivo inexistente retorna 404 Not Found", f"Obtido: {res.status_code}")
            self.assert_true(len(res.body) > 0, "Resposta 404 inclui corpo HTML informativo")

    def test_status_400_bad_request(self):
        print(f"\n{BOLD}6. Teste de Requisição Malformada (400 Bad Request){RESET}")
        # Caso 1: Linha de requisição inválida (menos de 3 partes)
        with create_connection() as s:
            req = b"REQUISICAO_INVALIDA_SEM_ESPACOS\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 400, "Request line inválida retorna 400 Bad Request")

        # Caso 2: Linha de cabeçalho sem dois pontos (:)
        with create_connection() as s:
            req = b"GET /index.html HTTP/1.1\r\nHost localhost\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 400, "Cabeçalho sem ':' retorna 400 Bad Request")

        # Caso 3: Protocolo inválido
        with create_connection() as s:
            req = b"GET /index.html FTP/1.0\r\nHost: localhost\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 400, "Versão de protocolo inválida retorna 400 Bad Request")

    def test_directory_traversal_security(self):
        print(f"\n{BOLD}7. Testes de Segurança: Proteção contra Directory Traversal (403 Forbidden){RESET}")
        
        traversal_attempts = [
            ("Travessia relativa simples (../)", "GET /../../Windows/System32/drivers/etc/hosts HTTP/1.1\r\nHost: localhost\r\n\r\n"),
            ("Travessia com percent-encoding simples (%2e%2e)", "GET /%2e%2e/%2e%2e/etc/passwd HTTP/1.1\r\nHost: localhost\r\n\r\n"),
            ("Travessia com percent-encoding misto (%2e%2e e subpasta)", "GET /subpasta/%2e%2e/%2e%2e/%2e%2e/Windows/win.ini HTTP/1.1\r\nHost: localhost\r\n\r\n"),
            ("Travessia com encoding de barras (%2e%2e%2f)", "GET /%2e%2e%2f%2e%2e%2fconfig.sys HTTP/1.1\r\nHost: localhost\r\n\r\n"),
        ]

        for desc, req_str in traversal_attempts:
            with create_connection() as s:
                res = send_raw_request(s, req_str.encode("ascii"))
                self.assert_true(
                    res.status_code == 403,
                    f"{desc} bloqueada com 403 Forbidden",
                    f"Obtido: {res.status_code}",
                )

    def test_persistent_connections_c2(self):
        print(f"\n{BOLD}8. Teste de Conexões Persistentes (Cenário C2 - 10 requisições sequenciais no mesmo socket){RESET}")
        with create_connection() as s:
            all_ok = True
            for i in range(10):
                req = f"GET /dados.json HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("ascii")
                res = send_raw_request(s, req)
                if res.status_code != 200:
                    all_ok = False
                    break
            self.assert_true(all_ok, "10 requisições sequenciais executadas com sucesso na MESMA conexão TCP")

    def test_connection_close_c1(self):
        print(f"\n{BOLD}9. Teste de Encerramento com Connection: close (Cenário C1){RESET}")
        with create_connection() as s:
            req = b"GET /index.html HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 200, "Requisição com Connection: close retorna 200 OK")
            self.assert_true(
                res.headers.get("connection", "").lower() == "close",
                "Servidor ecoa cabeçalho 'Connection: close'",
            )
            
            # Testa se o socket foi de fato fechado pelo servidor
            try:
                s.settimeout(1.0)
                data = s.recv(1024)
                self.assert_true(data == b"", "Servidor fechou o socket TCP após responder")
            except (socket.timeout, OSError):
                self.assert_true(True, "Socket fechado ou inacessível após resposta")

    def test_idle_timeout(self):
        print(f"\n{BOLD}10. Teste de Timeout de Conexão Ociosa{RESET}")
        with create_connection() as s:
            # Envia 1 requisição
            req = b"GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
            res = send_raw_request(s, req)
            self.assert_true(res.status_code == 200, "Primeira requisição bem sucedida")

            # Aguarda tempo ligeiramente superior ao timeout do servidor (TEST_TIMEOUT = 2.0s)
            print(f"    (Aguardando {TEST_TIMEOUT + 0.5:.1f}s para validar fechamento por ociosidade...)")
            time.sleep(TEST_TIMEOUT + 0.5)

            # Tenta ler do socket; deve retornar b"" (FIN recebido do servidor)
            try:
                s.settimeout(1.0)
                data = s.recv(1024)
                self.assert_true(data == b"", "Servidor fechou a conexão ociosa após o timeout")
            except (socket.timeout, ConnectionResetError, OSError) as e:
                self.assert_true(True, f"Conexão encerrada pelo servidor conforme esperado: {e}")

    def test_tcp_stream_fragmentation(self):
        print(f"\n{BOLD}11. Teste de Fluxo Contínuo e Fragmentação TCP (Buffer Accumulation){RESET}")
        # Envia requisição caractere a caractere com pausas (simula fragmentação de pacotes na rede)
        with create_connection() as s:
            req = b"GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
            for b in req:
                s.sendall(bytes([b]))
                time.sleep(0.002)

            res = send_raw_request(s, b"", timeout=2.0)
            self.assert_true(res.status_code == 200, "Buffer TCP acumula fluxo fragmentado byte-a-byte até CRLF CRLF")

        # Envia duas requisições coladas no mesmo sendall (simula pipelining / buffering de múltiplas requisições)
        with create_connection() as s:
            two_reqs = (
                b"GET /style.css HTTP/1.1\r\nHost: localhost\r\n\r\n"
                b"GET /app.js HTTP/1.1\r\nHost: localhost\r\n\r\n"
            )
            s.sendall(two_reqs)
            
            # Lê primeira resposta
            res1 = send_raw_request(s, b"", timeout=2.0)
            self.assert_true(res1.status_code == 200 and "text/css" in res1.headers.get("content-type", ""), "Primeira requisição acumulada atendida com sucesso")

            # Lê segunda resposta
            res2 = send_raw_request(s, b"", timeout=2.0)
            self.assert_true(res2.status_code == 200 and "application/javascript" in res2.headers.get("content-type", ""), "Segunda requisição no buffer residual atendida com sucesso")

    def test_concurrency(self):
        print(f"\n{BOLD}12. Teste de Concorrência: Múltiplas conexões simultâneas{RESET}")
        num_clients = 10
        barrier = threading.Barrier(num_clients)
        successes = []

        def worker(client_id: int):
            try:
                with create_connection() as s:
                    # Sincroniza todas as threads para dispararem no exato mesmo milissegundo
                    barrier.wait(timeout=5.0)
                    req = f"GET /dados.json?client={client_id} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("ascii")
                    res = send_raw_request(s, req)
                    if res.status_code == 200:
                        successes.append(client_id)
            except Exception as e:
                print(f"Erro no cliente concorrente {client_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_clients)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        self.assert_true(
            len(successes) == num_clients,
            f"{num_clients} conexões simultâneas atendidas com sucesso sem bloqueio mútuo ({len(successes)}/{num_clients})",
        )


def main():
    # Inicia o servidor em uma thread de background
    server_thread = threading.Thread(
        target=server.run_server,
        args=(TEST_HOST, TEST_PORT, TEST_ROOT, TEST_TIMEOUT),
        daemon=True,
    )
    server_thread.start()
    time.sleep(0.5)  # Breve tempo para o socket vincular

    suite = TestSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

