"""
Modified by: Zakariya Yusuf, BSc
May 2026
"""

import re
from typing import Iterable, List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from constants import SPEAKER_PREFIX_RE

load_dotenv()

TRANSCRIPT_FOOTER_LINES = 13

def scrape_site(url: str) -> BeautifulSoup:
    page = requests.get(url, timeout=10)
    return BeautifulSoup(page.text, "html.parser")

def clean_transcript(transcript: Iterable[str]) -> List[str]:
    if not transcript:
        return []

    cleaned: List[str] = []
    for line in list(transcript)[:-TRANSCRIPT_FOOTER_LINES]:
        text = line.replace("\\n", " ").replace("\n", " ").replace("\r", " ")
        text = re.sub(r"\s+", " ", text).strip()
        text = SPEAKER_PREFIX_RE.sub("", text)
        if text:
            cleaned.append(text)

    return cleaned

def extract_transcript(soup: BeautifulSoup) -> dict:
    article = soup.find(id="article-body-transcript")
    if not article:
        print("[extract_transcript] Warning: article container not found.")

    def safe_section_list(container, section_id: str) -> List[str]:
        if not container:
            print(
                f"[extract_transcript] Warning: container missing for section '{section_id}'."
            )
            return []
        header = container.find("h2", id=section_id)
        if not header:
            print(f"[extract_transcript] Warning: section header '{section_id}' not found.")
            return []
        list_root = header.find_next("ul")
        if not list_root:
            print(f"[extract_transcript] Warning: list for section '{section_id}' not found.")
            return []
        return [li.get_text(strip=True) for li in list_root.find_all("li")]

    summary = ""
    summary_node = soup.find("h2", id="summary")
    if summary_node:
        summary_para = summary_node.find_next("p")
        if summary_para:
            summary = summary_para.get_text(strip=True)
        else:
            print("[extract_transcript] Warning: summary paragraph not found.")
    else:
        print("[extract_transcript] Warning: summary header not found.")

    takeaways = safe_section_list(article, "takeaways")
    risks = safe_section_list(article, "risks")

    transcript_lines: List[str] = []
    if article:
        transcript_header = article.find("h2", id="full-conference-call-transcript")
        if transcript_header:
            transcript_lines = [
                p.get_text(strip=True)
                for p in transcript_header.find_all_next("p")
            ]
        else:
            print("[extract_transcript] Warning: transcript header not found.")

    transcript = " ".join(clean_transcript(transcript_lines))

    return {
        "summary": summary,
        "takeaways": takeaways,
        "risks": risks,
        "transcript": transcript,
    }
    