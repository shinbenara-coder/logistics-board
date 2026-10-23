"""수집 실행: 온비드 + 뉴스 + 수동 등록 → site/data/listings.json"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from common import env, grade, now_kst, sido_of
import onbid, news

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data" / "listings.json"


def main():
    c = yaml.safe_load((ROOT / "collector" / "criteria.yaml").read_text(encoding="utf-8"))
    manual = yaml.safe_load((ROOT / "collector" / "manual.yaml").read_text(encoding="utf-8")) or []
    prev = {}
    if OUT.exists():
        try:
            prev = {r["id"]: r for r in json.loads(OUT.read_text(encoding="utf-8")).get("items", [])}
        except Exception:  # noqa: BLE001
            prev = {}
    now = now_kst().strftime("%Y-%m-%d %H:%M")
    status, items = [], []

    key = env("ONBID_API_KEY")
    if key:
        rows, errs = onbid.fetch(key)
        recs = onbid.to_records(rows, c)
        status.append({"name": "온비드 공매", "ok": not errs or bool(recs), "count": len(recs),
                       "message": "; ".join(errs[:3])})
        items += recs
    else:
        status.append({"name": "온비드 공매", "ok": False, "count": 0, "message": "ONBID_API_KEY 미설정"})

    recs, errs = news.fetch(c)
    status.append({"name": "뉴스", "ok": not errs or bool(recs), "count": len(recs), "message": "; ".join(errs[:3])})
    items += recs

    for m in manual:
        m = dict(m)
        m.setdefault("src", "수동 등록")
        m["sido"] = sido_of(m.get("addr", ""), c["regions"])
        m["date"] = str(m.get("date", ""))
        m["deadline"] = str(m.get("deadline", "") or "")
        items.append(m)
    status.append({"name": "수동 등록(경매·중개)", "ok": True, "count": len(manual), "message": ""})

    for r in items:
        grade(r, c)
        old = prev.get(r["id"])
        r["first_seen"] = (old or {}).get("first_seen") or now
        r["is_new"] = old is None and bool(prev)
        if old and old.get("price_eok") and r.get("price_eok") and old["price_eok"] != r["price_eok"]:
            r["price_change"] = f"{old['price_eok']}→{r['price_eok']}억"
    gorder = {"A": 0, "B": 1, "C": 2, "D": 3}
    items.sort(key=lambda r: (gorder.get(r["grade"], 9), r.get("deadline") or "9999", r["title"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": now, "criteria": c, "status": status, "items": items},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"완료: {len(items)}건 (신규 {sum(r['is_new'] for r in items)})")


if __name__ == "__main__":
    main()
