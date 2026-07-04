"""Картинки для карточек слов/ролей и карточки шпиона.

Вместо AI-генерации "на лету" бот берёт готовые картинки из папки
app/assets/images/. Имя файла — это "слаг" от слова/роли (см. slugify),
любое из расширений .png/.jpg/.jpeg/.webp.

Если подходящего файла нет — рисуется простая текстовая карточка через
Pillow, чтобы бот продолжал работать даже без полного набора картинок.

Полный список нужных файлов — в IMAGES_NEEDED.md в корне проекта.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(__file__).parent / "assets" / "images"
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
SPY_SLUG = "_spy"  # начинается с "_", чтобы не совпасть ни с одним словом


def slugify(text: str) -> str:
    """Превращает слово/роль в безопасное имя файла.
    Пример: 'Роберт Дауни мл.' -> 'роберт_дауни_мл'"""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def _find_local_image(slug: str) -> Path | None:
    for ext in SUPPORTED_EXTENSIONS:
        path = IMAGES_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    return None


async def get_image_for_word(word: str) -> bytes:
    slug = slugify(word)
    path = _find_local_image(slug)
    if path:
        return path.read_bytes()
    logger.warning(
        "Картинка для слова '%s' (файл %s.*) не найдена в %s — использую текстовую заглушку. "
        "Список нужных файлов — в IMAGES_NEEDED.md",
        word, slug, IMAGES_DIR,
    )
    return _placeholder_card(word)


async def get_spy_image() -> bytes:
    path = _find_local_image(SPY_SLUG)
    if path:
        return path.read_bytes()
    logger.warning(
        "Картинка шпиона (файл %s.* в %s) не найдена — использую текстовую заглушку.",
        SPY_SLUG, IMAGES_DIR,
    )
    return _placeholder_card("Шпион")


def _placeholder_card(text: str) -> bytes:
    import io

    from PIL import Image, ImageDraw, ImageFont

    width, height = 800, 800
    img = Image.new("RGB", (width, height), color=(28, 30, 38))
    draw = ImageDraw.Draw(img)

    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            font = ImageFont.truetype(path, 46)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    words = text.split()
    lines: list[str] = []
    line = ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font=font) > width - 120:
            lines.append(line)
            line = w
        else:
            line = test
    lines.append(line)

    line_height = 62
    total_h = len(lines) * line_height
    y = (height - total_h) // 2
    for line in lines:
        line_w = draw.textlength(line, font=font)
        draw.text(((width - line_w) / 2, y), line, font=font, fill=(240, 240, 245))
        y += line_height

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
