"""공통 함수: 시간, HTTP, 숫자 변환, 등급 산정."""
from __future__ import annotations
import os, re, time
from datetime import datetime, timedelta, timezone
import requests

KST = timezone(timedelta(hours=9))
PY = 3.305785  # ㎡ → 평


def now_kst() -> datetime:
    return datetime.now(KST)


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def http_get(url: str, params=None, timeout=30, tries=3):
    last = None
    for i in range(tries):
        try:
            return requests.get(url, params=params, timeout=timeout,
                                headers={"User-Agent": "Mozilla/5.0 (logistics-board)"})
        except requests.RequestException as e:  # 네트워크 일시 오류 재시도
            last = e
            time.sleep(2 * (i + 1))
    raise last


def to_num(v):
    """숫자·'1,234,000원' 같은 문자열 모두 처리."""
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^0-9.]", "", str(v))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def sido_of(addr: str, regions: list[str]) -> str:
    a = addr or ""
    full = {"경기도": "경기", "인천광역시": "인천", "서울특별시": "서울", "충청북도": "충북",
            "충청남도": "충남", "세종특별자치시": "세종", "대전광역시": "대전"}
    for k, v in full.items():
        if a.startswith(k):
            return v
    for r in regions:
        if a.startswith(r):
            return r
    return ""


def grade(rec: dict, c: dict) -> dict:
    """A/B/C/D 등급과 근거.
    A: 냉동/저온 + 위치 1·2순위 + 찾는 금액대(price_range) 안 + 규모 적정
    B: 금액대 안 + (위치 1~3순위 또는 냉동)
    C: 금액대 밖 또는 기타 창고·물류
    D: 금액 미상 — 확인 필요"""
    text = " ".join(str(rec.get(k) or "") for k in ("title", "usage", "memo"))
    addr = rec.get("addr") or rec.get("title") or ""
    cold = rec.get("cold")
    if cold is None:
        cold = any(k in text for k in c["keywords"]["cold"])
    loc = 9
    for tier, names in sorted(c["location_tiers"].items()):
        if any(n in addr for n in names):
            loc = int(tier)
            break
    price = rec.get("price_eok")
    ptier = 9
    if price is not None:
        for tier, lim in sorted(c["price_tiers"].items()):
            if price <= lim:
                ptier = int(tier)
                break
    area = rec.get("area_py")
    area_ok = area is None or c["area_pyeong"]["min"] <= area <= c["area_pyeong"]["max"]

    reasons = [("냉동·저온" if cold else "상온/미확인"),
               (f"위치 {loc}순위" if loc < 9 else "위치 순위 밖"),
               (f"금액 {ptier}순위" if ptier < 9 else ("금액 미상" if price is None else "금액 초과"))]
    if area is not None:
        reasons.append("규모 적정" if area_ok else "규모 범위 밖")

    pr = c.get("price_range") or {}
    in_range = price is not None and pr.get("min", 0) <= price <= pr.get("max", 1e9)
    if price is not None and not in_range:
        reasons.append("금액대 밖")
    if cold and loc <= 2 and in_range and area_ok:
        g = "A"
    elif in_range and (loc <= 3 or cold):
        g = "B"
    elif price is None and rec.get("src") not in ("뉴스",):
        g = "D"
    else:
        g = "C"
    rec["cold"] = bool(cold)
    rec["loc_tier"] = loc if loc < 9 else None
    rec["price_tier"] = ptier if ptier < 9 else None
    rec["grade"] = g
    rec["why"] = " · ".join(reasons)
    return rec


def is_news_target(text: str, c: dict) -> bool:
    k = c["keywords"]
    return (is_target(text, c) and any(w in text for w in k.get("news_deal", []))
            and not any(w in text for w in k.get("news_exclude", [])))


def is_target(text: str, c: dict) -> bool:
    if not any(k in text for k in c["keywords"]["include"]):
        return False
    return not any(k in text for k in c["keywords"]["exclude"])
