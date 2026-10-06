#!/usr/bin/env python3
"""
Converte o RELATORIO.md em RELATORIO.html com estilização profissional para impressão/exportação em PDF.
Abra o arquivo RELATORIO.html no navegador (Chrome, Edge ou Firefox) e pressione Ctrl+P para salvar em PDF.
"""

import os
import re

def markdown_to_html(md_text: str) -> str:
    html = md_text

    # Escapar caracteres HTML básicos fora de formatações
    # Títulos
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Blocos de código
    html = re.sub(r'```([a-zA-Z]*)\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

    # Código inline
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)

    # Negrito e itálico
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Linha horizontal
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)

    # Tabelas
    def format_table(match):
        lines = match.group(0).strip().split('\n')
        if len(lines) < 2:
            return match.group(0)
        
        header_cols = [c.strip() for c in lines[0].split('|')[1:-1]]
        # ignora linha de separadores (lines[1])
        rows = []
        for line in lines[2:]:
            cols = [c.strip() for c in line.split('|')[1:-1]]
            rows.append(cols)

        out = ['<table class="report-table">', '<thead><tr>']
        for h in header_cols:
            out.append(f'<th>{h}</th>')
        out.append('</tr></thead><tbody>')

        for r in rows:
            out.append('<tr>')
            for c in r:
                out.append(f'<td>{c}</td>')
            out.append('</tr>')
        out.append('</tbody></table>')
        return '\n'.join(out)

    table_pattern = re.compile(r'(\|.*?\|\n\|[-:| ]+\|\n(?:\|.*?\|\n?)+)', re.MULTILINE)
    html = table_pattern.sub(format_table, html)

    # Parágrafos
    paragraphs = html.split('\n\n')
    formatted = []
    for p in paragraphs:
        p_str = p.strip()
        if not p_str:
            continue
        if p_str.startswith('<h') or p_str.startswith('<pre') or p_str.startswith('<table') or p_str.startswith('<hr'):
            formatted.append(p_str)
        elif p_str.startswith('- '):
            items = p_str.split('\n')
            list_html = '<ul>' + ''.join(f'<li>{it[2:]}</li>' for it in items if it.startswith('- ')) + '</ul>'
            formatted.append(list_html)
        else:
            formatted.append(f'<p>{p_str}</p>')

    return '\n\n'.join(formatted)

def main():
    if not os.path.exists("RELATORIO.md"):
        print("RELATORIO.md não encontrado!")
        return

    with open("RELATORIO.md", "r", encoding="utf-8") as f:
        md = f.read()

    body_html = markdown_to_html(md)

    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Técnico - Servidor HTTP/1.1 Socket TCP</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #1e293b;
            background: #ffffff;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 24px;
        }}
        h1 {{
            color: #0f172a;
            border-bottom: 2px solid #2563eb;
            padding-bottom: 12px;
            font-size: 1.8rem;
            margin-top: 0;
        }}
        h2 {{
            color: #1e3a8a;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 6px;
            margin-top: 32px;
            font-size: 1.35rem;
        }}
        h3 {{
            color: #1e293b;
            margin-top: 20px;
            font-size: 1.1rem;
        }}
        p, li {{
            font-size: 0.95rem;
            color: #334155;
        }}
        code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: Consolas, Monaco, "Courier New", monospace;
            font-size: 0.9em;
            color: #0f172a;
        }}
        pre {{
            background: #0f172a;
            color: #e2e8f0;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.85rem;
        }}
        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9rem;
        }}
        .report-table th, .report-table td {{
            border: 1px solid #cbd5e1;
            padding: 10px 12px;
            text-align: left;
        }}
        .report-table th {{
            background-color: #f8fafc;
            color: #0f172a;
            font-weight: 600;
        }}
        .report-table tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        hr {{
            border: 0;
            border-top: 1px solid #e2e8f0;
            margin: 28px 0;
        }}
        @media print {{
            body {{
                max-width: 100%;
                padding: 0;
            }}
            pre, .report-table {{
                page-break-inside: avoid;
            }}
            h2, h3 {{
                page-break-after: avoid;
            }}
        }}
    </style>
</head>
<body>
    {body_html}
</body>
</html>
"""

    with open("RELATORIO.html", "w", encoding="utf-8") as f:
        f.write(page)

    print("RELATORIO.html gerado com sucesso!")
    print("Dica: Abra RELATORIO.html no seu navegador e selecione 'Imprimir' -> 'Salvar como PDF' para gerar o PDF da entrega.")

if __name__ == "__main__":
    main()

