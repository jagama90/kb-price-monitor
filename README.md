# KB 시세 모니터

KB부동산의 평형별 **매매 일반가**를 수집해 Supabase에 누적하고, 정적 웹페이지에서 비교하는 개인용 모니터입니다.

기본 갱신 범위는 강남구·서초구·송파구·성동구입니다. 웹에서는 자치구 복수 선택, 공급평수 숫자 범위, 단지 세대수, 예산 필터, 모든 컬럼 정렬, CSV 저장, 비슷한 평형 모아보기를 지원합니다.

## 데이터 원칙

- 한 행은 `(complex_id, area_id)` 한 쌍입니다.
- 가격은 `/land-complex/complex/mpriByType`의 해당 평형 `매매일반거래가`만 사용합니다.
- 단지 최저·최고가, AI시세, 실거래가로 일반가를 대신하지 않습니다.
- 자료가 없으면 `general_price_manwon=null`로 유지합니다.
- `collected_at`은 조회시각이며 `price_date`와 다릅니다.
- ‘15억원 이하’는 가격 비교일 뿐 대출 승인 또는 한도를 보장하지 않습니다.

## 구성

- `dist/`: GitHub Pages용 정적 웹페이지
- `scripts/collect_seoul.py`: KB 단지·평형 전체 새 수집
- `scripts/sync_supabase.py`: 검증된 스냅샷을 원자적으로 DB에 게시
- `supabase/migrations/`: Supabase 스키마와 RLS 정책
- `.github/workflows/weekly-refresh.yml`: 토요일 오전 10시(KST) 자동 갱신

DB는 현재 화면용 `kb_current_prices`와 실제 가격이 바뀐 행만 남기는 `kb_price_history`를 분리합니다. 새 수집이 완전하지 않거나 행 수 검증에 실패하면 기존 게시 자료는 그대로 보존됩니다.

## 최초 설정

1. Supabase SQL Editor에서 `supabase/migrations/202609050001_kb_price_schema.sql`을 실행합니다.
2. GitHub Actions secrets에 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`를 등록합니다.
3. `dist/config.js`의 `supabaseAnonKey`에 Supabase publishable key를 넣습니다.
4. GitHub Pages의 Source를 `GitHub Actions`로 설정합니다.

## 로컬 검증

```sh
node --check dist/app.js
node scripts/test_price_core.cjs dist/seoul_types.json
python3 -m unittest discover -s scripts -p 'test_*.py'
```

## 수동 갱신

```sh
export KB_TARGET_DISTRICTS='강남구,서초구,송파구,성동구'
python3 scripts/collect_seoul.py
python3 scripts/sync_supabase.py data/seoul_types.json
```

KB 응답에서 401·403·429 또는 구조 변경이 감지되면 수집은 중단되고 마지막 검증된 DB 자료를 유지합니다.

