"""D군 (delusionist-mini) 결과 정량 분석 — A/B/C와 비교 가능하도록.

Exp 1: 26개 과일을 5×5=25로 청킹 (잉여 1 버림) → Jaccard 측정
Exp 2: 6개 의견을 5로 청킹 → 입장 분포 + 키워드 Jaccard
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
from statistics import mean
import re

EXP1 = Path("/Users/jakesmacair/프로젝트 파일/delusionist_factory_personal/mini/output/ideas_2026-05-09_14-39.md")
EXP2 = Path("/Users/jakesmacair/프로젝트 파일/delusionist_factory_personal/mini/output/ideas_2026-05-09_14-41.md")


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def kw_set(text: str) -> set[str]:
    return set(re.findall(r"[가-힣]{2,4}", text))


def analyze_exp1_d() -> None:
    fruits = [ln.strip() for ln in EXP1.read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"[D군 Exp1] 총 {len(fruits)}개 / 유니크 {len(set(fruits))}개")
    # 5×5 청킹 (앞 25개)
    chunks = [fruits[i:i + 5] for i in range(0, 25, 5)]
    print("  콜 분할 (5×5):")
    for i, c in enumerate(chunks, 1):
        print(f"    콜{i}: {c}")
    sets = [set(c) for c in chunks]
    pairs = list(combinations(sets, 2))
    avg_jac = mean(jaccard(a, b) for a, b in pairs)
    common = set.intersection(*sets) if sets else set()
    print(f"  유니크 (25개 풀): {len(set(fruits[:25]))}")
    print(f"  콜간 평균 Jaccard: {round(avg_jac, 3)}")
    print(f"  5콜 모두 등장: {sorted(common) or '없음'}")
    # 통념 5대 과일 빈도
    common5 = {"사과", "바나나", "포도", "딸기", "수박"}
    cnt = sum(1 for f in fruits if f in common5)
    print(f"  통념 5대 과일(사과/바나나/포도/딸기/수박) 등장: {cnt}회")


def analyze_exp2_d() -> None:
    text = EXP2.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    print(f"\n[D군 Exp2] 총 {len(lines)}개 의견")
    # 입장 추출
    stances = []
    for ln in lines:
        m = re.match(r"^(찬성|반대)\s*[:：]", ln)
        stances.append(m.group(1) if m else "")
    print(f"  입장 분포: 찬성={stances.count('찬성')} 반대={stances.count('반대')} 결측={stances.count('')}")
    # 앞 5개로 청킹 (콜로 간주)
    use = lines[:5]
    sets = [kw_set(ln) for ln in use]
    pairs = list(combinations(sets, 2))
    avg_jac = mean(jaccard(a, b) for a, b in pairs) if pairs else 0.0
    print(f"  앞 5개 의견 키워드 콜간 평균 Jaccard: {round(avg_jac, 3)}")
    # 통념 3축 키워드 등장
    cliche = ["집중력", "사이버 불링", "대면", "사회성"]
    cnt = sum(1 for ln in lines for kw in cliche if kw in ln)
    print(f"  통념 3축 키워드(집중력·사이버 불링·대면·사회성) 등장 횟수: {cnt}")


if __name__ == "__main__":
    analyze_exp1_d()
    analyze_exp2_d()
