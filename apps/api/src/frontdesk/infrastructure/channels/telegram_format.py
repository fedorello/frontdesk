"""Convert the model's Markdown to the small HTML subset Telegram renders.

Telegram's ``parse_mode=HTML`` supports <b> <i> <u> <s> <a> <code> <pre> — but not
headings, tables, or lists. We escape the three HTML-significant characters, map the
common Markdown a chat model emits onto those tags, and degrade headings/tables/bullets
to readable plain text. See https://core.telegram.org/bots/api#html-style.
"""

import re

# Fenced/inline code is protected first so its contents aren't treated as Markdown.
_CODE_BLOCK = re.compile(r"```[^\n]*\n?(.*?)```", re.DOTALL)
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*$", re.MULTILINE)
_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.DOTALL)
_STRIKE = re.compile(r"~~(.+?)~~", re.DOTALL)
_ITALIC_STAR = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
_ITALIC_USCORE = re.compile(r"(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_TABLE_SEP = re.compile(r"^[ \t]*\|?[ \t:|-]*-[ \t:|-]*\|?[ \t]*$", re.MULTILINE)
_PIPE = re.compile(r"[ \t]*\|[ \t]*")
_BULLET = re.compile(r"^([ \t]*)[-*+][ \t]+", re.MULTILINE)
_SENTINEL = "\x00{}\x00"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markdown_to_telegram_html(text: str) -> str:
    """Best-effort Markdown → Telegram HTML. Plain text passes through unchanged (escaped)."""
    stash: list[tuple[str, str]] = []

    def protect(match: re.Match[str], tag: str) -> str:
        stash.append((tag, match.group(1)))
        return _SENTINEL.format(len(stash) - 1)

    text = _CODE_BLOCK.sub(lambda m: protect(m, "pre"), text)
    text = _CODE_SPAN.sub(lambda m: protect(m, "code"), text)

    text = _escape(text)
    text = _TABLE_SEP.sub("", text)  # drop "|---|---|" rows
    text = "\n".join(_PIPE.sub(" · ", line).strip(" ·") for line in text.split("\n"))
    text = _HEADING.sub(r"<b>\1</b>", text)
    text = _BOLD.sub(lambda m: f"<b>{m.group(1) or m.group(2)}</b>", text)
    text = _STRIKE.sub(r"<s>\1</s>", text)
    text = _ITALIC_STAR.sub(r"<i>\1</i>", text)
    text = _ITALIC_USCORE.sub(r"<i>\1</i>", text)
    text = _LINK.sub(r'<a href="\2">\1</a>', text)
    text = _BULLET.sub(r"\1• ", text)

    def restore(match: re.Match[str]) -> str:
        tag, content = stash[int(match.group(1))]
        return f"<{tag}>{_escape(content)}</{tag}>"

    return re.sub(r"\x00(\d+)\x00", restore, text)
