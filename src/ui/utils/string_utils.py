"""String manipulation utilities for HTML processing."""

import re


def strip_html(html_str: str) -> str:
    """Strip HTML tags from a string for plain text preview.

    Removes <style> and <script> blocks entirely, then strips remaining
    HTML tags and decodes common HTML entities.

    Args:
        html_str: The HTML string to strip.

    Returns:
        Plain text with HTML tags removed and entities decoded.
    """
    if not html_str:
        return ""

    # Remove <style> and <script> blocks first (content + tags)
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove remaining tags
    clean = re.compile("<.*?>")
    text = re.sub(clean, "", text)

    # Replace common HTML entities
    return (
        text.replace("&nbsp;", " ")
        .replace("<", "<")
        .replace(">", ">")
        .replace("&", "&")
    )


def build_snippet_html(original_html: str, plain_snippet: str) -> str:
    """Build a safe HTML snippet for table display.

    Takes the original HTML and extracts a portion around the first few words
    of the plain text snippet, preserving inline formatting tags.

    Args:
        original_html: The full HTML content.
        plain_snippet: The plain text snippet to locate in the HTML.

    Returns:
        An HTML snippet suitable for display in a table cell.
    """
    if not original_html:
        return plain_snippet

    try:
        # Remove <style>, <script>, <head> blocks entirely
        cleaned = re.sub(
            r"<(style|script|head)[^>]*>.*?</\1>",
            " ",
            original_html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove comments
        cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)

        # Remove wrapper tags
        cleaned = re.sub(
            r"</?(html|body|meta|title|div|section|article|header|footer)[^>]*/?>",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )

        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Find where the first word of our snippet appears in the plain text
        words = plain_snippet.rstrip(".").split()
        if not words:
            return plain_snippet

        # Find the plain-text offset of our first word
        plain = re.sub(r"<[^>]+>", "", cleaned)
        plain = re.sub(r"\s+", " ", plain).strip()
        idx = plain.find(words[0])

        if idx < 0:
            return plain_snippet

        # Walk HTML to find the HTML position corresponding to plain-text idx
        pos = 0
        in_tag = False

        for i, ch in enumerate(cleaned):
            if ch == "<":
                in_tag = True
                continue
            if ch == ">":
                in_tag = False
                continue
            if not in_tag:
                if pos == idx:
                    # Back up to include any opening tags
                    search_back = cleaned[:i]
                    last_open = search_back.rfind("<")
                    start = (
                        last_open
                        if last_open >= 0 and ">" not in cleaned[last_open:i]
                        else i
                    )

                    # Extract enough HTML to cover ~3 words of plain text
                    target = len(" ".join(words[:3])) + 5  # small margin
                    cp = 0
                    end = start
                    in_t = False

                    for j in range(start, len(cleaned)):
                        c = cleaned[j]
                        if c == "<":
                            in_t = True
                            continue
                        if c == ">":
                            in_t = False
                            continue
                        if not in_t:
                            cp += 1
                            if cp >= target:
                                end = j + 1
                                # Include up to 2 closing tags right after
                                rest = cleaned[j + 1 : j + 40]
                                for cm in re.finditer(r"</(\w+)>", rest):
                                    end = cm.end() + j + 1
                                    break
                                break

                    snippet = cleaned[start:end]

                    # Close any unclosed inline tags
                    for tag in re.findall(
                        r"<(b|i|u|strong|em)(?:\s[^>]*)?>", snippet, re.IGNORECASE
                    ):
                        close_pattern = re.compile(rf"</{tag}>", re.IGNORECASE)
                        if not close_pattern.search(snippet):
                            snippet += f"</{tag}>"

                    return snippet
                pos += 1

        return plain_snippet
    except Exception:
        return plain_snippet