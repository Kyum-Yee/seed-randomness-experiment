"""실험 1·2 정량 분석.

실험 1 metrics (per group):
- 5콜 합집합에서의 유니크 과일 수 (다양성)
- 평균 pairwise Jaccard 유사도 (낮을수록 콜 간 다름)
- 5콜 모두 등장한 과일 수 (보수성 — fruit dominance)

실험 2 metrics (per group):
- 입장 분포 (찬/반)
- 정합성: 입장과 근거 3개 모두 같은 방향인가 (목측 후 binary)
- 콜 간 근거 토픽 다양성 (n-gram overlap이 아닌 키워드 추출 후 Jaccard)
"""
from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path
from statistics import mean

OUT = Path(__file__).resolve().parent / "output" / "generation"


def parse_fruits(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fruits: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\.\s*(.+?)\s*$", line)
        if m:
            fruits.append(m.group(1).strip())
    return fruits[:5]


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def analyze_exp1() -> dict:
    groups = {"A": [], "B": [], "C": []}
    for g in groups:
        for i in range(1, 6):
            fr = parse_fruits(OUT / f"exp1_{g.lower()}{i}.md")
            groups[g].append(fr)

    result: dict = {}
    for g, runs in groups.items():
        all_fruits = [f for run in runs for f in run]
        unique = set(all_fruits)
        # 평균 pairwise Jaccard
        sets = [set(r) for r in runs]
        pairs = list(combinations(sets, 2))
        avg_jac = mean(jaccard(a, b) for a, b in pairs) if pairs else 0.0
        # 5콜 모두 등장
        common = set.intersection(*sets) if sets else set()
        # 빈도
        freq: dict[str, int] = {}
        for f in all_fruits:
            freq[f] = freq.get(f, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])

        result[g] = {
            "runs": runs,
            "unique_count": len(unique),
            "unique_set": sorted(unique),
            "avg_pairwise_jaccard": round(avg_jac, 3),
            "common_5runs": sorted(common),
            "freq_top": top,
        }
    return result


def parse_exp2(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    stance = ""
    reasons: list[str] = []
    m = re.search(r"입장\s*:\s*(찬성|반대)", text)
    if m:
        stance = m.group(1)
    for i in (1, 2, 3):
        rm = re.search(rf"근거{i}\s*:\s*(.+?)(?=\n근거{i+1}\s*:|\Z)", text, re.DOTALL)
        if rm:
            reasons.append(rm.group(1).strip())
    return {"stance": stance, "reasons": reasons}


def analyze_exp2() -> dict:
    groups: dict[str, list[dict]] = {"A": [], "B": [], "C": []}
    for g in groups:
        for i in range(1, 6):
            d = parse_exp2(OUT / f"exp2_{g.lower()}{i}.md")
            groups[g].append(d)

    result: dict = {}
    for g, runs in groups.items():
        stances = [r["stance"] for r in runs]
        reason_counts = [len(r["reasons"]) for r in runs]
        stance_dist = {"찬성": stances.count("찬성"), "반대": stances.count("반대"), "결측": stances.count("")}
        result[g] = {
            "runs": runs,
            "stance_dist": stance_dist,
            "reasons_per_run": reason_counts,
            "all_3_reasons": all(c == 3 for c in reason_counts),
        }
    return result


def kw_set(text: str) -> set[str]:
    """단순 키워드 셋 — 한글 2-4자 명사 후보 + 공백 분리."""
    words = re.findall(r"[가-힣]{2,4}", text)
    return set(words)


def reason_similarity(group_runs: list[dict]) -> float:
    """한 군 내 5콜의 근거 3개씩(=15 reasons)을 모은 후 콜 간 평균 키워드 Jaccard."""
    sets = []
    for r in group_runs:
        merged = " ".join(r["reasons"])
        sets.append(kw_set(merged))
    pairs = list(combinations(sets, 2))
    if not pairs:
        return 0.0
    return mean(jaccard(a, b) for a, b in pairs)


def main() -> None:
    print("=" * 70)
    print("실험 1: gemini-3-flash-preview, '과일 5개 출력' (5콜 × 3군)")
    print("=" * 70)
    r1 = analyze_exp1()
    for g in ("A", "B", "C"):
        d = r1[g]
        label = {"A": "A (seed 10자리)", "B": "B (plain)", "C": "C ('랜덤하게' 지시)"}[g]
        print(f"\n[{label}]")
        for i, run in enumerate(d["runs"], 1):
            print(f"  콜{i}: {run}")
        print(f"  → 유니크 과일 수: {d['unique_count']} ({d['unique_set']})")
        print(f"  → 평균 pairwise Jaccard: {d['avg_pairwise_jaccard']}  (1=동일, 0=완전다름)")
        print(f"  → 5콜 모두 등장: {d['common_5runs']}")
        print(f"  → 빈도: {d['freq_top'][:8]}")

    print("\n" + "=" * 70)
    print("실험 2: gemini-3-flash-preview, '찬반+근거3' (5콜 × 3군)")
    print("논점: 초등학교에서 스마트폰 사용을 전면 금지해야 한다")
    print("=" * 70)
    r2 = analyze_exp2()
    for g in ("A", "B", "C"):
        d = r2[g]
        label = {"A": "A (seed 10자리)", "B": "B (plain)", "C": "C ('창의적이게' 지시)"}[g]
        print(f"\n[{label}]")
        print(f"  입장 분포: {d['stance_dist']}")
        print(f"  근거 개수/콜: {d['reasons_per_run']}  (모두 3개? {d['all_3_reasons']})")
        sim = reason_similarity(d["runs"])
        print(f"  근거 키워드 콜간 평균 Jaccard: {round(sim, 3)}")


if __name__ == "__main__":
    main()
