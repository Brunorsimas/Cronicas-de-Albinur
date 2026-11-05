"""Organiza as artes: img/ so com o que o site usa, resto em arquivo/.

Padrao de nome: Pagina-Assunto.ext
Nomes como Thorfinn01 e Eve02-Cena nao dizem o que tem na arte. Trocados por
descritores. Os que ja seguiam o padrao (Irus-Guardiao, Kheltan-Cavaleiro)
ficam como estao.

Roda uma vez. Idempotente: se o destino ja existe, pula.
"""
import re
import shutil
from pathlib import Path

RAIZ = Path(__file__).parent
IMG = RAIZ / "img"
ARQ = RAIZ / "arquivo"

RENOMEAR = {
    "Dragao-Ancestral.jpg": "Belford-Dragao.jpg",
    "Thorfinn01.jpg": "Thorfinn-Jovem.jpg",
    "Thorfinn02.jpg": "Thorfinn-CavaleiroNegro.jpg",
    "Dragao-Nuvens-Cena.jpg": "Thorfinn-Dragao.jpg",
    "Dragao-Nuvens-Cena.webp": "Thorfinn-Dragao.webp",
    "Eve01-Cena.png": "Eve-Elmo.png",
    "Eve01-Cena.webp": "Eve-Elmo.webp",
    "Eve02-Cena.png": "Eve-Capita.png",
    "Eve02-Cena.webp": "Eve-Capita.webp",
    "VharZhul.jpg": "VharZhul-Silhueta.jpg",
    "GrandeGuerra.jpg": "GrandeGuerra-Confronto.jpg",
    "Nheris-Capa.jpg": "Nheris-Miniatura.jpg",
}

ARQ.mkdir(exist_ok=True)

# 1. _arquivo -> arquivo
antigo = RAIZ / "_arquivo"
if antigo.is_dir():
    for f in antigo.iterdir():
        destino = ARQ / f.name
        if not destino.exists():
            shutil.move(str(f), str(destino))
    if not any(antigo.iterdir()):
        antigo.rmdir()
    print("_arquivo -> arquivo")

# 2. fontes 2K soltas na raiz vao para arquivo
for f in RAIZ.glob("*.jpg"):
    destino = ARQ / f.name
    if not destino.exists():
        shutil.move(str(f), str(destino))
        print("raiz ->", destino.name)

# 3. renomeia dentro de img/
for velho, novo in RENOMEAR.items():
    origem, destino = IMG / velho, IMG / novo
    if origem.exists() and not destino.exists():
        origem.rename(destino)
        print("img:", velho, "->", novo)

# 4. atualiza as referencias nos HTML
paginas = sorted(RAIZ.glob("*.html"))
for pagina in paginas:
    texto = original = pagina.read_text(encoding="utf-8")
    for velho, novo in RENOMEAR.items():
        texto = texto.replace(f"img/{velho}", f"img/{novo}")
    if texto != original:
        pagina.write_text(texto, encoding="utf-8")
        print("ref:", pagina.name)

# 5. o que img/ guarda tem de estar em uso; o resto vai para arquivo
usadas = set()
padrao = re.compile(r'(?:src|srcset|content)="img/([^"]+)"')
for pagina in paginas:
    usadas.update(padrao.findall(pagina.read_text(encoding="utf-8")))

for f in sorted(IMG.iterdir()):
    if f.is_file() and f.name not in usadas:
        destino = ARQ / f.name
        if not destino.exists():
            shutil.move(str(f), str(destino))
            print("orfa ->", f.name)

# --- checagem ---
restantes = {f.name for f in IMG.iterdir() if f.is_file()}
faltando = usadas - restantes
assert not faltando, f"referencia quebrada: {sorted(faltando)}"
assert restantes == usadas, f"orfa sobrou em img/: {sorted(restantes - usadas)}"
assert not list(RAIZ.glob("*.jpg")), "imagem solta na raiz"
print(f"\nok: img/ com {len(restantes)} artes, todas em uso")
