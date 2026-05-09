"""1회용 queue.json 생성 스크립트.

실험 설계
---------
- 실험 1 (exp1): gemini-3-flash-preview, "과일 5개 출력"
    A군 (a1-a5): seed 10자리 + 랜덤용도 명시
    B군 (b1-b5): plain (seed 없음)
    C군 (c1-c5): plain + "랜덤하게 골라라"
- 실험 2 (exp2): gemini-3-flash-preview, "찬반 + 근거 3개 논설문"
    논점: "초등학교에서 스마트폰 사용을 전면 금지해야 한다"
    A군 (a1-a5): seed 10자리 + 랜덤용도 명시
    B군 (b1-b5): plain
    C군 (c1-c5): plain + "창의적이게 써라"

각 군 내 5콜은 출력 변동성 측정용. seed 군은 매 콜 다른 seed.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent

random.seed(20260509)
SEEDS_EXP1 = [str(random.randint(10**9, 10**10 - 1)) for _ in range(5)]
SEEDS_EXP2 = [str(random.randint(10**9, 10**10 - 1)) for _ in range(5)]

FLASH = "gemini-3-flash-preview"

EXP2_TOPIC = "초등학교에서 스마트폰 사용을 전면 금지해야 한다"


def exp1_prompt(group: str, seed: str | None) -> str:
    """실험 1 — 과일 5개 출력."""
    seed_block = ""
    if group == "A":
        seed_block = (
            f"[랜덤 시드 — 응답의 랜덤성과 창의성을 위한 용도]\n"
            f"seed: {seed}\n\n"
        )
    extra = ""
    if group == "C":
        extra = "응답을 랜덤하게 골라라. 같은 질문에도 매번 다른 다섯 개를 골라야 한다.\n"

    return f"""{seed_block}[Tone]
Persona: 간결하고 즉답형.
Roleplay: 사용자의 단순 요청에 군더더기 없이 답하는 어시스턴트.

[Task]
한국어로 과일 이름 5개를 골라 번호 매김 리스트로 출력하라.
{extra}출력 형식 (반드시 이 형식만, 다른 텍스트 일체 금지):
1. <과일1>
2. <과일2>
3. <과일3>
4. <과일4>
5. <과일5>

[Core Capability]
1. 과일 5개를 떠올려라.
2. 위 형식 그대로 출력하라.

[Constraints]
- 인사말, 설명, component 블록, --- 구분자 일체 금지.
- 오직 1.~5. 다섯 줄만 출력.
"""


def exp2_prompt(group: str, seed: str | None) -> str:
    """실험 2 — 찬반 + 근거 3개 논설문."""
    seed_block = ""
    if group == "A":
        seed_block = (
            f"[랜덤 시드 — 응답의 랜덤성과 창의성을 위한 용도]\n"
            f"seed: {seed}\n\n"
        )
    creativity = ""
    if group == "C":
        creativity = "창의적이게 써라. 흔한 논거 말고 의외의 관점을 제시하라.\n"

    return f"""{seed_block}[Tone]
Persona: 단호하고 논리적인 칼럼니스트.
Roleplay: 짧은 사설을 쓴다.

[Task]
다음 논점에 대해 찬성 또는 반대 입장 하나를 분명히 정하고, 그 입장을 뒷받침하는 근거 3개를 제시하라.
논점: "{EXP2_TOPIC}"

{creativity}출력 형식 (반드시 이 형식만):
입장: <찬성 또는 반대>
근거1: <한 문장 요약 — 한 문단 부연>
근거2: <한 문장 요약 — 한 문단 부연>
근거3: <한 문장 요약 — 한 문단 부연>

[Core Capability]
1. 입장을 명확히 한 줄로 선언하라.
2. 근거 3개를 서로 겹치지 않게 작성하라.
3. 각 근거는 "요약 한 문장 → 부연 한 문단" 구조.

[Constraints]
- 인사말, 메타 설명, component 블록, --- 구분자 일체 금지.
- 위 4줄(입장/근거1/근거2/근거3) 골격만 사용.
- 한국어로 작성.
"""


def build_tasks() -> list[dict]:
    tasks: list[dict] = []

    # 실험 1
    for i, seed in enumerate(SEEDS_EXP1, start=1):
        tasks.append({"id": f"exp1_a{i}", "model": FLASH, "prompt": exp1_prompt("A", seed)})
    for i in range(1, 6):
        tasks.append({"id": f"exp1_b{i}", "model": FLASH, "prompt": exp1_prompt("B", None)})
    for i in range(1, 6):
        tasks.append({"id": f"exp1_c{i}", "model": FLASH, "prompt": exp1_prompt("C", None)})

    # 실험 2
    for i, seed in enumerate(SEEDS_EXP2, start=1):
        tasks.append({"id": f"exp2_a{i}", "model": FLASH, "prompt": exp2_prompt("A", seed)})
    for i in range(1, 6):
        tasks.append({"id": f"exp2_b{i}", "model": FLASH, "prompt": exp2_prompt("B", None)})
    for i in range(1, 6):
        tasks.append({"id": f"exp2_c{i}", "model": FLASH, "prompt": exp2_prompt("C", None)})

    return tasks


def main() -> None:
    queue = {
        "stacks": [
            {
                "id": "generation",
                "status": "pending",
                "reference_files": [],
                "tasks": build_tasks(),
            }
        ]
    }
    out = BASE / "queue.json"
    out.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"queue.json 생성: {len(queue['stacks'][0]['tasks'])} task")
    print(f"  실험1 seeds: {SEEDS_EXP1}")
    print(f"  실험2 seeds: {SEEDS_EXP2}")


if __name__ == "__main__":
    main()
