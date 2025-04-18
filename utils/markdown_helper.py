import markdown
from flask import Markup

def render_markdown(text):
    """
    Render markdown text to safe HTML
    """
    # Convert markdown to HTML
    html = markdown.markdown(text, extensions=['extra', 'codehilite', 'nl2br'])
    # Mark as safe HTML for Flask
    return Markup(html)
