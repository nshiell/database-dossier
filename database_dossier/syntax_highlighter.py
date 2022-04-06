from pygments import highlight as _highlight
from pygments.lexers import SqlLexer
from pygments.formatters import HtmlFormatter


def style():
    style = HtmlFormatter().get_style_defs()
    return style


def create_formatter(stylesheet):
    formatter = HtmlFormatter(cssstyles=stylesheet, style='native')
    formatter.noclasses = True

    return formatter


def highlight(text, formatter):
    extra_char = False
    if len(text) and text[-1] == "\n":
        extra_char = True
        text+= 'z'
    
    # Generated HTML contains unnecessary newline at the end
    # before </pre> closing tag.
    # We need to remove that newline because it's screwing up
    # QTextEdit formatting and is being displayed
    # as a non-editable whitespace.

    highlighted_text = _highlight(text, SqlLexer(), formatter).strip()

    if extra_char:
        highlighted_text = '</span>'.join(highlighted_text.rsplit('z</span>', 1))

    return highlighted_text