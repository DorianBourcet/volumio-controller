import utils


class TestFormatMinSec:
  def test_zero(self):
    assert utils.format_min_sec(0) == '00.00'

  def test_under_minute(self):
    assert utils.format_min_sec(45) == '00.45'

  def test_round_minute(self):
    assert utils.format_min_sec(60) == '01.00'

  def test_long(self):
    assert utils.format_min_sec(3725) == '62.05'


class TestGetLength:
  def test_simple(self):
    assert utils.get_length('hello') == 5

  def test_with_dot(self):
    # 'a.b' counts as ['a.', 'b'] => 2 graphemes for the display
    assert utils.get_length('a.b') == 2

  def test_leading_dot_excluded(self):
    # leading dot is not counted (negative lookahead in the regex)
    assert utils.get_length('.abc') == 3

  def test_empty(self):
    assert utils.get_length('') == 0

  def test_exactly_twelve(self):
    assert utils.get_length('abcdefghijkl') == 12


class TestTruncate:
  def test_short_unchanged(self):
    assert utils.truncate('hi', 100) == 'hi'

  def test_long_truncated(self):
    out = utils.truncate('a long sentence here that should be cut', 15)
    assert len(out) <= 15
    assert out.endswith('...')


class TestFitText:
  def test_short_passthrough(self):
    assert utils.fit_text('short') == 'short'

  def test_long_shortened(self):
    out = utils.fit_text('a very long song title that exceeds twelve chars')
    assert utils.get_length(out) <= 12


class TestShortenText:
  def test_under_limit(self):
    assert utils.shorten_text('court') == 'court'

  def test_strips_french_articles(self):
    out = utils.shorten_text('le concert de la nuit')
    assert ' le ' not in f' {out} '.lower()

  def test_terminates_for_pathological(self):
    # Cannot shorten further (every word <= 2 chars), should not loop forever
    text = 'a b c d e f g h i j k l m'
    out = utils.shorten_text(text)
    assert isinstance(out, str)


class TestSplitText:
  def test_with_dots(self):
    parts = utils.split_text('a.bc')
    assert parts == ['a.', 'b', 'c']
