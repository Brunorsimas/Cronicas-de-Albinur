"""Escreve width/height em todo <img> que aponta para img/.

Sem isso o navegador nao sabe o espaco da imagem antes de baixar, e a pagina
pula quando cada arte chega (layout shift). As classes do Tailwind continuam
mandando no tamanho visual; os atributos so informam a proporcao.
"""
import re
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).parent
total = 0


def completa(m):
    global total
    tag = m.group(0)
    if "width=" in tag or "height=" in tag:
        return tag
    src = re.search(r'src="([^"]+)"', tag)
    if not src:
        return tag
    alvo = src.group(1)
    # placehold.co codifica o tamanho na propria URL
    placeholder = re.search(r"placehold\.co/(\d+)x(\d+)", alvo)
    if placeholder:
        largura, altura = map(int, placeholder.groups())
    else:
        arquivo = RAIZ / alvo
        if not alvo.startswith("img/") or not arquivo.exists():
            return tag
        largura, altura = Image.open(arquivo).size
    total += 1
    fecha = "/>" if tag.rstrip().endswith("/>") else ">"
    corpo = tag.rstrip().removesuffix(fecha).rstrip()
    return f'{corpo} width="{largura}" height="{altura}"{fecha}'


for pagina in sorted(RAIZ.glob("*.html")):
    texto = pagina.read_text(encoding="utf-8")
    novo = re.sub(r"<img\b[^>]*>", completa, texto)
    if novo != texto:
        pagina.write_text(novo, encoding="utf-8")
        print("dimensoes:", pagina.name)

faltando = []
for pagina in sorted(RAIZ.glob("*.html")):
    for m in re.finditer(r"<img\b[^>]*>", pagina.read_text(encoding="utf-8")):
        tag = m.group(0)
        if "width=" not in tag or "height=" not in tag:
            faltando.append(f"{pagina.name}: {tag[:70]}")
assert not faltando, faltando
print(f"ok: {total} imagens receberam width/height, nenhuma pendente")
