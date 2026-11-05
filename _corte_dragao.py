"""Recorte do dragao mantendo rocha, carcaca, asa de tras e cauda.

Por que nao e uma chamada de rembg:

1. rembg sozinho descarta rocha e carcaca -- os modelos segmentam so o
   "objeto principal". u2net tambem engole a nuvem inteira a direita.
2. Limiar de luminancia nao separa nada: a asa de tras mede ~245, mais clara
   que o proprio ceu (~241), e com a mesma cor (sat 3.8 vs 3.9).
3. Flood fill so por luminancia vaza para dentro da asa, porque a transicao
   ceu->asa e um gradiente suave, sem degrau.

O que separa de verdade e o GRADIENTE: a borda da asa marca ~19 no sobel, a
textura de nuvem fica abaixo de 3. O flood fill do ceu corre por pixels
claros E de gradiente baixo, entao a borda da asa vira barreira que ele nao
atravessa -- mesmo a asa sendo mais clara que o ceu.

Sobra um caso: bolsoes de ceu encerrados entre asa, perna e cauda nao tocam a
borda do quadro, entao o flood fill nao chega neles. Removidos por area. A
caixa da asa e restaurada depois, porque la o "claro grande" e o proprio bicho.

ponytail: CX_ASA e coordenada desta arte. Serve porque e uma imagem so. Outra
arte exige remedir -- gere a grade de referencia antes.
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

SRC = "img/Dragao-Nuvens.jpg"
OUT = "img/Dragao-Nuvens"
THRESH = 100.0   # dragao ~40, rocha ~67, nuvem mais escura ~105
GRAD = 8.0       # borda da asa ~19, textura de nuvem <3
BOLSAO = 15000   # area minima para um claro encerrado contar como ceu
CX_ASA = (199, 607, 1096, 1560)  # asa de tras, cinza palida

src = Image.open(SRC).convert("RGB")
lum = np.asarray(src.convert("L"), dtype=np.float32)

# gradiente: revela contorno de objeto mesmo sem contraste de brilho
suave = ndimage.gaussian_filter(lum, 2.0)
grad = np.hypot(ndimage.sobel(suave, 0), ndimage.sobel(suave, 1)) / 4.0

# ceu = claro, liso e conectado a borda do quadro
passavel = (lum >= THRESH) & (grad < GRAD)
semente = np.zeros_like(passavel)
semente[0, :] = semente[-1, :] = semente[:, 0] = semente[:, -1] = True
semente &= passavel
base = ~ndimage.binary_propagation(semente, mask=passavel)

# bolsoes de ceu encerrados pelo corpo: claros e grandes, mas sem saida
claro = ndimage.binary_opening(lum >= THRESH, structure=np.ones((5, 5))) & base
rot, n = ndimage.label(claro)
tam = ndimage.sum(claro, rot, range(1, n + 1))
objeto = base & ~np.isin(rot, [i + 1 for i, t in enumerate(tam) if t > BOLSAO])

# dentro da caixa da asa o claro grande e o bicho, nao ceu: desfaz a limpeza
y0, y1, x0, x1 = CX_ASA
objeto[y0:y1, x0:x1] = base[y0:y1, x0:x1]

objeto = ndimage.binary_closing(objeto, structure=np.ones((5, 5)))

# respingos soltos caem fora
rot, n = ndimage.label(objeto)
if n > 1:
    tam = ndimage.sum(objeto, rot, range(1, n + 1))
    objeto = rot == (int(np.argmax(tam)) + 1)

a = Image.fromarray((objeto * 255).astype(np.uint8))
a = a.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.GaussianBlur(1.0))

out = src.convert("RGBA")
out.putalpha(a)
out = out.crop(a.getbbox())
out.save(f"{OUT}.png")
out.save(f"{OUT}.webp", quality=90, method=6)

# --- checagem, em coordenadas da imagem original ---
def cob(y0, y1, x0, x1):
    return objeto[y0:y1, x0:x1].mean()

assert cob(260, 440, 1120, 1330) > 0.70, "asa de tras sumiu"
assert cob(1150, 1300, 2250, 2700) > 0.50, "curva da cauda sumiu"
assert cob(1000, 1100, 2500, 2600) > 0.40, "ponta da cauda sumiu"
assert cob(1400, 1530, 900, 1400) > 0.90, "rocha perdida"
assert cob(1250, 1450, 1150, 1500) > 0.90, "carcaca perdida"
assert cob(600, 900, 1500, 1700) > 0.85, "corpo furado"
assert cob(200, 600, 100, 700) < 0.05, "ceu esquerdo vazou"
assert cob(60, 160, 1100, 1400) < 0.05, "ceu acima da asa vazou"
assert cob(1100, 1450, 50, 400) < 0.10, "nuvem baixa esquerda vazou"
assert cob(300, 800, 1900, 2300) < 0.60, "nuvem a direita vazou"
assert cob(800, 950, 2300, 2700) < 0.20, "nuvem acima da cauda vazou"

print("ok", out.size, "opaco", f"{100 * objeto.mean():.1f}%")
