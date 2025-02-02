import html
import random
import re
from typing import Optional

from genanki import Model, Deck, Note, Package
from markdown import markdown

from database import Problem
from utils import parser as conf


def random_id():
    return random.randrange(1 << 30, 1 << 31)


def safe_html_escape(content: Optional[str]) -> str:
    """Safely escape HTML content, handling None values."""
    if content is None:
        return ""
    return html.escape(content)


def markdown_to_html(content: str):
    # First escape any HTML tags in the content
    content = safe_html_escape(content)

    # replace the math symbol "$$x$$" to "\(x\)" to make it compatible with mathjax
    content = re.sub(pattern=r"\$\$(.*?)\$\$", repl=r"\(\1\)", string=content)

    # also need to load the mathjax and toc extensions
    return markdown(content, extensions=["mdx_math", "toc", "fenced_code", "tables"])


def code_to_html(source, language):
    # Escape the source code before wrapping in markdown
    source = safe_html_escape(source)
    content = f"```{language}\n{source}\n```"
    return markdown(content, extensions=["fenced_code"])


def get_anki_model():
    with open(conf.get("Anki", "front"), "r") as f:
        front_template = f.read()
    with open(conf.get("Anki", "back"), "r") as f:
        back_template = f.read()
    with open(conf.get("Anki", "css"), "r") as f:
        css = f.read()

    anki_model = Model(
        model_id=1048217874,
        name="LeetCode",
        fields=[
            {"name": "ID"},
            {"name": "Title"},
            {"name": "TitleSlug"},
            {"name": "Difficulty"},
            {"name": "Description"},
            {"name": "Tags"},
            {"name": "TagSlugs"},
            {"name": "Solution"},
            {"name": "Submission"},
        ],
        templates=[{"name": "LeetCode", "qfmt": front_template, "afmt": back_template}],
        css=css,
    )
    return anki_model


def make_note(problem):
    print(f"📓 Producing note for problem: {problem.title}...")
    tags = ";".join([safe_html_escape(t.name) for t in problem.tags])
    tags_slug = ";".join([safe_html_escape(t.slug) for t in problem.tags])

    try:
        solution = problem.solution.get()
    except Exception:
        solution = None

    codes = []
    for item in problem.submissions:
        source = re.sub(
            r"(\\u[\s\S]{4})",
            lambda x: x.group(1).encode("utf-8").decode("unicode-escape"),
            item.source,
        )
        output = code_to_html(source, item.language)
        codes.append(output)
    submissions = "\n".join(codes)

    note = Note(
        model=get_anki_model(),
        fields=[
            safe_html_escape(str(problem.display_id)),
            safe_html_escape(problem.title),
            safe_html_escape(problem.slug),
            safe_html_escape(problem.level),
            safe_html_escape(problem.description),
            tags,
            tags_slug,
            markdown_to_html(solution.content) if solution else "",
            submissions,
        ],
        guid=str(problem.display_id),
        sort_field=str(problem.display_id),
        tags=[t.slug for t in problem.tags],
    )
    return note


def render_anki():
    problems = Problem.select().order_by(Problem.display_id)

    anki_deck = Deck(deck_id=random_id(), name="LeetCode")

    for problem in problems:
        note = make_note(problem)
        anki_deck.add_note(note)

    path = conf.get("Anki", "output")
    Package(anki_deck).write_to_file(path)


if __name__ == "__main__":
    render_anki()
