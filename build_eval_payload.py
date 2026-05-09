"""평가자 3명에게 보낼 통일된 prompt + 실험 2 A/B 데이터 묶음 생성."""
from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "output" / "generation"

EVAL_PROMPT_HEADER = """당신은 LLM 응답의 다양성/정합성을 정량 평가하는 분석가다.

[배경]
한 연구자가 다음을 검증 중이다: "프롬프트 맨 앞에 10자리 랜덤 시드를 넣고 '랜덤성과 창의성을 위한 용도'라고 알려주면, LLM 응답이 더 랜덤(다양)해지는가?"

실험 설계:
- 모델: gemini-3-flash-preview (동일)
- 논점: "초등학교에서 스마트폰 사용을 전면 금지해야 한다" — 찬/반 입장 + 근거 3개를 쓰라고 지시
- A군 (5콜): 프롬프트 맨 앞에 매번 다른 10자리 seed + "랜덤성과 창의성을 위한 용도" 명시
- B군 (5콜): seed 없음. 다른 프롬프트 텍스트는 A와 동일.
- 변인 외 모든 조건 통제됨.

[당신의 작업]
A군과 B군 결과(아래)를 읽고 두 항목을 산출하라.

(1) 정성 보고서 (300~500자):
   - 두 군의 입장 분포, 근거 토픽 분포, 글의 결을 비교
   - seed가 실제로 결과를 더 random하게 만들었는지 결론
   - A vs B 차이의 크기 (작다/중간/크다)와 근거

(2) 정량 metric (1~5 정수 척도, 각 군 별):
   metric 정의 (모든 평가자가 동일 정의 사용):
   - 군내_유사성: 한 군 내 5콜 사이의 근거가 얼마나 비슷한가 (1=완전 다름, 5=거의 같음)
   - 정합성_입장: 입장 한 줄과 근거 3개의 방향성 일치 (1=상충, 5=완벽일치)
   - 정합성_주제: 근거가 논점("스마트폰 금지")에 충실 (1=논점이탈, 5=완벽고수)
   - 다양성: 5콜의 근거 토픽이 얼마나 폭넓게 분포 (1=같은 토픽 반복, 5=폭넓게 분포)

   추가로 한 점수만:
   - 군간_유사성: A군 vs B군 결과가 전체적으로 얼마나 닮았나 (1=완전 다름, 5=거의 같음)

[출력 형식 — 반드시 이 형식만]
## 정성 보고서
<300~500자 한 문단>

## 정량 metric
| metric | A군 | B군 |
|---|---|---|
| 군내_유사성 | _/5 | _/5 |
| 정합성_입장 | _/5 | _/5 |
| 정합성_주제 | _/5 | _/5 |
| 다양성 | _/5 | _/5 |

군간_유사성 (단일점수): _/5

## 결론
seed가 응답을 더 random하게 만들었는가? **예 / 아니오 / 미미함** 중 하나 + 한 문장 사유.
"""


def fmt_run(label: str, path: Path) -> str:
    body = path.read_text(encoding="utf-8").strip()
    return f"### {label}\n{body}\n"


def build() -> str:
    parts = [EVAL_PROMPT_HEADER, "\n---\n# 데이터\n\n## A군 (seed + 랜덤성/창의성 문구)\n"]
    for i in range(1, 6):
        parts.append(fmt_run(f"A-콜{i}", OUT / f"exp2_a{i}.md"))
    parts.append("\n## B군 (plain)\n")
    for i in range(1, 6):
        parts.append(fmt_run(f"B-콜{i}", OUT / f"exp2_b{i}.md"))
    return "\n".join(parts)


if __name__ == "__main__":
    payload = build()
    out = BASE / "eval_payload.txt"
    out.write_text(payload, encoding="utf-8")
    print(f"eval_payload.txt: {len(payload)}자")
