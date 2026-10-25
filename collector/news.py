"""구글 뉴스 RSS로 냉동창고·물류센터 매각/공매/경매 기사 수집 (API 키 불필요)."""
from __future__ import annotations
import re, html
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET
from common import http_get, now_kst, is_news_target, sido_of

RSS = "https://news.google.com/rss/search?q={q}+when:{d}d&hl=ko&gl=KR&ceid=KR:ko"
REGION_WORDS = ["용인", "수원", "화성", "오산", "성남", "의왕", "광주", "이천", "하남", "음성", "진천", "여주",
                "안성", "평택", "충주", "김포", "인천", "부천", "시흥", "안산", "파주", "고양", "남양주", "양주",
                "천안", "아산", "청주", "세종", "대전", "경기"]


def fetch(c, log=print):
    out, errs, seen = [], [], set()
    for q in c["news_queries"]:
        try:
            r = http_get(RSS.format(q=quote(q), d=c.get("news_days", 45)), timeout=30)
            root = ET.fromstring(r.content)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{q}: {e}")
            continue
        n = 0
        for it in root.iter("item"):
            title = html.unescape(it.findtext("title") or "")
            src = it.findtext("source") or ""
            t = re.sub(r"\s+-\s+[^-]+$", "", title)  # '제목 - 언론사' 꼬리 제거
            key = re.sub(r"\W", "", t)[:40]
            if key in seen or not is_news_target(t, c):
                continue
            seen.add(key)
            short = "s:" + re.sub(r"\W", "", t)[:12]
            if short in seen:
                continue
            seen.add(short)
            try:
                dt = parsedate_to_datetime(it.findtext("pubDate")).astimezone(now_kst().tzinfo)
            except Exception:  # noqa: BLE001
                dt = now_kst()
            region = next((w for w in REGION_WORDS if w in t), "")
            out.append({"id": "news:" + key, "src": "뉴스", "title": t, "addr": region, "sido": "",
                        "org": src, "status": "보도", "date": dt.strftime("%Y-%m-%d"),
                        "url": it.findtext("link") or "", "query": q})
            n += 1
        log(f"  뉴스 '{q}': {n}건")
    return out, errs
