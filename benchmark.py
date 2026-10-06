#!/usr/bin/env python3
"""
Script de Medição e Comparação de Desempenho HTTP/1.1 (C1 vs C2).
Laboratório de Redes de Computadores - PUCRS.

Cenários avaliados:
- C1: Uma nova conexão TCP por requisição (Connection: close) - 10 conexões consecutivas.
- C2: Uma única conexão persistente para as 10 requisições (HTTP/1.1 Keep-Alive).

Métricas analisadas:
- Handshakes TCP completos (SYN, SYN-ACK, ACK)
- Estimativa do total de pacotes TCP (Handshakes + Dados + Encerramentos FIN/ACK)
- Bytes totais trafegados (envio e recepção na camada de transporte)
- Tempo total de execução (ms)
- Economia percentual proporcionada pela persistência
"""

import argparse
import os
import socket
import sys
import time

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_scenario_c1(host: str, port: int, path: str, num_requests: int = 10):
    """
    Cenário C1: Conexão não-persistente.
    Abre uma conexão TCP separada para cada uma das requisições.
    """
    total_bytes_sent = 0
    total_bytes_received = 0
    handshakes = 0

    t_start = time.perf_counter()

    for i in range(num_requests):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((host, port))
        handshakes += 1

        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Connection: close\r\n"
            f"User-Agent: BenchmarkClient-C1/1.0\r\n\r\n"
        ).encode("iso-8859-1")

        s.sendall(req)
        total_bytes_sent += len(req)

        # Recebe a resposta completa até o fechamento do socket
        resp_bytes = bytearray()
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp_bytes.extend(chunk)

        total_bytes_received += len(resp_bytes)
        s.close()

    t_end = time.perf_counter()
    duration_ms = (t_end - t_start) * 1000

    # Estimativa de pacotes TCP:
    # Por conexão no C1:
    # 3 pacotes handshake (SYN, SYN-ACK, ACK)
    # 1 pacote requisição HTTP
    # 1 ou mais pacotes resposta HTTP + ACKs correspondentes (~2 pacotes)
    # 4 pacotes encerramento (FIN, ACK, FIN, ACK)
    # Total médio: ~10 pacotes por transação não-persistente
    est_packets = handshakes * 10

    return {
        "handshakes": handshakes,
        "est_packets": est_packets,
        "bytes_sent": total_bytes_sent,
        "bytes_received": total_bytes_received,
        "total_bytes": total_bytes_sent + total_bytes_received,
        "duration_ms": duration_ms,
    }


def run_scenario_c2(host: str, port: int, path: str, num_requests: int = 10):
    """
    Cenário C2: Conexão persistente (Keep-Alive).
    Uma única conexão TCP é aberta e reutilizada para todas as requisições.
    """
    total_bytes_sent = 0
    total_bytes_received = 0
    handshakes = 0

    t_start = time.perf_counter()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((host, port))
    handshakes = 1

    buffer = bytearray()

    for i in range(num_requests):
        is_last = (i == num_requests - 1)
        conn_header = "close" if is_last else "keep-alive"

        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Connection: {conn_header}\r\n"
            f"User-Agent: BenchmarkClient-C2/1.0\r\n\r\n"
        ).encode("iso-8859-1")

        s.sendall(req)
        total_bytes_sent += len(req)

        # Lê a resposta usando Content-Length para saber onde o corpo termina
        content_length = None
        while True:
            if b"\r\n\r\n" in buffer and content_length is not None:
                sep_idx = buffer.find(b"\r\n\r\n")
                if len(buffer) >= sep_idx + 4 + content_length:
                    # Resposta completa recebida nesta iteração
                    resp_len = sep_idx + 4 + content_length
                    total_bytes_received += resp_len
                    del buffer[:resp_len]
                    break

            chunk = s.recv(4096)
            if not chunk:
                break
            buffer.extend(chunk)

            if content_length is None and b"\r\n\r\n" in buffer:
                sep_idx = buffer.find(b"\r\n\r\n")
                hdr_text = buffer[:sep_idx].decode("iso-8859-1", errors="replace")
                for line in hdr_text.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())
                if content_length is None:
                    content_length = 0

    s.close()
    t_end = time.perf_counter()
    duration_ms = (t_end - t_start) * 1000

    # Estimativa de pacotes TCP no C2:
    # 3 pacotes handshake único (SYN, SYN-ACK, ACK)
    # Para cada req: 1 req + 1 resp + 1 ACK intermediário (~2 a 3 pacotes)
    # 4 pacotes encerramento único (FIN, ACK, FIN, ACK)
    # Total médio: 3 + (10 * 2.2) + 4 =~ 29 pacotes
    est_packets = 3 + (num_requests * 2) + 4

    return {
        "handshakes": handshakes,
        "est_packets": est_packets,
        "bytes_sent": total_bytes_sent,
        "bytes_received": total_bytes_received,
        "total_bytes": total_bytes_sent + total_bytes_received,
        "duration_ms": duration_ms,
    }


def main():
    parser = argparse.ArgumentParser(description="Medição comparativa HTTP/1.1: C1 vs C2")
    parser.add_argument("--host", default="127.0.0.1", help="Endereço IP do servidor (padrão: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Porta do servidor (padrão: 8080)")
    parser.add_argument("--path", default="/dados.json", help="Caminho do recurso requisitado (padrão: /dados.json)")
    parser.add_argument("--num", "-n", type=int, default=10, help="Quantidade de requisições sequenciais (padrão: 10)")

    args = parser.parse_args()

    # Testa se o servidor está acessível
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.settimeout(2.0)
    try:
        test_sock.connect((args.host, args.port))
        test_sock.close()
    except OSError as e:
        print(f"[ERRO] Não foi possível conectar ao servidor em {args.host}:{args.port}.")
        print("Certifique-se de que o servidor está em execução:")
        print(f"  python server.py --port {args.port} --root ./www")
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN}  BENCHMARK HTTP/1.1 - COMPARAÇÃO C1 (SEM PERSISTÊNCIA) vs C2 (KEEP-ALIVE){RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}")
    print(f" Servidor : {args.host}:{args.port}")
    print(f" Recurso  : {args.path}")
    print(f" Amostra  : {args.num} requisições sequenciais\n")

    print("[1/2] Executando Cenário C1 (uma conexão nova por requisição)...")
    res_c1 = run_scenario_c1(args.host, args.port, args.path, args.num)
    print("      Concluído com sucesso.")

    time.sleep(0.5)

    print("[2/2] Executando Cenário C2 (conexão persistente única Keep-Alive)...")
    res_c2 = run_scenario_c2(args.host, args.port, args.path, args.num)
    print("      Concluído com sucesso.\n")

    # Cálculos de economia percentual
    diff_hs = ((res_c1["handshakes"] - res_c2["handshakes"]) / res_c1["handshakes"]) * 100
    diff_pkt = ((res_c1["est_packets"] - res_c2["est_packets"]) / res_c1["est_packets"]) * 100
    diff_bytes = ((res_c1["total_bytes"] - res_c2["total_bytes"]) / res_c1["total_bytes"]) * 100
    diff_time = ((res_c1["duration_ms"] - res_c2["duration_ms"]) / res_c1["duration_ms"]) * 100

    print(f"{BOLD}{GREEN}------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}TABELA COMPARATIVA DE RESULTADOS (C1 vs C2){RESET}")
    print(f"{BOLD}{GREEN}------------------------------------------------------------------------{RESET}")
    header_fmt = "{:<32} | {:<16} | {:<16} | {:<12}"
    row_fmt    = "{:<32} | {:<16} | {:<16} | {:<12}"
    
    print(header_fmt.format("Métrica", "C1 (Nova Conexão)", "C2 (Persistente)", "Economia (%)"))
    print("-" * 84)
    print(row_fmt.format("Handshakes TCP completos", str(res_c1["handshakes"]), str(res_c2["handshakes"]), f"{diff_hs:.1f}%"))
    print(row_fmt.format("Estimativa de Pacotes TCP", f"~{res_c1['est_packets']}", f"~{res_c2['est_packets']}", f"{diff_pkt:.1f}%"))
    print(row_fmt.format("Bytes Totais Trafegados", f"{res_c1['total_bytes']} B", f"{res_c2['total_bytes']} B", f"{diff_bytes:.1f}%"))
    print(row_fmt.format("Tempo Total Decorrido", f"{res_c1['duration_ms']:.2f} ms", f"{res_c2['duration_ms']:.2f} ms", f"{diff_time:.1f}%"))
    print(f"{BOLD}{GREEN}------------------------------------------------------------------------{RESET}\n")

    print(f"{BOLD}Análise Resumida:{RESET}")
    print(f"- Handshakes evitados   : {res_c1['handshakes'] - res_c2['handshakes']} conexões completas poupadas.")
    print(f"- Redução de pacotes    : aprox. {diff_pkt:.1f}% menos mensagens de controle na rede.")
    print(f"- Ganho de desempenho   : o cenário C2 foi {diff_time:.1f}% mais rápido que o cenário C1.")
    print(f"\n{YELLOW}[DICA PARA O RELATÓRIO]{RESET}")
    print("Ao executar este teste na rede da PUCRS com RTT real (ex: ping ~5-20ms):")
    print("O tempo de cada handshake novo no C1 custa 1.5 RTTs a mais, tornando a diferença de tempo ainda mais expressiva!")
    print(f"{BOLD}{CYAN}========================================================================{RESET}\n")


if __name__ == "__main__":
    main()

