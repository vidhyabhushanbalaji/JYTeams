"""Dependency-free text handling shared by the local (model-free) matchers.

Graph Add and Graph AI Search score folders and documents the same way, and one section may not
import another section's internals, so the vocabulary work lives here: markdown stripping,
tokenising, a crude plural stem, query coverage, IDF weights and a snippet extractor.

Nothing in this module reads configuration or touches the network. Each section supplies its own
adapters and may tune behaviour through :class:`ScoreConfig`, but the algorithm is shared — so a
folder that ranks high in a search suggestion ranks high for placement as well.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-z0-9]+")
#: Fences are dropped but the code inside is kept: an error code or a CLI name often appears
#: nowhere else in the document.
_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\s*|~~~[a-zA-Z0-9_+-]*\s*")
_INLINE_CODE = re.compile(r"`")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_HEADING_MARK = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^\s{0,3}[-*+]\s+|^\s{0,3}\d+\.\s+", re.MULTILINE)
_URL = re.compile(r"https?://\S+")
_HTML = re.compile(r"<[^>]+>")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$", re.MULTILINE)

#: Suffixes stripped by :func:`stem`, longest first so "ations" wins over "s".
_SUFFIXES = (
    "ations",
    "ation",
    "ions",
    "ion",
    "ments",
    "ment",
    "ings",
    "ing",
    "ers",
    "er",
    "ies",
    "ied",
    "es",
    "ed",
    "s",
)

#: Filler words with no topic signal. The markdown suffixes are here because file names leak
#: them into the vocabulary (`readme.md` would otherwise match a query for "md").
_STOPWORD_TEXT = (
    "a about above after again all also am an and any are as at be because been before being "
    "below between both but by can cannot could did do does doing done down during each few "
    "for from further had has have having he her here hers him his how i if in into is it its "
    "itself just me more most my no nor not now of off on once only or other our out over own "
    "same she should so some such than that the their theirs them then there these they this "
    "those through to too under until up very was we were what when where which while who whom "
    "why will with would you your md mdx markdown txt"
)
STOPWORDS = frozenset(_STOPWORD_TEXT.split())

#: How often one term may count towards a score (a word repeated fifty times is not fifty
#: times more relevant).
TERM_REPEAT_CAP = 3


def strip_markdown(text: str) -> str:
    """Remove the parts of markdown that are formatting rather than content."""
    value = text or ""
    value = _FENCE.sub(" ", value)
    value = _INLINE_CODE.sub(" ", value)
    value = _LINK.sub(r"\1", value)
    value = _URL.sub(" ", value)
    value = _HTML.sub(" ", value)
    value = _HEADING_MARK.sub(" ", value)
    value = _BULLET.sub(" ", value)
    return " ".join(value.split())


def stem(word: str) -> str:
    """A light suffix stem, so "deployment" meets "deploy" and "releases" meets "release".

    Applied identically to queries and documents, so consistency matters more than linguistics:
    a shared stem for two words is safe even when it is not the "correct" one.
    """
    if len(word) <= 3:
        return word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            base = word[: -len(suffix)]
            if suffix in {"ies", "ied"}:
                base += "y"
            return base[:-1] if len(base) > 4 and base.endswith("e") else base
    return word[:-1] if len(word) > 4 and word.endswith("e") else word


def terms(text: str) -> frozenset[str]:
    """The stemmed vocabulary of a text, stopwords removed."""
    return frozenset(
        stem(word) for word in _WORD.findall(strip_markdown(text).lower()) if word not in STOPWORDS
    )


def term_counts(text: str) -> Counter[str]:
    """Stemmed term frequencies, stopwords removed (feeds the repeat-capped body score)."""
    counts: Counter[str] = Counter()
    for word in _WORD.findall(strip_markdown(text).lower()):
        if word not in STOPWORDS:
            counts[stem(word)] += 1
    return counts


def headings(text: str) -> tuple[str, ...]:
    """Every markdown heading title, in document order."""
    return tuple(match.strip() for match in _HEADING.findall(text or "") if match.strip())


def keywords(text: str, *, limit: int = 40) -> tuple[str, ...]:
    """The original words that best describe a text: most frequent first, then document order.

    A long document is a poor query (its vocabulary dilutes every comparison), so callers that
    match a whole document against short folder descriptions use this to build a compact query.
    """
    words = [
        word for word in _WORD.findall(strip_markdown(text or "").lower()) if word not in STOPWORDS
    ]
    if not words:
        return ()
    counts = Counter(stem(word) for word in words)
    wanted = {term for term, _ in counts.most_common(limit)}
    picked: list[str] = []
    seen: set[str] = set()
    for word in words:
        term = stem(word)
        if term in wanted and term not in seen:
            seen.add(term)
            picked.append(word)
    return tuple(picked)


def normalise_phrase(text: str) -> str:
    """A lowercased, whitespace-collapsed form used for exact-phrase checks."""
    return " ".join((text or "").lower().split())


def document_frequencies(texts: Iterable[str]) -> Counter[str]:
    """How many of ``texts`` contain each term."""
    frequencies: Counter[str] = Counter()
    for text in texts:
        frequencies.update(terms(text))
    return frequencies


def idf_map(frequencies: Mapping[str, int], total: int) -> dict[str, float]:
    """Smoothed inverse document frequency for every term seen in the corpus."""
    if total <= 0:
        return {}
    return {term: math.log((total + 1) / (count + 1)) + 1.0 for term, count in frequencies.items()}


@dataclass(frozen=True)
class Query:
    """A cleaned query plus the corpus weights used to score it.

    ``idf`` is optional: without it every term weighs the same, which is the right behaviour for
    short texts such as folder descriptions.
    """

    text: str
    terms: frozenset[str]
    phrase: str = ""
    idf: Mapping[str, float] = field(default_factory=dict)
    default_weight: float = 1.0
    #: Stem → the word the caller actually typed, so responses quote the query, not the stem.
    originals: Mapping[str, str] = field(default_factory=dict)

    def weight(self, term: str) -> float:
        """Corpus weight of one term; unknown terms weigh the most (they are the rarest)."""
        return float(self.idf.get(term, self.default_weight))

    def coverage(self, haystack: frozenset[str]) -> float:
        """Share of the query's terms present in ``haystack`` (0.0 … 1.0)."""
        if not self.terms:
            return 0.0
        return len(self.terms & haystack) / len(self.terms)

    def weighted_match(self, counts: Mapping[str, int], *, cap: int = TERM_REPEAT_CAP) -> float:
        """Coverage of the query by a long text, weighted by IDF and capped per term.

        One occurrence of a term already counts fully — a document either covers the query or
        it does not — and repeats up to ``cap`` add weight, so a page that mentions the topic
        five times outranks one that mentions it once.
        """
        weights = {term: self.weight(term) for term in self.terms}
        total = sum(weights.values())
        if total <= 0:
            return 0.0
        hit = sum(weight * min(int(counts.get(term, 0)), cap) for term, weight in weights.items())
        return min(1.0, hit / total)

    def matched(self, haystack: frozenset[str]) -> tuple[str, ...]:
        """The query terms found in ``haystack``, as the caller typed them, sorted."""
        words = {self.originals.get(term, term) for term in self.terms & haystack}
        return tuple(sorted(words))


def build_query(text: str, corpus: Sequence[str] = ()) -> Query:
    """Clean a query and weight its terms against ``corpus`` (folder names and descriptions)."""
    cleaned = " ".join((text or "").split())
    idf: dict[str, float] = {}
    default_weight = 1.0
    if corpus:
        idf = idf_map(document_frequencies(corpus), len(corpus))
        if idf:
            default_weight = max(idf.values())
    originals: dict[str, str] = {}
    for word in _WORD.findall(cleaned.lower()):
        if word not in STOPWORDS:
            originals.setdefault(stem(word), word)
    return Query(
        text=cleaned,
        terms=terms(cleaned),
        phrase=normalise_phrase(cleaned),
        idf=idf,
        default_weight=default_weight,
        originals=originals,
    )


@dataclass(frozen=True)
class ScoreConfig:
    """Weights for the local scorer.

    ``version`` travels into API responses, so a change in ranking behaviour is visible to a
    client (and to a snapshot test) instead of silently rearranging results.
    """

    folder_description_weight: float = 0.55
    folder_name_weight: float = 0.25
    folder_contains_weight: float = 0.20
    document_body_weight: float = 0.85
    document_name_weight: float = 0.15
    phrase_bonus: float = 0.15
    version: str = "local-1"


def score_folder_texts(
    query: Query,
    *,
    name: str,
    description: str,
    contains: Sequence[str] = (),
    config: ScoreConfig = ScoreConfig(),
) -> float:
    """Relevance of one folder to a query, from its name, description and contents (0.0 … 1.0)."""
    if not query.terms:
        return 0.0
    score = (
        config.folder_description_weight * query.coverage(terms(description))
        + config.folder_name_weight * query.coverage(terms(name))
        + config.folder_contains_weight * query.coverage(terms(" ".join(contains)))
    )
    if query.phrase and query.phrase in normalise_phrase(f"{name} {description}"):
        score += config.phrase_bonus
    return min(1.0, round(score, 4))


def score_document_texts(
    query: Query,
    *,
    name: str,
    body: str,
    config: ScoreConfig = ScoreConfig(),
) -> float:
    """Relevance of one document to a query, from its name and full text (0.0 … 1.0)."""
    if not query.terms:
        return 0.0
    body_score = query.weighted_match(term_counts(body))
    name_score = query.coverage(terms(name))
    if body_score <= 0.0 and name_score <= 0.0:
        return 0.0
    score = config.document_body_weight * body_score + config.document_name_weight * name_score
    if query.phrase and query.phrase in normalise_phrase(body):
        score += config.phrase_bonus
    return min(1.0, round(score, 4))


def clip_description(text: str, limit: int = 300) -> str:
    """Collapse whitespace and cut a folder description to a hard character limit.

    The cut lands on the last word boundary that fits and the ellipsis counts towards the
    limit, so the result is always ``len(result) <= limit``.
    """
    collapsed = " ".join((text or "").split())
    if limit <= 0:
        return ""
    if len(collapsed) <= limit:
        return collapsed
    cut = collapsed[: max(1, limit - 1)].rstrip()
    boundary = cut.rfind(" ")
    if boundary >= limit // 2:
        cut = cut[:boundary]
    return (cut.rstrip(" ,;:-–—") + "…")[:limit]


def excerpt(text: str, needles: Iterable[str], width: int = 200) -> str:
    """A readable snippet of ``text`` around the first place a query term appears."""
    collapsed = " ".join(strip_markdown(text).split())
    if not collapsed:
        return ""
    wanted = {needle.casefold() for needle in needles if needle}
    lowered = collapsed.casefold()
    start = -1
    for needle in wanted:
        found = lowered.find(needle)
        if found != -1 and (start == -1 or found < start):
            start = found
    if start == -1:
        return _ellipsis(collapsed[:width], len(collapsed) > width)
    begin = max(0, start - width // 2)
    end = min(len(collapsed), begin + width)
    return _ellipsis(collapsed[begin:end], begin > 0)


def _ellipsis(value: str, truncated: bool) -> str:
    snippet = value.strip()
    return f"…{snippet}…" if truncated else snippet
