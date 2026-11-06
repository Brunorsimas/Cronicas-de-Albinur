"""Varre os HTML a procura de defeito: imagem sem atributo, link quebrado,
heading fora de ordem, meta faltando, mojibake e erro de digitacao comum.

Nao julga lore. So o que quebra pagina, atrasa carregamento ou esta escrito errado.
"""
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).parent
PAGINAS = sorted(RAIZ.glob("*.html"))

# pares que o portugues escreve junto e o teclado separa, e vice-versa
ERROS_COMUNS = [
    (r"\bpra\b", "para"),
    (r"\bmais\s+(?:de\s+)?(?:nunca|jamais)\b", "mas"),
    (r"\bha\s+\d+\s+anos?\s+atras\b", "redundancia: ha ... atras"),
    (r"\bonde\s+que\b", "onde"),
    (r"\bdevido\s+a\s+que\b", "porque"),
    (r"\bem\s+baixo\b", "embaixo"),
    (r"\bde\s+repete\b", "se repete"),
    # "e e" nao e gagueira: e conjuncao seguida do verbo ser acentuado.
    (r"(?!\be e\b)(\b\w+\b)\s+\1\b", "palavra repetida"),
]

problemas = []


def anota(pagina, linha, msg, grave=True):
    problemas.append((grave, pagina, linha, msg))


def linha_de(texto, pos):
    return texto[:pos].count("\n") + 1


for pagina in PAGINAS:
    bruto = pagina.read_bytes()
    texto = bruto.decode("utf-8")
    nome = pagina.name

    # 1. mojibake: UTF-8 lido como latin-1 e regravado
    for marca in ("Ã£", "Ã§", "Ã©", "Ã­", "Ãº", "Ã´", "â€"):
        if marca in texto:
            anota(nome, linha_de(texto, texto.index(marca)), f"mojibake {marca!r}")

    # 2. caractere de substituicao
    if "\ufffd" in texto:
        anota(nome, linha_de(texto, texto.index("\ufffd")), "caractere invalido U+FFFD")

    # 3. <img>
    for m in re.finditer(r"<img\b[^>]*>", texto):
        tag, ln = m.group(0), linha_de(texto, m.start())
        if "alt=" not in tag:
            anota(nome, ln, "img sem alt")
        elif re.search(r'alt=""', tag) and "aria-hidden" not in tag:
            anota(nome, ln, "alt vazio sem aria-hidden", grave=False)
        # a imagem do topo deve carregar logo; lazy so vale abaixo da dobra
        if "loading=" not in tag and "object-cover" not in tag:
            anota(nome, ln, "img sem loading=lazy", grave=False)
        if "width=" not in tag or "height=" not in tag:
            anota(nome, ln, "img sem width/height (causa layout shift)", grave=False)

    # 4. <source> dentro de picture precisa de type
    for m in re.finditer(r"<source\b[^>]*>", texto):
        if "type=" not in m.group(0):
            anota(nome, linha_de(texto, m.start()), "source sem type", grave=False)

    # 5. headings em ordem
    niveis = [(int(m.group(1)), linha_de(texto, m.start()))
              for m in re.finditer(r"<h([1-6])\b", texto)]
    h1 = [n for n, _ in niveis if n == 1]
    if not h1:
        anota(nome, 0, "sem h1")
    elif len(h1) > 1:
        anota(nome, 0, f"{len(h1)} elementos h1", grave=False)
    anterior = 0
    for nivel, ln in niveis:
        if anterior and nivel > anterior + 1:
            anota(nome, ln, f"salto de h{anterior} para h{nivel}", grave=False)
        anterior = nivel

    # 6. metas e lang
    abertura = texto[texto.find("<html"):texto.find(">", texto.find("<html")) + 1]
    if "lang=" not in abertura:
        anota(nome, 1, "html sem lang")
    for meta in ("charset", 'name="viewport"', 'name="description"', "og:image", "og:title"):
        if meta not in texto:
            anota(nome, 0, f"meta ausente: {meta}", grave=(meta == "charset"))
    if "<title>" not in texto:
        anota(nome, 0, "sem title")

    # 7. links locais
    for m in re.finditer(r'href="(?!https?:|#|mailto:|data:)([^"]+)"', texto):
        alvo = m.group(1).split("#")[0]
        if alvo and not (RAIZ / alvo).exists():
            anota(nome, linha_de(texto, m.start()), f"link quebrado: {alvo}")

    # 8. ancoras internas
    ids = set(re.findall(r'id="([^"]+)"', texto))
    for m in re.finditer(r'href="#([^"]+)"', texto):
        if m.group(1) and m.group(1) not in ids:
            anota(nome, linha_de(texto, m.start()), f"ancora sem destino: #{m.group(1)}")

    # 9. imagens referenciadas
    for m in re.finditer(r'(?:src|srcset|content)="(img/[^"]+)"', texto):
        if not (RAIZ / m.group(1)).exists():
            anota(nome, linha_de(texto, m.start()), f"imagem ausente: {m.group(1)}")

    # 10. texto visivel: erros de digitacao.
    # Tag vira string vazia, nao espaco: remover a tag nao pode inventar
    # separacao entre palavra e pontuacao que o leitor nunca ve.
    visivel = re.sub(r"<(script|style)\b.*?</\1>", " ", texto, flags=re.S)
    visivel = re.sub(r"<[^>]+>", "", visivel)
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", visivel)
                         if unicodedata.category(c) != "Mn").lower()
    for padrao, sugestao in ERROS_COMUNS:
        for m in re.finditer(padrao, sem_acento):
            trecho = " ".join(sem_acento[max(0, m.start() - 30):m.end() + 30].split())
            anota(nome, 0, f"{sugestao}: ...{trecho}...", grave=False)

    # 11. espaco antes de pontuacao, na mesma linha
    for m in re.finditer(r"\w[ \t]+[,.;:!?]", visivel):
        anota(nome, 0, f"espaco antes de pontuacao: {m.group(0)!r}", grave=False)

    # 12. acentos abolidos pelo Acordo Ortografico de 1990
    for errado, certo in (("joia", "joi"), ("ideia", "idei"), ("heroico", "heroic"),
                          ("plateia", "platei"), ("assembleia", "assemblei"),
                          ("enjoo", "enjo"), ("voo", "vo"), ("feiura", "feiur")):
        for m in re.finditer(rf"\b{certo}[aeiou]?s?\b", visivel, re.I):
            if any(ch in m.group(0) for ch in "óéêôúí"):
                anota(nome, 0, f"acento abolido: {m.group(0)} -> {errado}", grave=False)


# --- imagens orfas e peso ---
usadas = set()
for pagina in PAGINAS:
    usadas.update(re.findall(r'(?:src|srcset|content)="img/([^"]+)"',
                             pagina.read_text(encoding="utf-8")))
for f in sorted((RAIZ / "img").iterdir()):
    if f.is_file():
        if f.name not in usadas:
            anota("img/", 0, f"orfa: {f.name}")
        kb = f.stat().st_size / 1024
        if kb > 500:
            anota("img/", 0, f"{f.name} com {kb:.0f} KB", grave=False)

graves = [p for p in problemas if p[0]]
leves = [p for p in problemas if not p[0]]

for titulo, grupo in (("GRAVE", graves), ("LEVE", leves)):
    print(f"\n===== {titulo} ({len(grupo)}) =====")
    for _, pagina, linha, msg in grupo:
        print(f"  {pagina}:{linha or '-'}  {msg}")

print(f"\ntotal: {len(graves)} graves, {len(leves)} leves")
