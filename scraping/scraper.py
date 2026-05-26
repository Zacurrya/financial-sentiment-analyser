"""
Modified by: Zakariya Yusuf, BSc
May 2026
"""

import re
from typing import Iterable, List

import requests
from bs4 import BeautifulSoup
"""Scraper helpers for extracting transcript data from Motley Fool pages.

This module focuses on robustness and clarity: use logging instead of prints,
limit traversal to the article container, and collect paragraph text only
until the next section header when extracting the transcript body.
"""

import re
import logging
from typing import Iterable, List

import requests
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv

from constants import SPEAKER_PREFIX_RE, WHITESPACE_RE
from models import ExtractTranscriptResult

load_dotenv()

logger = logging.getLogger(__name__)

TRANSCRIPT_FOOTER_LINES = 13


def scrape_site(url: str) -> BeautifulSoup:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def clean_transcript(transcript: Iterable[str]) -> List[str]:
    if not transcript:
        return []

    lines = list(transcript)
    if len(lines) > TRANSCRIPT_FOOTER_LINES:
        lines = lines[:-TRANSCRIPT_FOOTER_LINES]

    cleaned: List[str] = []
    for line in lines:
        text = line.replace("\\n", " ").replace("\n", " ").replace("\r", " ")
        text = WHITESPACE_RE.sub(" ", text).strip()
        text = SPEAKER_PREFIX_RE.sub("", text)
        if text:
            cleaned.append(text)

    return cleaned

def extract_summary(article):
    # summary
    summary = ""
    summary_node = article.find("h2", id="summary")
    if summary_node:
        # prefer immediate sibling paragraph, fallback to next paragraph
        summary_para = summary_node.find_next_sibling("p") or summary_node.find_next("p")
        if summary_para:
            summary = summary_para.get_text(strip=True)
        else: logger.debug("extract_transcript: summary paragraph not found")
    else: logger.debug("extract_transcript: summary header not found")
    return summary

def _extract_transcript_body(article):
    # transcript body: collect <p> elements after the transcript header until next <h2>
    transcript_lines: List[str] = []
    if article:
        transcript_header = article.find("h2", id="full-conference-call-transcript")
        if transcript_header:
            for sibling in transcript_header.find_next_siblings():
                if getattr(sibling, "name", None) == "h2":
                    break
                if getattr(sibling, "name", None) == "p":
                    transcript_lines.append(sibling.get_text(strip=True))
        else:
            logger.debug("extract_transcript: transcript header not found")

    return " ".join(clean_transcript(transcript_lines))

def scrape_article(soup: BeautifulSoup) -> ExtractTranscriptResult:
    article = soup.find(id="article-body-transcript")
    if not article: logger.warning("extract_transcript: article container not found")


    def safe_section_list(container: Tag | None, section_id: str) -> List[str]:
        if not container: 
            logger.debug("safe_section_list: missing container for %s", section_id)
            return []
        
        header = container.find("h2", id=section_id)
        if not header: 
            logger.debug("safe_section_list: header '%s' not found", section_id)
            return []
        
        list_root = header.find_next("ul")
        if not list_root:
            logger.debug("safe_section_list: list for '%s' not found", section_id)
            return []
        return [li.get_text(strip=True) for li in list_root.find_all("li")]

    summary = extract_summary(article)

    takeaways = safe_section_list(article, "takeaways")
    
    risks = safe_section_list(article, "risks")
    
    transcript = _extract_transcript_body(article)

    return ExtractTranscriptResult(
        summary=summary,
        takeaways=takeaways,
        risks=risks,
        transcript=transcript,
    )


def extract_transcript(soup: BeautifulSoup) -> ExtractTranscriptResult:
    """Compatibility wrapper: accept a soup and return ExtractTranscriptResult.

    Existing callers expect `extract_transcript(soup)` to return the model.
    """
    return scrape_article(soup)
