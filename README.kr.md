# Seed Randomness Experiment

prompt 맨 앞에 random seed를 넣으면 LLM 응답이 실제로 더 랜덤해지는가? 4가지 처치 조건을 비교한 통제 실험이다.

## 핵심 결과

다양성을 만들어내는 메커니즘 사이에는 뚜렷한 효과의 사다리가 존재한다.

```
plain  <  seed prefix  <  자연어 지시("랜덤하게")  <  delusionist-mini pollution
```

prompt 맨 앞의 random seed는 응답을 의미 있게 더 랜덤하게 만들지 못한다. 표면적인 어휘 변주는 다소 늘어나지만, 모델은 결국 동일한 입장과 동일한 핵심 근거 구조로 수렴한다. 본질적인 분포 이동을 원한다면 자연어 지시나 의미 단위의 노이즈 주입이 필요하다.

![다양성 사다리](report/figures/fig1_diversity_ladder.png)

상세 내용은 [report/한국어_md.ver.md](report/한국어_md.ver.md) (만연체 보고서) 또는 [report/한국어_논문.ver.md](report/한국어_논문.ver.md) (학술 논문체)에서 확인할 수 있다.

## 보고서

| 언어 | 만연체 | 논문체 |
|---|---|---|
| 한국어 | [한국어_md.ver.md](report/한국어_md.ver.md) | [한국어_논문.ver.md](report/한국어_논문.ver.md) |
| 영어 | [Eng_md.ver.md](report/Eng_md.ver.md) | [Eng_pap.ver.md](report/Eng_pap.ver.md) |

## 프로젝트 구조

```
seed-randomness-experiment/
├── README.md                       # 영어 README (이 파일)
├── README.kr.md                    # 한국어 README
├── report/
│   ├── 한국어_md.ver.md             # 한국어 만연체 보고서
│   ├── 한국어_논문.ver.md            # 한국어 논문체 보고서
│   ├── Eng_md.ver.md                # 영어 만연체 보고서
│   ├── Eng_pap.ver.md               # 영어 논문체 보고서
│   └── figures/                    # 7장 figure (PNG)
├── output/generation/              # 실험 원본 출력 30개 콜 (Exp 1·2 × A/B/C × 5콜)
├── eval_payload.txt                # 평가자 3명에게 보낸 데이터 패키지
├── eval_gemini_3_1_pro.txt         # gemini-3.1-pro-preview 평가 응답
├── eval_codex.txt                  # codex (gpt-5.4) 평가 응답
├── queue.json                      # 실험 prompt 큐 (run_batches.py 입력)
├── fill_queue.py                   # 6-layer prompt 빌더
├── run_batches.py                  # 병렬 gemini CLI 배치 실행기
├── analyze.py                      # Exp 1·2 정량 분석
├── analyze_d.py                    # D군(delusionist) 분석
├── generate_figures.py             # 7장 figure 생성
└── build_eval_payload.py           # 평가자 데이터 패키지 빌더
```

## 실험 재현

요구사항:
- Python 3.12+ (matplotlib 3.8+)
- gemini CLI (`gemini-3-flash-preview`, `gemini-3.1-pro-preview` 모델 접근 가능)
- codex CLI (선택, 평가자 3명 중 하나로 사용)

```bash
# 1. queue.json 생성 (30 task = 5콜 × 3군 × 2실험)
python3 fill_queue.py

# 2. 배치 실행 — 결과는 output/generation/ 에 저장
python3 run_batches.py

# 3. 정량 분석
python3 analyze.py

# 4. 평가자 패키지 생성 후 gemini-3.1-pro-preview / codex로 평가 의뢰
python3 build_eval_payload.py

# 5. 7장 figure 재생성
python3 generate_figures.py
```

D군(delusionist-mini)은 별도 파이프라인으로 실행한다:
- `/Users/jakesmacair/프로젝트 파일/delusionist_factory_personal/mini/`
- request.json 작성 → `python3 run_mini.py`
- 결과는 mini/output/ 에 저장

## 실험 메서드 요약

| 항목 | 내용 |
|---|---|
| 모델 | gemini-3-flash-preview |
| 작업 1 | 한국어 과일 5개 출력 |
| 작업 2 | "초등학교 스마트폰 전면 금지" 찬반 논설문 (입장 + 근거 3개) |
| 처치 | A: seed prefix / B: plain / C: 자연어 지시 / D: delusionist-mini pollution |
| 콜 수 | 군당 5콜 × 작업 2개 = 10 (D군은 별도 파이프라인) |
| 평가자 | gemini-3.1-pro-preview, codex (gpt-5.4), claude opus 4.7 — 1~5 척도 4 metric |

## 라이센스

연구 및 교육 목적으로 자유롭게 이용할 수 있다. 인용 시에는 출처 표기를 권장한다.
