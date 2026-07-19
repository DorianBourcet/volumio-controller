import re
import textwrap

DISPLAY_WIDTH = 12

DEFAULT_IGNORABLE_PATTERNS: list[str] = [
  r'\sle', r'le\s', r'^le',
  r'\sla', r'la\s', r'^la',
  r'\sde', r'de\s',
  r"\sd'", r"d'\s",
]

_TEXT_PART_RE = re.compile(r'([^\.]\.|[^\.]|\.)')
_LENGTH_RE = re.compile(r'(?!^\.)([^\.]\.|[^\.]|\.)')


def format_min_sec(seconds: int) -> str:
  minutes, sec = divmod(seconds, 60)
  return f'{minutes:02d}.{sec:02d}'


def get_length(text: str) -> int:
  return len(_LENGTH_RE.findall(text))


def split_text(text: str) -> list[str]:
  return _TEXT_PART_RE.findall(text)


def truncate(s: str, limit: int) -> str:
  return textwrap.shorten(s, width=limit, placeholder='...')


def get_max_length(words: list[str]) -> int:
  return max((get_length(w) for w in words), default=0)


def fit_text(text: str) -> str:
  if get_length(text) > DISPLAY_WIDTH:
    return shorten_text(text)
  return text


def spread_text(text: str) -> str:
  if get_length(text) <= 3 and ' ' not in text:
    return ' '.join(_TEXT_PART_RE.findall(text))
  return text


def shorten_text(text: str, ignorable_patterns: list[str] | None = None) -> str:
  if ignorable_patterns is None:
    ignorable_patterns = DEFAULT_IGNORABLE_PATTERNS
  pattern = '(' + '|'.join(ignorable_patterns) + ')'
  text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
  text = text.strip()
  text = re.sub(r'\s{2,}', ' ', text)
  length = get_length(text)
  if length <= DISPLAY_WIDTH:
    return text
  words = text.split()
  nb_words = len(words)
  surplus = length - DISPLAY_WIDTH
  if nb_words > 1:
    if nb_words > 4:
      words = words[:4]
      text = ' '.join(words)
      length = get_length(text)
      surplus = length - DISPLAY_WIDTH
    while surplus > 0:
      max_word_length = get_max_length(words)
      shrunk = False
      for i in range(len(words)):
        word_length = get_length(words[i])
        if word_length <= 2:
          continue
        if word_length >= max_word_length:
          splitted = split_text(words[i])
          splitted.pop()
          words[i] = ''.join(splitted)
          if re.search(r'\.$', words[i]) is None:
            words[i] += '.'
          surplus -= 1
          shrunk = True
          break
      if not shrunk:
        break
    return ' '.join(words)
  splitted = split_text(text)
  return ''.join(splitted[:DISPLAY_WIDTH])
