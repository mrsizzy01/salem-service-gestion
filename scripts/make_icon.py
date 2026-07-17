"""Génère l'icône de l'application (iconset macOS).

Dessine un pictogramme simple (caisse enregistreuse stylisée) avec PIL
aux tailles exigées par macOS, dans ``resources/AppIcon.iconset``.
La conversion en ``.icns`` se fait avec ``iconutil`` (macOS uniquement) :

    iconutil -c icns resources/AppIcon.iconset -o resources/AppIcon.icns

L'icône est facultative : sans elle, py2app utilise l'icône par défaut.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 32, 64, 128, 256, 512, 1024]
OUT = Path(__file__).resolve().parent.parent / "resources" / "AppIcon.iconset"

ACCENT = (10, 132, 255, 255)      # #0A84FF
WHITE = (255, 255, 255, 255)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill) -> None:
    """Dessine un rectangle arrondi."""
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def draw_icon(size: int) -> Image.Image:
    """Dessine l'icône à la taille demandée."""
    scale = size / 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fond arrondi bleu (style icône macOS).
    margin = int(48 * scale)
    rounded_rect(draw, (margin, margin, size - margin, size - margin),
                 int(220 * scale), ACCENT)

    # Corps de la caisse.
    x0, y0 = int(220 * scale), int(420 * scale)
    x1, y1 = int(804 * scale), int(760 * scale)
    rounded_rect(draw, (x0, y0, x1, y1), int(60 * scale), WHITE)

    # Écran de la caisse.
    rounded_rect(draw, (int(340 * scale), int(220 * scale),
                        int(684 * scale), int(420 * scale)), int(40 * scale), WHITE)
    # Détail écran.
    draw.rectangle((int(380 * scale), int(260 * scale),
                    int(644 * scale), int(300 * scale)), fill=ACCENT)
    draw.rectangle((int(380 * scale), int(320 * scale),
                    int(564 * scale), int(360 * scale)), fill=ACCENT)

    # Tiroir.
    draw.rectangle((int(260 * scale), int(560 * scale),
                    int(764 * scale), int(600 * scale)), fill=ACCENT)
    # Poignée du tiroir.
    rounded_rect(draw, (int(452 * scale), int(650 * scale),
                        int(572 * scale), int(700 * scale)), int(24 * scale), ACCENT)
    return img


def main() -> None:
    """Génère toutes les tailles dans l'iconset."""
    OUT.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        img = draw_icon(size)
        img.save(OUT / f"icon_{size}x{size}.png")
        if size <= 512:
            # Variantes @2x.
            img2x = draw_icon(size * 2)
            img2x.save(OUT / f"icon_{size}x{size}@2x.png")
    print(f"Iconset généré dans {OUT}")
    print("Convertir en .icns (macOS) :")
    print(f"  iconutil -c icns {OUT} -o {OUT.parent / 'AppIcon.icns'}")


if __name__ == "__main__":
    main()
