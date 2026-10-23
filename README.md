# 냉동창고 매물 트래킹

대한제당 자가 냉동창고 매입 기준(기획팀)에 맞는 물류창고 매물을 매일 **08시·14시·18시** 자동으로 모아 한 페이지로 보여주는 사이트입니다. 서버 없이 GitHub(무료)만으로 돌아갑니다.

| 출처 | 방식 | 비고 |
|---|---|---|
| 온비드 공매 | 공공데이터포털 OpenAPI (자동) | 신탁공매·압류·국공유재산 중 창고·물류·냉동 물건, 경기·인천·서울·충청 |
| 뉴스 | 구글 뉴스 RSS (자동, 키 불필요) | "냉동창고 매각", "물류센터 공매" 등 검색어 기사 |
| 법원경매·중개·채권 | `collector/manual.yaml` (수동) | 법원경매는 공식 API가 없어 자동 수집 불가 → 발견 시 한 블록 추가 |

등급: **A 적합**(냉동·저온 + 경부/중부 + 350억 이하 + 3천~1.2만평) / **B 검토** / **C 참고** / **D 정보 부족**. 기준 숫자는 `collector/criteria.yaml`에서 바꿉니다.

---

## 처음 설정 (약 15분, 한 번만)

### 1. 공공데이터포털 서비스키 (무료)
1. <https://www.data.go.kr> 회원가입·로그인
2. `한국자산관리공사_차세대 온비드 부동산 물건목록 조회서비스` 검색 → **활용신청** (용도: 내부 매물 조회)
3. 마이페이지 → 개발계정 → 해당 서비스 → **일반 인증키(Decoding)** 복사

### 2. GitHub 저장소 만들기
1. <https://github.com> 가입·로그인 → 오른쪽 위 **+ → New repository**
2. 이름 `logistics-board`, **Private 권장**(Pages는 Private이면 유료 플랜 필요 → 무료로 쓰려면 Public. 매물 정보에 내부 메모가 있으니 `manual.yaml`의 memo는 공개돼도 되는 수준으로만 작성)
3. 이 폴더의 파일 전체를 업로드(저장소 화면의 **uploading an existing file**에 끌어다 놓기 → Commit)
   - `.github` 폴더는 숨김 폴더라 안 보일 수 있습니다. 업로드 후 `.github/workflows/update.yml`이 없으면 **Add file → Create new file**로 같은 이름·내용을 만들어 주세요.

### 3. 서비스키 등록
**Settings → Secrets and variables → Actions → New repository secret** → Name `ONBID_API_KEY`, 값 = 1단계 키

### 4. 웹사이트 켜기
**Settings → Pages → Source: GitHub Actions**

### 5. 첫 실행
**Actions → 매물 수집·배포 → Run workflow** → 5~10분 뒤 `https://<아이디>.github.io/logistics-board/`

---

## 매물 수동 추가 (경매·중개)
GitHub에서 `collector/manual.yaml` 열기 → 연필(편집) → 맨 아래에 블록 추가 → Commit. 몇 분 뒤 사이트에 반영됩니다.
```yaml
- id: m-새이름            # 겹치지 않는 영문 id
  src: 법원경매            # 법원경매 / 중개 / 채권·PF 등
  title: 물건명
  addr: 경기도 OO시 ...
  cold: true               # 냉동·저온이면 true
  area_py: 6000            # 연면적(평)
  price_eok: 280           # 금액(억원)
  price_note: 최저가(감정의 50%)
  status: 입찰예정
  deadline: 2026-11-30
  url: https://...
  memo: 한 줄 메모
  date: 2026-10-23
```

## 화면 기능
- 등급 카드(전체·A·B·C·신규) 클릭 필터, 탭(온비드 공매·법원경매·중개·채권·뉴스), 위치 순위·냉동만·신규만 필터, 검색, 정렬(등급·마감·금액·최근)
- **NEW**: 직전 갱신 이후 새로 잡힌 매물 / 금액이 바뀌면 `가격변동` 표시 / 마감 D-day
- 필터 상태가 주소(#)에 남아 즐겨찾기·공유 가능

## 한계
- 법원경매·오프마켓 매물은 자동 수집이 안 됩니다(공식 API 없음). 모닝브리핑에서 발견되는 경매 물건은 manual.yaml 블록으로 정리해 드립니다.
- 온비드 물건 제목에 '창고·물류·냉동' 등 키워드가 없으면 빠질 수 있습니다(키워드는 criteria.yaml에서 추가).
- 냉동 톤수는 공매·뉴스 자료에 거의 없어 연면적·냉동 여부로 대신 판단합니다.
