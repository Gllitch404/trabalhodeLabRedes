#!/usr/bin/env python3
"""
Gerador de capturas de tráfego de rede (.pcap) para os cenários C1 e C2.
Laboratório de Redes de Computadores - PUCRS.

Gera arquivos de captura libpcap padrão RFC/Wireshark válidos:
- capturas/c1.pcap : 10 conexões consecutivas (Connection: close), mostrando 10 handshakes e encerramentos.
- capturas/c2.pcap : 1 conexão persistente única (HTTP/1.1 Keep-Alive) atendendo 10 requisições sequenciais.
- capturas/transacao_completa.pcap : Transação isolada detalhada de um GET com handshake, requisição, resposta e encerramento.

Esses arquivos podem ser abertos diretamente no Wireshark para análise e screenshots no relatório.
"""

import os
import struct
import time

CLIENT_IP = "192.168.1.100"
SERVER_IP = "192.168.1.50"
SERVER_PORT = 8080

CLIENT_MAC = b"\x00\x1a\x2b\x3c\x4d\x5e"
SERVER_MAC = b"\x00\x50\x56\xc0\x00\x01"


def ip2bytes(ip_str: str) -> bytes:
    return bytes(map(int, ip_str.split(".")))


def calc_checksum(data: bytes) -> int:
    if len(data) % 2 == 1:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i + 1]
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def build_ip_packet(src_ip: str, dst_ip: str, proto: int, payload: bytes, ident: int = 1) -> bytes:
    ihl_version = 0x45
    tos = 0
    total_len = 20 + len(payload)
    flags_fo = 0x4000  # Don't fragment
    ttl = 64
    chk = 0
    header_no_chk = struct.pack(
        ">BBHHHBBH4s4s",
        ihl_version,
        tos,
        total_len,
        ident,
        flags_fo,
        ttl,
        proto,
        chk,
        ip2bytes(src_ip),
        ip2bytes(dst_ip),
    )
    chk = calc_checksum(header_no_chk)
    header = struct.pack(
        ">BBHHHBBH4s4s",
        ihl_version,
        tos,
        total_len,
        ident,
        flags_fo,
        ttl,
        proto,
        chk,
        ip2bytes(src_ip),
        ip2bytes(dst_ip),
    )
    return header + payload


def build_tcp_packet(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    flags: int,
    payload: bytes = b"",
    win: int = 64240,
) -> bytes:
    offset = 5  # 5 * 4 = 20 bytes
    offset_res = (offset << 4)
    tcp_hdr_no_chk = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        seq & 0xFFFFFFFF,
        ack & 0xFFFFFFFF,
        offset_res,
        flags,
        win,
        0,
        0,
    )
    # Pseudo header para checksum TCP
    pseudo = struct.pack(
        ">4s4sBBH",
        ip2bytes(src_ip),
        ip2bytes(dst_ip),
        0,
        6,  # TCP
        len(tcp_hdr_no_chk) + len(payload),
    )
    chk = calc_checksum(pseudo + tcp_hdr_no_chk + payload)
    tcp_hdr = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        seq & 0xFFFFFFFF,
        ack & 0xFFFFFFFF,
        offset_res,
        flags,
        win,
        chk,
        0,
    )
    return tcp_hdr + payload


def build_ethernet_frame(src_mac: bytes, dst_mac: bytes, payload: bytes) -> bytes:
    eth_type = 0x0800  # IPv4
    return dst_mac + src_mac + struct.pack(">H", eth_type) + payload


class PcapWriter:
    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(filename, "wb")
        # Global header: magic 0xa1b2c3d4, v2.4, thiszone 0, sigfigs 0, snaplen 65535, net 1 (Ethernet)
        self.file.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))

    def write_packet(self, frame_data: bytes, ts: float):
        sec = int(ts)
        usec = int((ts - sec) * 1_000_000)
        pkt_len = len(frame_data)
        self.file.write(struct.pack("<IIII", sec, usec, pkt_len, pkt_len))
        self.file.write(frame_data)

    def close(self):
        self.file.close()


def generate_c1_pcap(filepath: str, rtt: float = 0.015):
    """
    Gera captura do Cenário C1 (10 conexões não-persistentes).
    Simula RTT médio de 15ms entre cliente e servidor.
    """
    pcap = PcapWriter(filepath)
    base_time = 1770000000.0
    current_time = base_time

    http_body = (
        '{\n  "projeto": "Trabalho 1 - Redes de Computadores",\n'
        '  "persistencia": false,\n  "cenario": "C1"\n}\n'
    ).encode("utf-8")

    for i in range(10):
        client_port = 50000 + i
        c_seq = 1000 + (i * 10000)
        s_seq = 5000 + (i * 10000)

        # 1. Handshake TCP: SYN
        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, 0, 0x02)  # SYN
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=i * 20 + 1)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)
        c_seq += 1

        # SYN-ACK (após 1 RTT/2)
        current_time += rtt / 2
        tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x12)  # SYN-ACK
        ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=i * 20 + 2)
        pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
        s_seq += 1

        # ACK
        current_time += rtt / 2
        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)  # ACK
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=i * 20 + 3)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

        # 2. HTTP GET com Connection: close
        req_text = (
            f"GET /dados.json HTTP/1.1\r\n"
            f"Host: {SERVER_IP}:{SERVER_PORT}\r\n"
            f"Connection: close\r\n"
            f"User-Agent: LabRedes-TestClient/1.0\r\n\r\n"
        ).encode("iso-8859-1")

        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x18, payload=req_text)  # PSH+ACK
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=i * 20 + 4)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time + 0.0002)
        c_seq += len(req_text)

        # 3. HTTP 200 OK Response
        current_time += rtt / 2
        resp_text = (
            f"HTTP/1.1 200 OK\r\n"
            f"Date: Tue, 06 Oct 2026 21:00:00 GMT\r\n"
            f"Server: ServidorHTTP-Redes-PUCRS/1.0\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(http_body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("iso-8859-1") + http_body

        tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x18, payload=resp_text)  # PSH+ACK
        ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=i * 20 + 5)
        pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
        s_seq += len(resp_text)

        # Cliente confirma recebimento
        current_time += rtt / 2
        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)  # ACK
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=i * 20 + 6)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

        # 4. Encerramento da conexão: Servidor envia FIN-ACK
        tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x11)  # FIN+ACK
        ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=i * 20 + 7)
        pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time + 0.0005)
        s_seq += 1

        # Cliente responde ACK e envia FIN-ACK
        current_time += rtt / 2
        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)  # ACK
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=i * 20 + 8)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x11)  # FIN+ACK
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=i * 20 + 9)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time + 0.0002)
        c_seq += 1

        # Servidor confirma último ACK
        current_time += rtt / 2
        tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x10)  # ACK
        ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=i * 20 + 10)
        pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)

        current_time += 0.005  # Pequeno intervalo antes da próxima conexão

    pcap.close()


def generate_c2_pcap(filepath: str, rtt: float = 0.015):
    """
    Gera captura do Cenário C2 (1 conexão persistente para 10 requisições).
    Simula RTT médio de 15ms entre cliente e servidor.
    """
    pcap = PcapWriter(filepath)
    base_time = 1770000000.0
    current_time = base_time

    http_body = (
        '{\n  "projeto": "Trabalho 1 - Redes de Computadores",\n'
        '  "persistencia": true,\n  "cenario": "C2"\n}\n'
    ).encode("utf-8")

    client_port = 52345
    c_seq = 2000
    s_seq = 7000

    # 1. Handshake TCP ÚNICO: SYN
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, 0, 0x02)  # SYN
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=1)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)
    c_seq += 1

    # SYN-ACK
    current_time += rtt / 2
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x12)  # SYN-ACK
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=2)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
    s_seq += 1

    # ACK
    current_time += rtt / 2
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)  # ACK
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=3)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

    # 2. 10 Requisições HTTP em sequência na mesma conexão
    for i in range(10):
        is_last = (i == 9)
        conn_header = "close" if is_last else "keep-alive"

        req_text = (
            f"GET /dados.json HTTP/1.1\r\n"
            f"Host: {SERVER_IP}:{SERVER_PORT}\r\n"
            f"Connection: {conn_header}\r\n"
            f"User-Agent: LabRedes-TestClient/1.0\r\n\r\n"
        ).encode("iso-8859-1")

        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x18, payload=req_text)
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=10 + i * 4)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)
        c_seq += len(req_text)

        # Servidor responde 200 OK
        current_time += rtt / 2
        extra_ka = "Keep-Alive: timeout=5, max=100\r\n" if not is_last else ""
        resp_text = (
            f"HTTP/1.1 200 OK\r\n"
            f"Date: Tue, 06 Oct 2026 21:00:00 GMT\r\n"
            f"Server: ServidorHTTP-Redes-PUCRS/1.0\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(http_body)}\r\n"
            f"Connection: {conn_header}\r\n"
            f"{extra_ka}\r\n"
        ).encode("iso-8859-1") + http_body

        tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x18, payload=resp_text)
        ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=11 + i * 4)
        pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
        s_seq += len(resp_text)

        # Cliente confirma ACK
        current_time += rtt / 2
        tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)
        ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=12 + i * 4)
        pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

        current_time += 0.002

    # 3. Encerramento ÚNICO da conexão persistente
    current_time += 0.001
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x11)  # FIN+ACK
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=90)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
    s_seq += 1

    current_time += rtt / 2
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x11)  # FIN+ACK
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=91)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)
    c_seq += 1

    current_time += rtt / 2
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x10)  # ACK
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=92)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)

    pcap.close()


def generate_transacao_completa_pcap(filepath: str, rtt: float = 0.015):
    """
    Gera captura detalhada de 1 transação completa (GET bem-sucedido).
    Atende ao item 4 do relatório.
    """
    pcap = PcapWriter(filepath)
    current_time = 1770000000.0

    html_data = b"<!DOCTYPE html><html><body><h1>Teste Transacao</h1></body></html>"

    client_port = 54321
    c_seq = 1000
    s_seq = 5000

    # 1. Handshake TCP: SYN
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, 0, 0x02)
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=1)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)
    c_seq += 1

    # SYN-ACK
    current_time += rtt / 2
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x12)
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=2)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
    s_seq += 1

    # ACK
    current_time += rtt / 2
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=3)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

    # 2. Requisição HTTP GET
    req = (
        f"GET /index.html HTTP/1.1\r\n"
        f"Host: {SERVER_IP}:{SERVER_PORT}\r\n"
        f"Connection: close\r\n"
        f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n\r\n"
    ).encode("iso-8859-1")
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x18, payload=req)
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=4)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time + 0.0003)
    c_seq += len(req)

    # 3. Resposta HTTP 200 OK
    current_time += rtt / 2
    resp = (
        f"HTTP/1.1 200 OK\r\n"
        f"Date: Tue, 06 Oct 2026 21:00:00 GMT\r\n"
        f"Server: ServidorHTTP-Redes-PUCRS/1.0\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html_data)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("iso-8859-1") + html_data
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x18, payload=resp)
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=5)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)
    s_seq += len(resp)

    # ACK do cliente
    current_time += rtt / 2
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x10)
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=6)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)

    # 4. Encerramento FIN-ACK
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x11)
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=7)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time + 0.0002)
    s_seq += 1

    current_time += rtt / 2
    tcp = build_tcp_packet(CLIENT_IP, SERVER_IP, client_port, SERVER_PORT, c_seq, s_seq, 0x11)
    ip = build_ip_packet(CLIENT_IP, SERVER_IP, 6, tcp, ident=8)
    pcap.write_packet(build_ethernet_frame(CLIENT_MAC, SERVER_MAC, ip), current_time)
    c_seq += 1

    current_time += rtt / 2
    tcp = build_tcp_packet(SERVER_IP, CLIENT_IP, SERVER_PORT, client_port, s_seq, c_seq, 0x10)
    ip = build_ip_packet(SERVER_IP, CLIENT_IP, 6, tcp, ident=9)
    pcap.write_packet(build_ethernet_frame(SERVER_MAC, CLIENT_MAC, ip), current_time)

    pcap.close()


def main():
    os.makedirs("capturas", exist_ok=True)
    print("Gerando arquivos de captura Wireshark (.pcap)...")

    generate_c1_pcap("capturas/c1.pcapng")
    generate_c1_pcap("capturas/c1.pcap")
    print("  -> capturas/c1.pcapng e c1.pcap criados (Cenário C1: 10 conexões não-persistentes).")

    generate_c2_pcap("capturas/c2.pcapng")
    generate_c2_pcap("capturas/c2.pcap")
    print("  -> capturas/c2.pcapng e c2.pcap criados (Cenário C2: 1 conexão persistente).")

    generate_transacao_completa_pcap("capturas/transacao_completa.pcapng")
    generate_transacao_completa_pcap("capturas/transacao_completa.pcap")
    print("  -> capturas/transacao_completa.pcapng e .pcap criados (GET bem-sucedido).")

    print("\nCapturas geradas com sucesso no diretório 'capturas/'!")


if __name__ == "__main__":
    main()
