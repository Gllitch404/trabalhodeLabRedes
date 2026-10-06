// Script interativo da pagina de teste
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
