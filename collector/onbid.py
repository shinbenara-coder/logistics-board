"""온비드 부동산 물건목록(공공데이터포털 OpenAPI)에서 창고·물류 물건만 수집.

API: 한국자산관리공사_차세대 온비드 부동산 물건목록 조회서비스
     GET https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2
신탁공매(기타일반재산)·압류·국유·공유재산을 모두 받아, 제목·용도에 창고/물류/냉동 키워드가 있는 것만 남긴다.
"""
from __future__ import annotations
import time
from common import http_get, to_num, sido_of, is_target, PY, now_kst

URL = "https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2"
DETAIL = "https://www.onbid.co.kr/op/cltrpbancinf/cltrdtl/CltrDtlController/mvmnCltrDtl.do"
LIST_PAGE = "https://www.onbid.co.kr/"
PRPT_DIVS = ("0007", "0005", "0010", "0002", "0008")  # 기타일반(신탁 등)·압류·국유·공유 등


def _items(js):
    if isinstance(js, dict) and isinstance(js.get("response"), dict):
        js = js["response"]
    body = (js or {}).get("body") or {}
    items = body.get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    return [i for i in items if isinstance(i, dict)]


def fetch(key: str, log=print):
    rows, errs = [], []
    for div in PRPT_DIVS:
        for pvct in ("N", "Y"):
            page = 1
            while page <= 60:
                p = {"serviceKey": key, "pageNo": page, "numOfRows": 500, "resultType": "json",
                     "prptDivCd": div, "pvctTrgtYn": pvct}
                try:
                    r = http_get(URL, params=p, timeout=40)
                    t = r.text.strip()
                    if r.status_code != 200 or t.startswith("<"):
                        errs.append(f"{div}/{pvct} p{page}: {r.status_code} {t[:120]}")
                        break
                    it = _items(r.json())
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{div}/{pvct} p{page}: {e}")
                    break
                if not it:
                    break
                for x in it:
                    x["_pvct"] = pvct
                rows += it
                if len(it) < 500:
                    break
                page += 1
                time.sleep(0.2)
        log(f"  온비드 {div}: 누적 {len(rows)}행")
    return rows, errs


def _d(v):
    s = "".join(ch for ch in str(v or "") if ch.isdigit())
    if len(s) < 8 or s.startswith(("2999", "9999")):
        return ""
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" + (f" {s[8:10]}:{s[10:12]}" if len(s) >= 12 else "")


def to_records(rows, c):
    now = now_kst().strftime("%Y-%m-%d %H:%M")
    groups = {}
    for x in rows:
        if x.get("cltrMngNo"):
            groups.setdefault(str(x["cltrMngNo"]), []).append(x)
    out = []
    for no, rs in groups.items():
        live = [r for r in rs if _d(r.get("cltrBidEndDt")) >= now[:len(_d(r.get("cltrBidEndDt")))] and _d(r.get("cltrBidEndDt"))]
        pv = any(r.get("_pvct") == "Y" or str(r.get("pvctTrgtYn", "")).upper() == "Y" for r in rs)
        if not live and not pv:
            continue
        cur = sorted(live or rs, key=lambda r: _d(r.get("cltrBidBgngDt")) or "9")[0]
        title = (cur.get("onbidCltrNm") or "").strip()
        usage = " > ".join(filter(None, [cur.get("cltrUsgMclsCtgrNm"), cur.get("cltrUsgSclsCtgrNm")]))
        if "임대" in (cur.get("dspsMthodNm") or ""):
            continue
        if not is_target(f"{title} {usage}", c):
            continue
        addr = (cur.get("zadrNm") or cur.get("cltrAdr") or
                " ".join(filter(None, [cur.get("lctnSdnm"), cur.get("lctnSggnm"), cur.get("lctnEmdNm")])))
        sido = sido_of(addr, c["regions"]) or (cur.get("lctnSdnm") or "")[:2]
        if sido not in c["regions"]:
            continue
        apsl = to_num(cur.get("apslEvlAmt"))
        minp = None
        for k in ("lowstBidPrcIndctCont", "lowstBidPrc", "lowstBidAmt", "minBidPrc"):
            minp = to_num(cur.get(k))
            if minp:
                break
        ref = minp or apsl
        pr = c.get("price_range") or {}
        if ref and not (pr.get("min", 0) * 1e8 <= ref <= pr.get("max", 1e9) * 1e8):
            continue  # 찾는 금액대 밖
        bld, land = to_num(cur.get("bldSqms")), to_num(cur.get("landSqms"))
        keys = ("onbidCltrno", "onbidPbancNo", "pbctNo", "pbctCdtnNo")
        url = LIST_PAGE
        if all(cur.get(k) for k in keys):
            url = DETAIL + "?cltrScrnGrpCd=0001&cltrPrptDivCd=" + str(cur.get("prptDivCd") or "") + "&" + \
                "&".join(f"{k}={cur.get(k)}" for k in keys)
        out.append({
            "id": f"onbid:{no}", "src": "온비드 공매", "title": title or addr, "addr": addr, "sido": sido,
            "usage": usage, "org": cur.get("orgNm") or "", "prpt": cur.get("prptDivNm") or "",
            "area_py": round(bld / PY) if bld else None, "land_py": round(land / PY) if land else None,
            "appraisal_eok": round(apsl / 1e8, 1) if apsl else None,
            "price_eok": round(ref / 1e8, 1) if ref else None,
            "price_note": ("최저입찰가" + (f"(감정가의 {minp / apsl * 100:.0f}%)" if apsl else "")) if minp else ("감정가 기준" if apsl else ""),
            "fails": int(to_num(cur.get("usbdNft")) or 0),
            "status": (f"수의계약 가능(최종입찰 {_d(cur.get('cltrBidEndDt'))[:7]})" if _d(cur.get('cltrBidEndDt')) else "수의계약 가능")
                      if (pv and not live) else (cur.get("pbctStatNm") or "진행"),
            "deadline": _d(cur.get("cltrBidEndDt")), "url": url,
        })
    return out
