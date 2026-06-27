"""Markdown → Telegram HTML conversion."""

from frontdesk.infrastructure.channels.telegram_format import markdown_to_telegram_html as to_html


def test_bold_italic_strike() -> None:
    assert to_html("**bold**") == "<b>bold</b>"
    assert to_html("__bold__") == "<b>bold</b>"
    assert to_html("*italic*") == "<i>italic</i>"
    assert to_html("_italic_") == "<i>italic</i>"
    assert to_html("~~gone~~") == "<s>gone</s>"


def test_bold_then_italic_in_one_line() -> None:
    assert to_html("**B** and *i*") == "<b>B</b> and <i>i</i>"


def test_links() -> None:
    assert to_html("[site](https://x.com)") == '<a href="https://x.com">site</a>'


def test_headings_become_bold() -> None:
    assert to_html("# Title") == "<b>Title</b>"
    assert to_html("### Sub") == "<b>Sub</b>"


def test_bullets_become_dots() -> None:
    assert to_html("- one\n- two") == "• one\n• two"


def test_tables_lose_pipes_and_separator() -> None:
    table = "| Time | Status |\n|------|--------|\n| 9:00 | free |"
    out = to_html(table)
    assert "|" not in out
    assert "Time · Status" in out
    assert "9:00 · free" in out
    assert "---" not in out


def test_html_special_chars_are_escaped() -> None:
    assert to_html("a < b & c > d") == "a &lt; b &amp; c &gt; d"


def test_code_is_preserved_and_inner_markdown_ignored() -> None:
    assert to_html("`**x**`") == "<code>**x**</code>"  # not turned into bold
    assert to_html("`a<b`") == "<code>a&lt;b</code>"  # escaped inside code


def test_plain_text_unchanged() -> None:
    assert to_html("Booked for 09:00 (America/Montevideo). 🎉") == (
        "Booked for 09:00 (America/Montevideo). 🎉"
    )


def test_underscores_in_words_are_not_italic() -> None:
    assert to_html("see file_name_here") == "see file_name_here"
