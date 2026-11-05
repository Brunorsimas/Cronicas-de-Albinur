# -*- coding: utf-8 -*-
"""Verifica links internos, imagens e HTML das Crônicas de Albinur."""
import io, os, re, glob
from html.parser import HTMLParser

DST = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(DST, 'img')
EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif')
pages = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DST, '*.html')))


def exists(rel):
    """Caminho relativo a raiz do site existe? (case-insensitive, como no Windows)"""
    parts = rel.replace('\\', '/').split('/')
    cur = DST
    for part in parts:
        try:
            match = next(f for f in os.listdir(cur) if f.lower() == part.lower())
        except (StopIteration, NotADirectoryError, FileNotFoundError):
            return False
        cur = os.path.join(cur, match)
    return True

VOID = {'img', 'br', 'hr', 'meta', 'link', 'input', 'source', 'path', 'svg'}


def refs(s):
    """URLs de imagem da pagina: src="..." e cada candidato de srcset."""
    out = list(re.findall(r'src="([^"]+)"', s))
    for ss in re.findall(r'srcset="([^"]+)"', s):
        out += [c.strip().split()[0] for c in ss.split(',') if c.strip()]
    return out


class Check(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errs = [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID or tag == 'svg':
            return
        self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            t, ln = self.stack.pop()
            if t == tag:
                return
            self.errs.append(f'  tag <{t}> (linha {ln}) nao fechada antes de </{tag}>')
            return
        self.errs.append(f'  </{tag}> sem abertura')


fails = 0
for pg in pages:
    s = io.open(os.path.join(DST, pg), encoding='utf-8').read()
    probs = []

    # links internos
    for href in re.findall(r'href="([^"#:]+\.html)"', s):
        if not exists(href):
            probs.append(f'  link quebrado -> {href}')
    # css
    for href in re.findall(r'href="([^"#:]+\.css)"', s):
        if not exists(href):
            probs.append(f'  css ausente -> {href}')
    # imagens locais
    for src in refs(s):
        if src.startswith(('http', 'data:')):
            continue
        if not exists(src):
            probs.append(f'  imagem ausente -> {src}')
        if re.search(r"[ '\"]", src):
            probs.append(f'  nome inseguro em URL -> {src}')
    # encoding / mojibake
    if 'Ã' in s or 'â€' in s:
        probs.append('  possivel mojibake (encoding)')
    # estrutura
    c = Check()
    c.feed(s)
    probs += c.errs
    if c.stack:
        probs += [f'  tag <{t}> (linha {ln}) nunca fechada' for t, ln in c.stack if t not in ('html', 'body')]

    if probs:
        fails += 1
        print(f'[FALHA] {pg}')
        for x in dict.fromkeys(probs):
            print(x)
    else:
        print(f'[ok] {pg}')

# imagens orfas
used = set()
for pg in pages:
    s = io.open(os.path.join(DST, pg), encoding='utf-8').read()
    used |= {os.path.basename(m).lower() for m in refs(s)}
orphan = [f for f in os.listdir(IMG) if f.lower().endswith(EXTS) and f.lower() not in used]
print('\nimagens nao usadas:', orphan or 'nenhuma')
print('paginas com falha:', fails, '/', len(pages))
