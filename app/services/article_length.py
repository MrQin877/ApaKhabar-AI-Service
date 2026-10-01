"""Content word count excludes title and excerpt; never cut a sentence mid-claim."""
import re
from app.providers.models import ModelError

MAX_ARTICLE_WORDS = 250


def word_count(article):
    return len((' '.join([article.lead, *article.body])).split())


def enforce_word_limit(article):
    if word_count(article) <= MAX_ARTICLE_WORDS:
        return article
    paragraphs, remaining = [], MAX_ARTICLE_WORDS
    for paragraph in [article.lead, *article.body]:
        kept = []
        for sentence in re.split(r'(?<=[.!?])\s+', paragraph.strip()):
            size = len(sentence.split())
            if size > remaining:
                break
            kept.append(sentence)
            remaining -= size
        if kept:
            paragraphs.append(' '.join(kept))
        if len(' '.join(kept).split()) < len(paragraph.split()):
            break
    if not paragraphs:
        raise ModelError('The draft cannot fit within 250 words without cutting a sentence. Retry generation.')
    article.lead = paragraphs[0]
    article.body = paragraphs[1:] or ['']
    article.warnings.append('Article shortened at a sentence boundary to meet the 250-word limit; review fact coverage.')
    return article
