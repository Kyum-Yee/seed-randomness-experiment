"""실험 결과 시각화 — figures/*.png 생성.

생성 figure:
1. fig1_diversity_ladder.png — 다양성 사다리 (Exp1·Exp2 통합)
2. fig2_exp1_metrics.png    — Exp 1 (과일) 4군 metric 비교
3. fig3_exp1_fruit_pool.png — Exp 1 과일 풀 분포 (각 군의 유니크 과일)
4. fig4_exp2_stance.png     — Exp 2 입장 분포 (찬/반)
5. fig5_exp2_jaccard.png    — Exp 2 키워드 Jaccard 4군 비교
6. fig6_evaluator_scores.png — Exp 2 평가자 3명 metric (A vs B)
7. fig7_diversity_summary.png — 종합 요약 표 (4군×2실험)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

# 한글 폰트
mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["figure.dpi"] = 110

BASE = Path(__file__).resolve().parent
FIG = BASE / "figures"
FIG.mkdir(exist_ok=True)

# ─── 데이터 ────────────────────────────────────────────────────────
GROUPS = ["A\n(seed)", "B\n(plain)", "C\n(랜덤하게)", "D\n(delusionist)"]
COLORS = {
    "A": "#5B8FF9",
    "B": "#9CA3AF",
    "C": "#F59E0B",
    "D": "#EF4444",
}
COL_LIST = [COLORS["A"], COLORS["B"], COLORS["C"], COLORS["D"]]

# Exp 1 결과
EXP1_UNIQUE = [11, 7, 15, 20]
EXP1_JACCARD = [0.420, 0.767, 0.144, 0.068]
EXP1_DIVERSITY = [1 - j for j in EXP1_JACCARD]  # 1 - Jaccard
EXP1_CLICHE = [25, 25, 13, 0]  # 통념 5대 과일 등장 횟수 (25콜 중)

# Exp 2 결과
EXP2_STANCE_FOR = [5, 5, 3, 4]
EXP2_STANCE_AGAINST = [0, 0, 2, 2]
EXP2_JACCARD = [0.107, 0.114, 0.060, 0.038]
EXP2_DIVERSITY = [1 - j for j in EXP2_JACCARD]
EXP2_CLICHE_RATE = [95, 98, 50, 0]  # 통념 3축 등장률 (%)

# 평가자 점수 — A vs B (3 평가자 × 4 metric)
EVALUATORS = ["gemini-3.1-pro", "codex (gpt-5.4)", "claude opus 4.7"]
METRICS = ["군내_유사성", "정합성_입장", "정합성_주제", "다양성"]
SCORES_A = np.array([
    [4, 5, 5, 2],  # gemini
    [4, 5, 5, 3],  # codex
    [4, 5, 5, 2],  # claude
])
SCORES_B = np.array([
    [5, 5, 5, 1],
    [5, 5, 5, 2],
    [5, 5, 5, 1],
])


# ─── Figure 1: Diversity Ladder ────────────────────────────────────
def fig_diversity_ladder() -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(4)
    width = 0.38
    bars1 = ax.bar(x - width / 2, EXP1_DIVERSITY, width, label="Exp 1 (과일) — (1 - Jaccard)",
                   color=[c for c in COL_LIST], edgecolor="black", linewidth=0.6)
    bars2 = ax.bar(x + width / 2, EXP2_DIVERSITY, width, label="Exp 2 (논설문) — (1 - Jaccard)",
                   color=[c for c in COL_LIST], edgecolor="black", linewidth=0.6, hatch="//")
    for bs, vals in ((bars1, EXP1_DIVERSITY), (bars2, EXP2_DIVERSITY)):
        for b, v in zip(bs, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}",
                    ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(GROUPS, fontsize=10)
    ax.set_ylabel("다양성 점수 (1 − Jaccard, 높을수록 다양)", fontsize=11)
    ax.set_title("Figure 1. 다양성 사다리 — 4군 × 2실험", fontsize=13, weight="bold")
    ax.set_ylim(0, 1.05)
    ax.axhline(y=0.5, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig1_diversity_ladder.png", bbox_inches="tight")
    plt.close()


# ─── Figure 2: Exp 1 Metrics ───────────────────────────────────────
def fig_exp1_metrics() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))

    # 유니크 수
    ax = axes[0]
    ax.bar(GROUPS, EXP1_UNIQUE, color=COL_LIST, edgecolor="black", linewidth=0.6)
    for i, v in enumerate(EXP1_UNIQUE):
        ax.text(i, v + 0.3, str(v), ha="center", fontsize=10)
    ax.set_ylabel("유니크 과일 수")
    ax.set_title("(a) 유니크 과일 다양성")
    ax.set_ylim(0, 25)
    ax.grid(axis="y", alpha=0.3)

    # Jaccard
    ax = axes[1]
    ax.bar(GROUPS, EXP1_JACCARD, color=COL_LIST, edgecolor="black", linewidth=0.6)
    for i, v in enumerate(EXP1_JACCARD):
        ax.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)
    ax.set_ylabel("콜간 평균 Jaccard ↓ 낮을수록 다양")
    ax.set_title("(b) 5콜 사이 유사도")
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", alpha=0.3)

    # 통념 5대 과일 등장
    ax = axes[2]
    ax.bar(GROUPS, EXP1_CLICHE, color=COL_LIST, edgecolor="black", linewidth=0.6)
    for i, v in enumerate(EXP1_CLICHE):
        ax.text(i, v + 0.5, str(v), ha="center", fontsize=10)
    ax.set_ylabel("통념 5대 과일 등장 횟수 (25콜 중)")
    ax.set_title("(c) 통념 회피")
    ax.set_ylim(0, 28)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Figure 2. Exp 1 (과일 5개 출력) — 4군 metric 비교", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(FIG / "fig2_exp1_metrics.png", bbox_inches="tight")
    plt.close()


# ─── Figure 3: Exp 1 Fruit Pool ─────────────────────────────────────
def fig_exp1_fruit_pool() -> None:
    a_set = ["사과", "포도", "딸기", "바나나", "복숭아", "오렌지", "수박", "참외", "배", "감", "귤"]
    b_set = ["사과", "바나나", "포도", "딸기", "수박", "오렌지", "배"]
    c_set = ["참외", "자두", "멜론", "감", "밤", "배", "귤", "망고", "복숭아", "한라봉", "사과", "바나나", "포도", "딸기", "수박"]
    d_set = ["핑거라임", "으름", "블러드오렌지", "불수감", "자보티카바", "아떼모야", "블랙사포테", "포멜로", "노니", "미라클프루트",
             "살락", "레드커런트", "용안", "슈가애플", "왁스애플", "스타애플", "구즈베리", "마르멜로", "깔라만시", "람부탄"]

    all_fruits = list(dict.fromkeys(a_set + b_set + c_set + d_set))
    matrix = np.zeros((4, len(all_fruits)), dtype=int)
    for i, group in enumerate([a_set, b_set, c_set, d_set]):
        for f in group:
            j = all_fruits.index(f)
            matrix[i, j] = 1

    fig, ax = plt.subplots(figsize=(15, 3.6))
    ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(range(4))
    ax.set_yticklabels(["A (seed)", "B (plain)", "C (랜덤하게)", "D (delusionist)"], fontsize=10)
    ax.set_xticks(range(len(all_fruits)))
    ax.set_xticklabels(all_fruits, rotation=70, ha="right", fontsize=8)
    ax.set_title("Figure 3. Exp 1 — 4군의 과일 풀 분포 (■=등장)", fontsize=12, weight="bold")

    # Add cell separators
    ax.set_xticks(np.arange(-0.5, len(all_fruits), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 4, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.5)

    plt.tight_layout()
    plt.savefig(FIG / "fig3_exp1_fruit_pool.png", bbox_inches="tight")
    plt.close()


# ─── Figure 4: Exp 2 Stance ─────────────────────────────────────────
def fig_exp2_stance() -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(4)
    width = 0.55
    ax.bar(x, EXP2_STANCE_FOR, width, label="찬성", color="#5B8FF9", edgecolor="black", linewidth=0.6)
    ax.bar(x, EXP2_STANCE_AGAINST, width, bottom=EXP2_STANCE_FOR, label="반대",
           color="#EF4444", edgecolor="black", linewidth=0.6)
    for i in range(4):
        if EXP2_STANCE_FOR[i] > 0:
            ax.text(i, EXP2_STANCE_FOR[i] / 2, str(EXP2_STANCE_FOR[i]), ha="center", va="center",
                    fontsize=11, color="white", weight="bold")
        if EXP2_STANCE_AGAINST[i] > 0:
            ax.text(i, EXP2_STANCE_FOR[i] + EXP2_STANCE_AGAINST[i] / 2, str(EXP2_STANCE_AGAINST[i]),
                    ha="center", va="center", fontsize=11, color="white", weight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(GROUPS)
    ax.set_ylabel("콜 수 (총 5)")
    ax.set_title("Figure 4. Exp 2 — 4군의 입장 분포 (찬/반)", fontsize=12, weight="bold")
    ax.set_ylim(0, 6)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig4_exp2_stance.png", bbox_inches="tight")
    plt.close()


# ─── Figure 5: Exp 2 Jaccard + Cliche ───────────────────────────────
def fig_exp2_jaccard() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    ax.bar(GROUPS, EXP2_JACCARD, color=COL_LIST, edgecolor="black", linewidth=0.6)
    for i, v in enumerate(EXP2_JACCARD):
        ax.text(i, v + 0.003, f"{v:.3f}", ha="center", fontsize=10)
    ax.set_ylabel("키워드 콜간 평균 Jaccard ↓ 낮을수록 다양")
    ax.set_title("(a) 근거 키워드 유사도")
    ax.set_ylim(0, 0.15)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    ax.bar(GROUPS, EXP2_CLICHE_RATE, color=COL_LIST, edgecolor="black", linewidth=0.6)
    for i, v in enumerate(EXP2_CLICHE_RATE):
        ax.text(i, v + 1, f"{v}%", ha="center", fontsize=10)
    ax.set_ylabel("통념 3축 등장률 (%)")
    ax.set_title("(b) 통념 회피 — 집중력·사이버불링·사회성")
    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Figure 5. Exp 2 (논설문) — 다양성·통념 회피", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(FIG / "fig5_exp2_jaccard.png", bbox_inches="tight")
    plt.close()


# ─── Figure 6: Evaluator Scores ─────────────────────────────────────
def fig_evaluator_scores() -> None:
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.5), sharey=True)
    x = np.arange(3)
    width = 0.36

    for j, metric in enumerate(METRICS):
        ax = axes[j]
        a_vals = SCORES_A[:, j]
        b_vals = SCORES_B[:, j]
        ax.bar(x - width / 2, a_vals, width, label="A군", color=COLORS["A"], edgecolor="black", linewidth=0.6)
        ax.bar(x + width / 2, b_vals, width, label="B군", color=COLORS["B"], edgecolor="black", linewidth=0.6)
        for i in range(3):
            ax.text(i - width / 2, a_vals[i] + 0.05, str(a_vals[i]), ha="center", fontsize=9)
            ax.text(i + width / 2, b_vals[i] + 0.05, str(b_vals[i]), ha="center", fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels([e.split(" ")[0] for e in EVALUATORS], rotation=20, fontsize=9)
        ax.set_title(metric, fontsize=11)
        ax.set_ylim(0, 6)
        ax.set_yticks(range(0, 6))
        ax.grid(axis="y", alpha=0.3)
        if j == 0:
            ax.set_ylabel("점수 (1-5 척도)")
        if j == 3:
            ax.legend(loc="upper right", fontsize=9)

    fig.suptitle("Figure 6. Exp 2 — 평가자 3명 × 4 metric (A vs B군)", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(FIG / "fig6_evaluator_scores.png", bbox_inches="tight")
    plt.close()


# ─── Figure 7: Summary Heatmap ──────────────────────────────────────
def fig_summary_heatmap() -> None:
    metrics_label = [
        "Exp1 다양성\n(1−Jaccard)",
        "Exp1 유니크\n과일 수 (정규화)",
        "Exp1 통념회피\n(1−등장률)",
        "Exp2 다양성\n(1−Jaccard)",
        "Exp2 입장분기\n(반대/총)",
        "Exp2 통념회피\n(1−등장률)",
    ]
    data = np.array([
        EXP1_DIVERSITY,
        [u / 25 for u in EXP1_UNIQUE],
        [1 - c / 25 for c in EXP1_CLICHE],
        EXP2_DIVERSITY,
        [a / (a + f) if (a + f) else 0 for a, f in zip(EXP2_STANCE_AGAINST, EXP2_STANCE_FOR)],
        [1 - c / 100 for c in EXP2_CLICHE_RATE],
    ])

    fig, ax = plt.subplots(figsize=(8.5, 5))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(4))
    ax.set_xticklabels(GROUPS)
    ax.set_yticks(range(len(metrics_label)))
    ax.set_yticklabels(metrics_label, fontsize=9)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            color = "white" if data[i, j] < 0.4 else "black"
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", fontsize=10, color=color)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("정규화된 다양성 점수 (0 낮음, 1 높음)")
    ax.set_title("Figure 7. 종합 — 6개 metric × 4군 (모든 점수 0-1로 정규화)",
                 fontsize=12, weight="bold")
    plt.tight_layout()
    plt.savefig(FIG / "fig7_summary_heatmap.png", bbox_inches="tight")
    plt.close()


# ─── Run all ────────────────────────────────────────────────────────
def main() -> None:
    fig_diversity_ladder()
    fig_exp1_metrics()
    fig_exp1_fruit_pool()
    fig_exp2_stance()
    fig_exp2_jaccard()
    fig_evaluator_scores()
    fig_summary_heatmap()
    print(f"7 figures → {FIG}")
    for p in sorted(FIG.glob("*.png")):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
