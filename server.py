#!/usr/bin/env python3
"""
Servidor HTTP/1.1 sobre sockets TCP puros.
Desenvolvido para o Laboratório de Redes de Computadores - PUCRS.

Características:
- Implementação direta sobre sockets TCP (socket, bind, listen, accept, recv, send).
- Sem bibliotecas de alto nível de HTTP (parsing e formatação manuais).
- Suporte a conexões persistentes (HTTP/1.1 Keep-Alive) com timeout de ociosidade.
- Concorrência via threads (uma thread por conexão).
- Tratamento correto de fluxo contínuo de bytes do TCP e buffer residual.
- Métodos GET e HEAD, com status 405 para outros métodos.
- Códigos de status: 200, 400, 403, 404, 405.
- Proteção robusta contra Directory Traversal.
- Respostas com Date (IMF-fixdate RFC 9110), Server, Content-Type e Content-Length.
"""

import argparse
import email.utils
import mimetypes
import os
import socket
import sys
import threading
import time
import urllib.parse

# Mapeamento de tipos MIME obrigatórios e comuns
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
}

STATUS_PHRASES = {
    200: "OK",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

SERVER_NAME = "ServidorHTTP-Redes-PUCRS/1.0"
DEFAULT_TIMEOUT = 5.0  # Timeout de conexão ociosa em segundos (conforme Parte 2)


def get_current_imf_date() -> str:
    """Gera a data atual no formato IMF-fixdate GMT (RFC 9110)."""
    return email.utils.formatdate(timeval=None, localtime=False, usegmt=True)


def get_mime_type(file_path: str) -> str:
    """Retorna o Content-Type derivado da extensão do arquivo ou application/octet-stream."""
    _, ext = os.path.splitext(file_path.lower())
    if ext in MIME_TYPES:
        return MIME_TYPES[ext]
    guess, _ = mimetypes.guess_type(file_path)
    return guess if guess else "application/octet-stream"


def build_error_body(status_code: int, detail: str = "") -> bytes:
    """Gera uma página HTML simples para respostas de erro."""
    phrase = STATUS_PHRASES.get(status_code, "Error")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{status_code} {phrase}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #f8fafc; color: #1e293b; }}
        .card {{ background: white; padding: 32px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }}
        h1 {{ color: #dc2626; margin-top: 0; }}
        p {{ line-height: 1.5; color: #475569; }}
        .badge {{ background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>{status_code} {phrase}</h1>
        <p><span class="badge">HTTP/1.1</span> O servidor retornou o status correspondente à sua requisição.</p>
        {f'<p><strong>Detalhes:</strong> {detail}</p>' if detail else ''}
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <small style="color: #94a3b8;">{SERVER_NAME}</small>
    </div>
</body>
</html>
"""
    return html.encode("utf-8")


def is_safe_path(root_dir: str, target_path: str) -> bool:
    """
    Verifica de maneira estrita se o caminho alvo está contido dentro do diretório raiz.
    Impede qualquer tipo de Directory Traversal (../, %2e%2e, symlinks, drives alternativos).
    """
    try:
        canonical_root = os.path.realpath(root_dir)
        canonical_target = os.path.realpath(target_path)
        common = os.path.commonpath([canonical_root, canonical_target])
        return common == canonical_root
    except (ValueError, OSError):
        # ValueError ocorre no Windows se canonical_root e canonical_target estiverem em discos diferentes (ex: C: vs D:)
        return False


def build_response_headers(
    status_code: int,
    content_length: int,
    content_type: str,
    keep_alive: bool,
    extra_headers: dict = None,
) -> bytes:
    """Monta os cabeçalhos da resposta HTTP/1.1."""
    phrase = STATUS_PHRASES.get(status_code, "Unknown")
    headers = [
        f"HTTP/1.1 {status_code} {phrase}",
        f"Date: {get_current_imf_date()}",
        f"Server: {SERVER_NAME}",
        f"Content-Type: {content_type}",
        f"Content-Length: {content_length}",
        f"Connection: {'keep-alive' if keep_alive else 'close'}",
    ]
    if keep_alive:
        headers.append(f"Keep-Alive: timeout={int(DEFAULT_TIMEOUT)}, max=100")
    if extra_headers:
        for k, v in extra_headers.items():
            headers.append(f"{k}: {v}")

    header_block = "\r\n".join(headers) + "\r\n\r\n"
    return header_block.encode("iso-8859-1")


def handle_client(
    client_socket: socket.socket,
    client_address: tuple,
    root_dir: str,
    timeout: float,
):
    """
    Trata a conexão com o cliente em uma thread separada.
    Gerencia persistência (HTTP/1.1 Keep-Alive), buffer TCP e timeout.
    """
    thread_name = threading.current_thread().name
    # print(f"[{thread_name}] Conexão aceita de {client_address[0]}:{client_address[1]}")
    client_socket.settimeout(timeout)

    # Buffer para acumular o fluxo de bytes do socket TCP
    buffer = bytearray()
    keep_alive = True

    try:
        while keep_alive:
            # 1. Acumular bytes até encontrar a linha em branco (\r\n\r\n) que finaliza os cabeçalhos
            while b"\r\n\r\n" not in buffer:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        # Cliente encerrou o envio (EOF)
                        return
                    buffer.extend(chunk)
                except socket.timeout:
                    # Timeout de ociosidade expirou (5s sem nova requisição)
                    # print(f"[{thread_name}] Timeout de ociosidade atingido para {client_address[0]}. Fechando socket.")
                    return
                except (ConnectionResetError, BrokenPipeError, OSError):
                    return

            # 2. Separar a seção de cabeçalho do restante do buffer
            header_end_pos = buffer.find(b"\r\n\r\n")
            header_bytes = bytes(buffer[:header_end_pos])
            # Preserva no buffer o que sobrar para a próxima requisição na mesma conexão TCP
            del buffer[: header_end_pos + 4]

            # 3. Decodificar e realizar o parsing dos cabeçalhos
            try:
                header_text = header_bytes.decode("iso-8859-1")
            except UnicodeDecodeError:
                # Requisição com codificação inválida
                body = build_error_body(400, "Codificação de cabeçalho inválida.")
                resp = build_response_headers(400, len(body), "text/html; charset=utf-8", keep_alive=False)
                client_socket.sendall(resp + body)
                break

            lines = header_text.split("\r\n")
            if not lines or not lines[0].strip():
                # Requisição vazia
                body = build_error_body(400, "Linha de requisição vazia.")
                resp = build_response_headers(400, len(body), "text/html; charset=utf-8", keep_alive=False)
                client_socket.sendall(resp + body)
                break

            request_line = lines[0]
            header_lines = lines[1:]

            # 4. Validar e analisar a linha de requisição
            parts = request_line.split(" ")
            if len(parts) != 3:
                body = build_error_body(400, f"Linha de requisição malformada: '{request_line}'")
                resp = build_response_headers(400, len(body), "text/html; charset=utf-8", keep_alive=False)
                client_socket.sendall(resp + body)
                break

            method, request_target, http_version = parts
            http_version = http_version.upper().strip()

            # Validação básica de versão HTTP
            if not (http_version.startswith("HTTP/1.0") or http_version.startswith("HTTP/1.1")):
                body = build_error_body(400, f"Versão HTTP não suportada: '{http_version}'")
                resp = build_response_headers(400, len(body), "text/html; charset=utf-8", keep_alive=False)
                client_socket.sendall(resp + body)
                break

            # 5. Parsing das linhas de cabeçalho
            headers = {}
            bad_header = False
            for hline in header_lines:
                if not hline.strip():
                    continue
                if ":" not in hline:
                    bad_header = True
                    break
                hname, hval = hline.split(":", 1)
                headers[hname.strip().lower()] = hval.strip()

            if bad_header:
                body = build_error_body(400, "Linha de cabeçalho sem delimitador ':'")
                resp = build_response_headers(400, len(body), "text/html; charset=utf-8", keep_alive=False)
                client_socket.sendall(resp + body)
                break

            # Se o cliente enviou Content-Length, consumir o corpo para manter o buffer sincronizado
            content_length_val = 0
            if "content-length" in headers:
                try:
                    content_length_val = int(headers["content-length"])
                except ValueError:
                    content_length_val = 0

            # Drenar do buffer/socket se houver corpo
            while len(buffer) < content_length_val:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)
                except (socket.timeout, OSError):
                    break
            if content_length_val > 0:
                del buffer[:content_length_val]

            # 6. Determinar persistência da conexão
            # Em HTTP/1.1 a conexão é persistente por padrão, exceto se 'Connection: close'.
            # Em HTTP/1.0 a conexão fecha por padrão, exceto se 'Connection: keep-alive'.
            conn_header = headers.get("connection", "").lower()
            if http_version == "HTTP/1.1":
                if conn_header == "close":
                    keep_alive = False
                else:
                    keep_alive = True
            else:  # HTTP/1.0
                if conn_header == "keep-alive":
                    keep_alive = True
                else:
                    keep_alive = False

            def send_response(status_code: int, body_data: bytes, content_type: str, extra: dict = None):
                nonlocal keep_alive
                resp_hdrs = build_response_headers(
                    status_code, len(body_data), content_type, keep_alive=keep_alive, extra_headers=extra
                )
                if method == "HEAD":
                    client_socket.sendall(resp_hdrs)
                else:
                    client_socket.sendall(resp_hdrs + body_data)

            # 7. Validação do método (GET e HEAD obrigatórios; demais retornam 405)
            method = method.upper()
            if method not in ("GET", "HEAD"):
                body = build_error_body(405, f"O método '{method}' não é permitido neste servidor.")
                send_response(405, body, "text/html; charset=utf-8", extra={"Allow": "GET, HEAD"})
                print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 405 {len(body)}")
                continue

            # 8. Decodificação de percent-encoding e sanitização de caminho
            # Separar eventual query string (?foo=bar) ou fragmento (#anchor)
            path_only = request_target.split("?", 1)[0].split("#", 1)[0]

            # Decodificar percent-encoding (ex: %20 -> espaço, %2e%2e -> ..)
            decoded_path = urllib.parse.unquote(path_only)

            # Rejeitar caracteres nulos imediatamente
            if "\0" in decoded_path:
                body = build_error_body(400, "Caractere nulo detectado no caminho.")
                keep_alive = False
                send_response(400, body, "text/html; charset=utf-8")
                break

            # 9. Resolução de caminho e proteção contra Directory Traversal
            # Normalizar separadores e remover barra inicial para combinar com root_dir
            norm_rel = decoded_path.lstrip("/\\")
            candidate_path = os.path.join(root_dir, norm_rel)

            # Verificar se o caminho tenta escapar do diretório raiz
            if not is_safe_path(root_dir, candidate_path):
                # Tentativa de Directory Traversal detectada! Retorna 403 Forbidden
                body = build_error_body(403, "Acesso negado: o caminho requisitado está fora do diretório raiz.")
                send_response(403, body, "text/html; charset=utf-8")
                print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 403 {len(body)} [TRAVERSAL BLOCKED]")
                continue

            # Se for um diretório, procurar por index.html dentro dele
            resolved_file = candidate_path
            if os.path.isdir(resolved_file):
                index_candidate = os.path.join(resolved_file, "index.html")
                if os.path.isfile(index_candidate):
                    resolved_file = index_candidate
                else:
                    # Diretório solicitado sem index.html -> 404 Not Found
                    body = build_error_body(404, "Diretório não contém index.html.")
                    send_response(404, body, "text/html; charset=utf-8")
                    print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 404 {len(body)}")
                    continue

            # 10. Verificar existência do arquivo
            if not os.path.exists(resolved_file) or not os.path.isfile(resolved_file):
                body = build_error_body(404, f"Arquivo '{decoded_path}' não foi encontrado.")
                send_response(404, body, "text/html; charset=utf-8")
                print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 404 {len(body)}")
                continue

            # 11. Leitura do arquivo e envio da resposta
            try:
                file_size = os.path.getsize(resolved_file)
                content_type = get_mime_type(resolved_file)
                resp_headers = build_response_headers(
                    200, file_size, content_type, keep_alive=keep_alive
                )

                if method == "HEAD":
                    # Método HEAD retorna exatamente os cabeçalhos sem o corpo
                    client_socket.sendall(resp_headers)
                else:
                    # Método GET: enviar cabeçalhos e depois o corpo do arquivo
                    client_socket.sendall(resp_headers)
                    with open(resolved_file, "rb") as f:
                        while True:
                            data = f.read(65536)
                            if not data:
                                break
                            client_socket.sendall(data)

                print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 200 {file_size} ({content_type})")

            except PermissionError:
                body = build_error_body(403, "Permissão negada ao tentar acessar o arquivo.")
                send_response(403, body, "text/html; charset=utf-8")
                print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 403 {len(body)}")
            except Exception as e:
                body = build_error_body(500, f"Erro interno ao processar arquivo: {str(e)}")
                keep_alive = False
                send_response(500, body, "text/html; charset=utf-8")
                print(f"[{thread_name}] {client_address[0]}:{client_address[1]} - \"{request_line}\" 500 {len(body)}")
                break

    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"[{thread_name}] Exceção inesperada na conexão: {e}")
    finally:
        try:
            client_socket.close()
        except OSError:
            pass
        # print(f"[{thread_name}] Conexão fechada com {client_address[0]}:{client_address[1]}")


def run_server(host: str, port: int, root_dir: str, timeout: float = DEFAULT_TIMEOUT):
    """Inicializa o socket TCP do servidor e aceita conexões concorrentes."""
    abs_root = os.path.realpath(root_dir)
    if not os.path.exists(abs_root):
        print(f"[ERRO] Diretório raiz '{abs_root}' não existe. Criando diretório...")
        os.makedirs(abs_root, exist_ok=True)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR permite reiniciar rapidamente o servidor na mesma porta
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
    except OSError as e:
        print(f"[ERRO] Não foi possível vincular a porta {port} no host '{host}': {e}")
        sys.exit(1)

    server_socket.listen(128)
    print("=" * 70)
    print("   SERVIDOR HTTP/1.1 SOBRE SOCKETS TCP - LAB REDES PUCRS")
    print("=" * 70)
    print(f" Endereço de escuta : {host}:{port}")
    print(f" Diretório raiz     : {abs_root}")
    print(f" Timeout ocioso     : {timeout} segundos")
    print(f" Concorrência       : Multi-threading (thread por conexão)")
    print(f" Persistência       : HTTP/1.1 Keep-Alive ativado por padrão")
    print("=" * 70)
    print(" Pressione Ctrl+C para encerrar o servidor.")
    print("=" * 70)

    try:
        while True:
            client_sock, client_addr = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_sock, client_addr, abs_root, timeout),
                daemon=True,
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[INFO] Sinal de interrupção recebido. Encerrando servidor...")
    finally:
        server_socket.close()
        print("[INFO] Socket do servidor fechado.")


def main():
    parser = argparse.ArgumentParser(
        description="Servidor HTTP/1.1 sobre sockets TCP puros (Trabalho 1 - Redes PUCRS)"
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Porta TCP na qual o servidor irá escutar (padrão: 8080)",
    )
    parser.add_argument(
        "--root",
        "-r",
        type=str,
        default="./www",
        help="Caminho do diretório raiz a ser servido (padrão: ./www)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Endereço IP de escuta (padrão: 0.0.0.0 - todas as interfaces)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout de conexão ociosa em segundos (padrão: {DEFAULT_TIMEOUT}s)",
    )

    args = parser.parse_args()
    run_server(args.host, args.port, args.root, args.timeout)


if __name__ == "__main__":
    main()
