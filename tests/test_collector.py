import sys, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))
import onbid, news, common
C = yaml.safe_load((Path(__file__).resolve().parent.parent / "collector" / "criteria.yaml").read_text(encoding="utf-8"))

def test_onbid_filter():
    rows = [
        {"cltrMngNo": "1", "onbidCltrNm": "경기도 광주시 초월읍 냉동창고 및 부속토지", "cltrUsgMclsCtgrNm": "산업용건물",
         "cltrUsgSclsCtgrNm": "창고", "zadrNm": "경기도 광주시 초월읍 지월리 1", "apslEvlAmt": "50000000000",
         "lowstBidPrc": "30000000000", "bldSqms": "19834", "cltrBidBgngDt": "209901011000", "cltrBidEndDt": "209901021600",
         "pbctStatNm": "입찰진행중", "orgNm": "OO신탁", "_pvct": "N"},
        {"cltrMngNo": "2", "onbidCltrNm": "서울 아파트", "zadrNm": "서울특별시 강남구", "cltrBidEndDt": "209901021600", "_pvct": "N"},
        {"cltrMngNo": "3", "onbidCltrNm": "부산 냉동창고", "zadrNm": "부산광역시 사하구", "cltrBidEndDt": "209901021600", "_pvct": "N"},
    ]
    recs = onbid.to_records(rows, C)
    assert [r["id"] for r in recs] == ["onbid:1"]
    r = common.grade(recs[0], C)
    assert r["price_eok"] == 300.0 and r["area_py"] == 6000 and r["grade"] == "A", r

def test_grade_tiers():
    r = common.grade({"title": "창고", "addr": "경기도 김포시", "price_eok": 900, "src": "온비드 공매"}, C)
    assert r["grade"] == "C"
    r = common.grade({"title": "냉동창고", "addr": "경기도 이천시", "price_eok": 480, "area_py": 5897}, C)
    assert r["grade"] == "B"

def test_news_parse(monkeypatch):
    xml = """<rss><channel><item><title>&#51060;&#52380; &#45257;&#46041;&#52285;&#44256; &#47588;&#44033; &#52628;&#51652; - &#46377;&#49324;&#51060;&#53944;</title>
    <link>https://example.com/a</link><pubDate>Thu, 22 Oct 2026 01:00:00 GMT</pubDate><source>딜사이트</source></item>
    <item><title>서울 아파트 매각 - 언론</title><link>x</link><pubDate>Thu, 22 Oct 2026 01:00:00 GMT</pubDate></item></channel></rss>""".encode("utf-8")
    class R: content = xml
    monkeypatch.setattr(news, "http_get", lambda *a, **k: R())
    out, errs = news.fetch({**C, "news_queries": ["q"]}, log=lambda *a: None)
    assert len(out) == 1 and out[0]["addr"] == "이천" and out[0]["title"] == "이천 냉동창고 매각 추진"
