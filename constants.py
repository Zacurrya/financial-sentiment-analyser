import re

BASE_EARNING_CALL_PATH = 'https://www.fool.com/earnings-call-transcripts'
SPEAKER_PREFIX_RE = re.compile(r"^[A-Za-z .'-]{2,60}:\s*")
URL_QUARTER_YEAR_PATTERN = re.compile(
	# matches patterns like '-q1-2026', '/q1-2026', '_q1_2026' occurring anywhere in the path
	r"[/-_]?q(?P<quarter>[1-4])[-_ ]?(?P<year>\d{4})",
	re.IGNORECASE,
)
TICKER_BOUNDARY_PATTERN_FORMAT = r"(?:^|[/_\-])({})(?:$|[/_\-])"

# Common regexes used across the project
NON_ALNUM_RE = re.compile(r"[^a-z0-9]")
DATE_PATH_RE = re.compile(r"/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/")
WHITESPACE_RE = re.compile(r"\s+")
