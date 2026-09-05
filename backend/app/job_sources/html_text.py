import html as html_module

from bs4 import BeautifulSoup


def html_to_text(content: str) -> str:
    """Strip HTML down to plain text.

    Some job boards (e.g. Greenhouse) return this field HTML-entity-encoded
    on top of the markup itself (`&lt;h2&gt;...&lt;/h2&gt;` rather than real
    `<h2>` tags), so an initial unescape is needed before the tags are
    actually parseable — otherwise BeautifulSoup sees plain text with no
    tags to strip, and get_text() just unescapes the entities back into
    literal HTML.
    """
    if not content:
        return ""
    unescaped = html_module.unescape(content)
    soup = BeautifulSoup(unescaped, "html.parser")
    return soup.get_text(separator="\n").strip()
