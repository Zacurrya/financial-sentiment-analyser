import re

BASE_EARNING_CALL_PATH = 'https://www.fool.com/earnings-call-transcripts'
GOOGLE_CUSTOM_SEARCH_API_KEY='AIzaSyCh615leF_PrwV_Rexzp6Nv4RkZ0fc2b0Q'
SPEAKER_PREFIX_RE = re.compile(r"^[A-Za-z .'-]{2,60}:\s*")
QUARTER_YEAR_PATTERN = re.compile(
	# matches patterns like '-q1-2026', '/q1-2026', '_q1_2026' occurring anywhere in the path
	r"[/-_]?q(?P<quarter>[1-4])[-_ ]?(?P<year>\d{4})",
	re.IGNORECASE,
)