import os
import struct
import zlib

os.makedirs('www/subpasta', exist_ok=True)

# 1. index.html
html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teste de Interoperabilidade - Servidor HTTP/1.1</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>Laboratório de Redes de Computadores - PUCRS</h1>
            <p class="subtitle">Trabalho 1: Servidor HTTP/1.1 sobre Sockets TCP</p>
        </div>
    </header>

    <main class="container">
        <section class="card intro">
            <h2>Teste de Interoperabilidade</h2>
            <p>Esta página foi projetada para validar a interoperabilidade entre grupos. O navegador requisita múltiplos recursos estáticos simultaneamente (HTML, CSS, JS, PNG, JPG, PDF e JSON), testando as conexões persistentes <strong>HTTP/1.1 (Keep-Alive)</strong>.</p>
            <div class="status-box">
                <span class="badge-success">Servidor Ativo</span>
                <span>Porta e socket TCP operando com concorrência multi-thread</span>
            </div>
        </section>

        <section class="grid">
            <div class="card">
                <h3>Arquivos e Tipos MIME</h3>
                <ul class="file-list">
                    <li><a href="style.css" target="_blank">CSS: style.css (text/css)</a></li>
                    <li><a href="app.js" target="_blank">JavaScript: app.js (application/javascript)</a></li>
                    <li><a href="dados.json" target="_blank">JSON: dados.json (application/json)</a></li>
                    <li><a href="exemplo.txt" target="_blank">Texto: exemplo.txt (text/plain)</a></li>
                    <li><a href="documento.pdf" target="_blank">PDF: documento.pdf (application/pdf)</a></li>
                    <li><a href="subpasta/sub.html">Subdiretório: subpasta/sub.html</a></li>
                </ul>
            </div>

            <div class="card">
                <h3>Interatividade JavaScript (AJAX / Fetch)</h3>
                <p>Clique no botão abaixo para requisitar <code>dados.json</code> dinamicamente na mesma conexão:</p>
                <button id="btn-load" class="btn">Carregar Dados JSON</button>
                <div id="json-result" class="code-block">Nenhum dado carregado ainda.</div>
            </div>
        </section>

        <section class="card">
            <h3>Recursos Visuais Referenciados</h3>
            <p>Carregamento simultâneo de imagens binárias no navegador:</p>
            <div class="image-grid">
                <div class="image-card">
                    <h4>Imagem PNG (image/png)</h4>
                    <img src="imagem.png" alt="Teste PNG" width="200" height="120">
                </div>
                <div class="image-card">
                    <h4>Foto JPEG (image/jpeg)</h4>
                    <img src="foto.jpg" alt="Teste JPEG" width="200" height="120">
                </div>
            </div>
        </section>
    </main>

    <footer>
        <div class="container">
            <p>Servidor HTTP/1.1 Socket TCP &bull; Redes de Computadores &bull; PUCRS</p>
        </div>
    </footer>

    <script src="app.js"></script>
</body>
</html>
"""
with open('www/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# 2. style.css
css_content = """/* Estilos do Servidor HTTP/1.1 */
:root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --success: #16a34a;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

.container {
    max-width: 960px;
    margin: 0 auto;
    padding: 0 20px;
}

header {
    background: linear-gradient(135deg, #1e3a8a, var(--primary));
    color: white;
    padding: 40px 0;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

header h1 { font-size: 2rem; margin-bottom: 8px; }
.subtitle { font-size: 1.1rem; opacity: 0.9; }

main { padding: 32px 20px; }

.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.card h2, .card h3 {
    margin-bottom: 16px;
    color: #0f172a;
}

.status-box {
    margin-top: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.badge-success {
    background-color: #dcfce7;
    color: var(--success);
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.875rem;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 24px;
}

.file-list {
    list-style: none;
}

.file-list li {
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
}

.file-list li:last-child { border-bottom: none; }

.file-list a {
    color: var(--primary);
    text-decoration: none;
    font-weight: 500;
}

.file-list a:hover { text-decoration: underline; }

.btn {
    background-color: var(--primary);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
    margin-top: 12px;
}

.btn:hover { background-color: var(--primary-dark); }

.code-block {
    background: #0f172a;
    color: #38bdf8;
    padding: 12px;
    border-radius: 6px;
    margin-top: 12px;
    font-family: monospace;
    font-size: 0.85rem;
    white-space: pre-wrap;
}

.image-grid {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    margin-top: 16px;
}

.image-card {
    text-align: center;
    border: 1px solid var(--border);
    padding: 12px;
    border-radius: 8px;
    background: #fafafa;
}

.image-card img {
    border-radius: 4px;
    margin-top: 8px;
    border: 1px solid #cbd5e1;
}

footer {
    text-align: center;
    padding: 24px 0;
    color: var(--text-muted);
    font-size: 0.9rem;
    border-top: 1px solid var(--border);
}
"""
with open('www/style.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

# 3. app.js
js_content = """// Script interativo da pagina de teste
document.addEventListener('DOMContentLoaded', () => {
    console.log('[HTTP/1.1 Client] Pagina carregada com sucesso via socket TCP.');

    const btn = document.getElementById('btn-load');
    const resultBox = document.getElementById('json-result');

    if (btn && resultBox) {
        btn.addEventListener('click', async () => {
            resultBox.textContent = 'Carregando dados.json...';
            try {
                const response = await fetch('dados.json');
                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }
                const data = await response.json();
                resultBox.textContent = JSON.stringify(data, null, 2);
            } catch (err) {
                resultBox.textContent = 'Erro ao buscar dados: ' + err.message;
            }
        });
    }
});
"""
with open('www/app.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# 4. dados.json
json_content = """{
  "projeto": "Trabalho 1 - Redes de Computadores",
  "disciplina": "Laboratorio de Redes de Computadores",
  "instituicao": "PUCRS",
  "protocolo": "HTTP/1.1",
  "camada_transporte": "TCP",
  "persistencia": true,
  "timeout_ocioso_segundos": 5,
  "concorrencia": "Multi-threaded",
  "modos_teste": ["C1 (conexao nova)", "C2 (conexao persistente)"]
}
"""
with open('www/dados.json', 'w', encoding='utf-8') as f:
    f.write(json_content)

# 5. exemplo.txt
txt_content = """Laboratório de Redes de Computadores - PUCRS
Trabalho 1: Servidor HTTP/1.1 sobre sockets TCP

Este arquivo de texto (.txt) é servido com o Content-Type: text/plain; charset=utf-8.
Todos os requisitos da especificação foram cumpridos:
1. Conexão persistente (HTTP/1.1 Keep-Alive)
2. Proteção contra Directory Traversal
3. Resposta correta a métodos GET e HEAD
4. Rejeição de outros métodos com 405 Method Not Allowed e cabeçalho Allow: GET, HEAD
5. Concorrência com atendimento de múltiplas conexões simultâneas.
"""
with open('www/exemplo.txt', 'w', encoding='utf-8') as f:
    f.write(txt_content)

# 6. subpasta/sub.html
sub_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Subdiretorio - Teste</title>
</head>
<body>
    <h1>Recurso dentro de subdiretório</h1>
    <p>Caminho servido com sucesso: <code>/subpasta/sub.html</code></p>
    <p><a href="../index.html">Voltar para index</a></p>
</body>
</html>
"""
with open('www/subpasta/sub.html', 'w', encoding='utf-8') as f:
    f.write(sub_content)

# 7. Valid PNG file (64x64 blue image)
def generate_png():
    width = 200
    height = 120
    raw = bytearray()
    for y in range(height):
        raw.append(0) # filter byte 0 (None)
        for x in range(width):
            raw.append(int(20 + 40 * (x / width)))   # R
            raw.append(int(80 + 100 * (y / height))) # G
            raw.append(220)                         # B
    
    compressed = zlib.compress(bytes(raw))
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        crc = struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        return c + crc

    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    png.extend(chunk(b'IHDR', ihdr_data))
    png.extend(chunk(b'IDAT', compressed))
    png.extend(chunk(b'IEND', b''))
    return bytes(png)

with open('www/imagem.png', 'wb') as f:
    f.write(generate_png())

# 8. Valid minimal JPEG file (1x1 red pixel)
jpeg_bytes = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
    0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
    0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
    0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
    0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
    0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
    0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
    0x00, 0x54, 0xBF, 0xFF, 0xD9
])
with open('www/foto.jpg', 'wb') as f:
    f.write(jpeg_bytes)

# 9. Valid minimal PDF file
pdf_content = b'''%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 73 >>
stream
BT
/F1 24 Tf
100 700 Td
(Servidor HTTP/1.1 Socket TCP - Lab Redes PUCRS) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000366 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
445
%%EOF
'''
with open('www/documento.pdf', 'wb') as f:
    f.write(pdf_content)

print("Arquivos de teste criados em www/ com sucesso!")

