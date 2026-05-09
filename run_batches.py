"""
run_batches.py — gemini CLI 병렬 배치 처리 범용 템플릿 (stack 구조)

================================================================================
[전체 흐름 요약]
================================================================================

  queue.json
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │ run() 메인                                          │
  │  1. queue.json에서 status="pending" stack만 추출     │
  │  2. stack을 순차 실행 (stack1 → stack2 → ...)        │
  │  3. 각 stack 안의 task들은 ThreadPoolExecutor로     │
  │     동시 실행 (workers = min(len(tasks), STACK))    │
  │  4. 각 task → process_task() → call_gemini()        │
  │  5. 결과를 output/{stack_id}/{task_id}.md 로 저장    │
  │  6. stack의 모든 task 성공 시 status="done"          │
  │  7. (선택) stack별 결과를 result-*.md 로 합산        │
  │  8. cleanup_byproducts(): gemini가 남긴 부산물 삭제 │
  └─────────────────────────────────────────────────────┘

================================================================================
[설계 원칙 — 사전 계획(queue.json) ↔ 실행(run_batches.py) 분리]
================================================================================

  - queue.json 한 곳에서 stack/task별로 (id, model, prompt, reference_files)
    를 사전 계획한다.
  - run_batches.py 는 그 계획을 그대로 읽어 병렬 실행만 담당한다.
  - 모델은 task 단위로 바뀐다. 같은 stack 안에서 a는 pro, b는 flash 가능.
  - reference_files 는 stack 단위로 묶인다. 한 stack의 모든 task가 동일 자료를 참조.
  - gemini approval mode 는 "plan" 으로 고정 (yolo 모드 아님 — 코드 실행 차단).

================================================================================
[커스터마이징 포인트 — TODO 주석을 검색하면 한 번에 보임]
================================================================================

  1) queue.json       : stack/task/reference_files 를 채운다 (메인 작업)
  2) SYSTEM_INSTR     : 모든 task 공통으로 앞에 붙는 시스템 지시문
  3) DEFAULT_MODEL    : task에 model이 없을 때 쓸 기본값
  4) APPROVAL_MODE    : "plan"(안전, 기본) / "default" / "yolo"
  5) STACK            : stack당 동시 실행 task 상한 (안전 캡)
  6) STAGGER          : 인스턴스 시작 딜레이
  7) MERGE_OUTPUTS    : True/False — stack별 합산 파일 생성 여부

================================================================================
[사용법]
================================================================================

  # 1) 템플릿 폴더(이 파일이 들어있는 곳)를 새 프로젝트로 복제.
  cp -R "/Users/jakesmacair/프로젝트 파일/gemini for test" \\
        "/Users/jakesmacair/프로젝트 파일/<새-프로젝트-이름>"

  # 2) 새 폴더로 이동해서 queue.json만 채우고 실행.
  cd "/Users/jakesmacair/프로젝트 파일/<새-프로젝트-이름>"
  # queue.json 편집 (stack/task/reference_files/prompt 채움)
  python3 run_batches.py

  # BASE_DIR 은 __file__ 기준 자동 결정되므로 코드 수정 불필요.
  # 다시 실행하면 status="pending"인 stack만 재시도됨.
  # 출력 파일이 이미 있으면 자동 스킵 (process_task 내부에서 검사).
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ─── 경로 & 핵심 설정 ────────────────────────────────────────────────────────
#
# BASE_DIR 은 이 파일이 위치한 디렉터리로 자동 결정된다.
# → 템플릿을 다른 폴더로 복제(cp -R)해도 별도 수정 없이 그대로 동작.
# 한글/공백 경로라도 Path 객체는 그대로 처리한다 (subprocess shell=True 안 쓰면 안전).

BASE_DIR = Path(__file__).resolve().parent
QUEUE_PATH = BASE_DIR / "queue.json"
OUTPUT_DIR = BASE_DIR / "output"

# TODO[병렬]: 한 stack 안에서 동시에 띄울 gemini 인스턴스 최대 개수 (안전 캡).
#   - 실제 동시 실행 수 = min(len(stack.tasks), STACK).
#   - 너무 크면 lock 파일 충돌 / API rate limit / 메모리 압박.
#   - 7~10 권장. 실험할 때는 2~3으로 시작.
STACK = 7

# TODO[stagger]: 같은 stack 내 인스턴스 시작 간격(초).
#   - gemini는 ~/.gemini/ 아래에 lock 파일을 잠깐 잡으므로 동시에 시작하면
#     일부 인스턴스가 죽을 수 있다. 0초로 두고 문제 생기면 0.5~1.0으로.
STAGGER = 0.8

# TODO[재시도]: 빈 응답 시 최대 재시도 횟수. 0이면 한 번만 시도.
MAX_RETRY = 3

# TODO[모델]: queue.json의 task에 "model" 필드가 없을 때 사용할 기본 모델.
DEFAULT_MODEL = "gemini-3.1-pro-preview"

# TODO[승인 모드]: gemini CLI 의 --approval-mode 값.
#   "plan"    : (기본·안전) 계획만 — 코드 실행 차단, 파일 쓰기는 허용.
#   "default" : 위험한 동작 전에 확인 프롬프트 (자동화엔 부적합).
#   "yolo"    : 무조건 실행 — 자동화 가능하지만 시스템 명령 무방비. 사용 금지 권장.
APPROVAL_MODE = "auto_edit"

# TODO[합산]: True면 stack별로 output/{stack_id}/{task_id}.md 를 한 파일로 묶는다.
#   - 단순히 개별 파일만 필요하면 False로 두자.
MERGE_OUTPUTS = False
MERGE_PREFIX = "result"   # output/{stack_id}/result-2026-05-03-15-30.md 형식


# ─── 로깅: 30초마다 버퍼 flush ───────────────────────────────────────────────
#
# 병렬 처리 중 로그가 마구 섞이면 가독성이 떨어진다.
# 30초에 한 번씩 모아서 flush 하므로, 짧은 작업이라면 즉시 출력이 안 보일 수 있다.
# 즉시 보고 싶으면 LOG_FLUSH_INTERVAL을 1~2초로 줄일 것.

LOG_FLUSH_INTERVAL = 30


class BatchedHandler(logging.Handler):
    """버퍼에 쌓인 로그를 일정 간격마다 한꺼번에 flush. 변경 없으면 출력 생략."""

    def __init__(self, targets: list[logging.Handler], interval: float = LOG_FLUSH_INTERVAL) -> None:
        super().__init__()
        self._targets = targets
        self._interval = interval
        self._buffer: list[logging.LogRecord] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._flusher, daemon=True)
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        with self._lock:
            self._buffer.append(record)

    def _flusher(self) -> None:
        while not self._stop.wait(self._interval):
            self._flush()

    def _flush(self) -> None:
        with self._lock:
            records, self._buffer = self._buffer, []
        if not records:
            return
        for record in records:
            for handler in self._targets:
                if record.levelno >= handler.level:
                    handler.emit(record)
        for handler in self._targets:
            handler.flush()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._flush()
        super().close()


_file_handler = logging.FileHandler(BASE_DIR / "run_batches.log", encoding="utf-8")
_stream_handler = logging.StreamHandler()
_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_file_handler.setFormatter(_fmt)
_stream_handler.setFormatter(_fmt)

_batched = BatchedHandler(targets=[_file_handler, _stream_handler])

root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(_batched)

logger = logging.getLogger(__name__)


# ─── 시스템 지시문 (gemini가 따라야 할 역할/형식) ────────────────────────────
#
# TODO[SYSTEM_INSTR]: 여기를 작업 성격에 맞게 갈아끼우는 게 핵심이다.
# 아래는 "어떤 작업이든 작동하는" 최소 골격. 실제로는 다음 항목을 채워라:
#   1. 너는 무엇이다 (역할 정의)
#   2. 절대 금지 (코드 실행, 추가 파일 생성 등 — 리소스 보호)
#   3. 출력 형식 (마크다운? JSON? 자유서술?)
#   4. 출력 경로 규칙 (파일 1개만 / 경로 외 문자 금지)

SYSTEM_INSTR = """\
너는 배치 처리 에이전트다.
아래 지시를 정확히 따르고, 추가 질문 없이 즉시 실행한다.

[절대 금지 — 리소스 보호]
- 코드 작성·실행 금지. Python, shell 등 일체의 스크립트를 생성·실행하지 않는다.
- [출력 경로]에 명시된 파일 1개 외 어떠한 파일도 생성·수정·삭제하지 않는다.
- 외부 명령(터미널, 시스템 호출 등) 실행 금지.

[지시]
- [참조 파일]이 명시되어 있다면 모든 경로의 파일을 먼저 읽어 컨텍스트로 활용하라.
- [작업 지시]에 따라 결과를 생성하라.
- 결과는 [출력 형식] 규칙에 따라 [출력 경로] 파일에 저장하라.

[출력 형식 — 기본값]
- [작업 지시]에 별도 형식 요구가 없으면 아래 component 블록 형식으로 출력하라.
- 마크다운(.md) 파일.
- 메타 텍스트("알겠습니다", "이제 시작합니다" 등) 출력 금지.
- 결과만 깔끔히 출력.

  component1: (첫 번째 항목 내용)
  ---
  component2: (두 번째 항목 내용)
  ---
  component3: (세 번째 항목 내용)
  ---
  ...

규칙:
- 각 component는 한 줄로 시작 (component번호: 내용).
- component 사이의 구분은 반드시 `---` 단독 줄.
  (사유: component 내용이 글·시·인용문 등 빈 줄을 포함하는 장문일 수 있으므로,
   빈 줄로는 경계 식별 불가. `---` 한 줄을 명확한 구분자로 고정.)
- 내용이 길면 여러 줄·여러 단락으로 이어 써도 되며, 본문 안에 빈 줄도 허용된다.
- 마지막 component 뒤에도 `---` 단독 줄을 1번 더 붙인다 (파서 종결 표식).
- component 개수는 작업 성격에 맞게 자율 판단 (강제 개수 없음).
- [작업 지시]에 다른 형식이 명시되어 있다면 그것을 우선한다.
"""


# ─── 참조 파일 경로 정규화 ───────────────────────────────────────────────────
#
# 절대경로면 그대로, 상대경로면 BASE_DIR 기준으로 해석.
# 존재하지 않는 파일은 경고만 찍고 그대로 전달 (gemini가 스스로 처리하도록).

def resolve_reference_paths(paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for p in paths:
        path = Path(p)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        if not path.exists():
            logger.warning(f"  [refs] 존재하지 않는 참조 파일: {path}")
        resolved.append(path)
    return resolved


# ─── 프롬프트 빌더 ───────────────────────────────────────────────────────────
#
# 골격: SYSTEM_INSTR(공통) + [참조 파일] + task["prompt"](id별) + 출력경로 지시
# stack의 reference_files 와 task의 prompt 를 조합해서 한 프롬프트로 만든다.

def build_prompt(task: dict, reference_files: list[Path], output_path: Path) -> str:
    task_id = task["id"]
    task_prompt = task.get("prompt", "")

    if reference_files:
        ref_lines = "\n".join(f"- {p}" for p in reference_files)
        ref_block = f"""
[참조 파일 — 절대경로]
아래 파일들을 먼저 읽어 본문 작업 컨텍스트로 사용하라.
{ref_lines}
"""
    else:
        ref_block = ""

    return f"""{SYSTEM_INSTR}

[담당 task]
id: {task_id}
{ref_block}
[작업 지시]
{task_prompt}

[출력 경로]
아래 경로에 결과 파일을 저장하라 (오케스트레이터가 수집한다):
{output_path}

파일명은 task id 그대로. 확장자 .md. 경로 외 다른 문자 포함 금지.
"""


# ─── gemini CLI 호출 ─────────────────────────────────────────────────────────
#
# 모델은 task별로 다르므로 인자로 받는다. approval mode는 전역 고정.
#
#   --approval-mode plan : 코드 실행 등 위험 동작을 차단하고 계획만 세우게 함.
#                          파일 읽기·쓰기는 허용되므로 참조파일 읽기·결과 저장 가능.
#   -m <model>            : queue.json의 task["model"] (없으면 DEFAULT_MODEL)
#   stdin=DEVNULL         : 인터랙티브 입력 차단. 자동화에 필수.

def call_gemini(prompt: str, model: str) -> str:
    try:
        result = subprocess.run(
            ["gemini", "--approval-mode", APPROVAL_MODE, "-m", model, "-p", prompt],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            logger.error(f"gemini 에러 (model={model}, returncode={result.returncode}): {result.stderr[:500]}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"gemini 타임아웃 (model={model})")
        return ""
    except Exception as e:
        logger.error(f"gemini 호출 실패 (model={model}): {e}")
        return ""


# ─── task 1개 처리 ───────────────────────────────────────────────────────────
#
# 동작 순서:
#   1. output/{stack_id}/{task_id}.md 가 이미 있으면 스킵 (재실행 안전)
#   2. STAGGER 만큼 대기 (lock 충돌 방지)
#   3. gemini 호출 → 빈 응답이면 MAX_RETRY 까지 재시도
#   4. gemini가 직접 파일을 썼는지 검사 → 없으면 stdout을 폴백 저장

def process_task(
    task: dict,
    stack_dir: Path,
    reference_files: list[Path],
    stagger_idx: int = 0,
) -> bool:
    task_id = task["id"]
    model = task.get("model") or DEFAULT_MODEL
    output_path = stack_dir / f"{task_id}.md"

    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info(f"  [{task_id}] 스킵 — 출력 파일 이미 존재")
        return True

    if stagger_idx > 0 and STAGGER > 0:
        delay = stagger_idx * STAGGER
        logger.info(f"  [{task_id}] stagger 대기 {delay:.1f}초")
        time.sleep(delay)

    for attempt in range(MAX_RETRY + 1):
        logger.info(f"  [{task_id}] 처리 시작 (model={model}, 시도 {attempt}/{MAX_RETRY})")
        start = time.time()

        prompt = build_prompt(task, reference_files, output_path)
        response = call_gemini(prompt, model)
        elapsed = time.time() - start

        # gemini가 직접 파일을 저장한 경우
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"  [{task_id}] 완료 (gemini 직접 저장, {elapsed:.1f}초)")
            return True

        # gemini가 파일을 안 썼지만 stdout에 응답이 있으면 폴백 저장
        if response:
            stack_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response, encoding="utf-8")
            logger.info(f"  [{task_id}] 완료 (Python 폴백 저장, {elapsed:.1f}초, {len(response)}자)")
            return True

        logger.warning(f"  [{task_id}] 빈 응답 ({elapsed:.1f}초)")
        if attempt < MAX_RETRY:
            logger.info(f"  [{task_id}] 재시도 {attempt + 1}/{MAX_RETRY}")

    logger.error(f"  [{task_id}] 최대 재시도 초과, 실패")
    return False


# ─── stack 1개 처리 ──────────────────────────────────────────────────────────
#
# stack의 모든 task를 ThreadPoolExecutor로 병렬 실행.
# workers = min(len(tasks), STACK) — STACK 캡으로 폭주 방지.

def process_stack(stack: dict) -> tuple[list[str], list[str]]:
    stack_id = stack["id"]
    tasks = stack.get("tasks", [])
    raw_refs = stack.get("reference_files", [])
    reference_files = resolve_reference_paths(raw_refs)
    stack_dir = OUTPUT_DIR / stack_id
    stack_dir.mkdir(parents=True, exist_ok=True)

    workers = min(len(tasks), STACK)
    task_ids = [t["id"] for t in tasks]
    logger.info(
        f"[stack {stack_id}] task {task_ids} — {workers}개 병렬 / 참조파일 {len(reference_files)}개"
    )

    succeeded: list[str] = []
    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(process_task, task, stack_dir, reference_files, i): task["id"]
            for i, task in enumerate(tasks)
        }
        for future in as_completed(future_map):
            task_id = future_map[future]
            try:
                ok = future.result()
                (succeeded if ok else failed).append(task_id)
            except Exception as e:
                logger.error(f"  [{task_id}] Future 에러: {e}")
                failed.append(task_id)

    return succeeded, failed


# ─── 결과 합산 (stack 단위) ──────────────────────────────────────────────────
#
# MERGE_OUTPUTS=True 일 때만 사용. stack 안의 개별 task 결과를 한 파일로 묶는다.
# 묶음 파일에는 HTML 주석 마커가 들어가서 다음 실행 때 같은 파일을 확장 가능.

_TASK_MARKER_RE = re.compile(
    r"<!-- TASK:([^\s]+) START -->\n(.*?)<!-- TASK:\1 END -->\n?",
    re.DOTALL,
)


def _wrap_chunk(task_id: str, content: str) -> str:
    if not content.endswith("\n"):
        content += "\n"
    return f"<!-- TASK:{task_id} START -->\n{content}<!-- TASK:{task_id} END -->\n"


def _parse_chunks(content: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _TASK_MARKER_RE.finditer(content)}


def _find_extendable_file(stack_dir: Path, new_ids: set[str]) -> Path | None:
    """가장 최근 result-*.md 가 마커 보유 + 새 id와 겹침 없으면 그 경로 반환."""
    candidates = sorted(
        stack_dir.glob(f"{MERGE_PREFIX}-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    latest = candidates[0]
    try:
        existing = _parse_chunks(latest.read_text(encoding="utf-8"))
    except OSError:
        return None
    if not existing:
        return None
    overlap = new_ids & existing.keys()
    if overlap:
        logger.warning(f"  [merge:{stack_dir.name}] 최근 파일에 중복 id {sorted(overlap)} — 새 파일 생성")
        return None
    return latest


def merge_stack_outputs(stack_id: str, succeeded: list[str]) -> Path | None:
    if not MERGE_OUTPUTS:
        logger.info(f"  [merge:{stack_id}] MERGE_OUTPUTS=False — 스킵")
        return None
    if not succeeded:
        logger.info(f"  [merge:{stack_id}] 성공한 task 없음 — 스킵")
        return None

    stack_dir = OUTPUT_DIR / stack_id
    new_chunks: dict[str, str] = {}
    for task_id in sorted(succeeded):
        path = stack_dir / f"{task_id}.md"
        if path.exists() and path.stat().st_size > 0:
            new_chunks[task_id] = path.read_text(encoding="utf-8")

    if not new_chunks:
        logger.warning(f"  [merge:{stack_id}] 합산할 파일 없음")
        return None

    extend_target = _find_extendable_file(stack_dir, set(new_chunks))
    if extend_target is not None:
        existing = _parse_chunks(extend_target.read_text(encoding="utf-8"))
        merged = {**existing, **new_chunks}
        out_path = extend_target
        action = f"기존 파일 확장 ({len(existing)} → {len(merged)} task)"
    else:
        merged = dict(new_chunks)
        now = datetime.now()
        out_path = stack_dir / (
            f"{MERGE_PREFIX}-{now.year}-{now.month}-{now.day}-{now.hour:02d}-{now.minute:02d}.md"
        )
        action = f"새 파일 생성 ({len(merged)} task)"

    body = "".join(_wrap_chunk(tid, merged[tid]) for tid in sorted(merged))
    out_path.write_text(body, encoding="utf-8")

    # 합산했으면 개별 임시 파일은 지운다 (중복 방지).
    for task_id in new_chunks:
        try:
            (stack_dir / f"{task_id}.md").unlink()
        except OSError as e:
            logger.warning(f"  [merge:{stack_id}] 임시 파일 삭제 실패: {task_id}.md — {e}")

    logger.info(f"  [merge:{stack_id}] {action} → {out_path.relative_to(OUTPUT_DIR)}")
    return out_path


# ─── queue.json 상태 갱신 ────────────────────────────────────────────────────
#
# stack의 모든 task가 성공해야 stack을 done으로 처리.
# 일부만 성공한 경우 stack은 pending 유지 → 다음 실행 때 재시도.
# 단, 개별 task의 출력 파일은 남아있으므로 process_task가 자동 스킵한다.

def update_queue_status(stack_results: dict[str, tuple[list[str], list[str]]]) -> None:
    if not stack_results:
        return

    with QUEUE_PATH.open(encoding="utf-8") as f:
        queue = json.load(f)

    count = 0
    for stack in queue["stacks"]:
        sid = stack["id"]
        if sid not in stack_results:
            continue
        succeeded, failed = stack_results[sid]
        if failed:
            logger.warning(f"  [queue] stack '{sid}' 일부 실패 ({failed}) — pending 유지")
            continue
        if stack.get("status") == "pending":
            stack["status"] = "done"
            count += 1

    with QUEUE_PATH.open("w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    remaining = sum(1 for s in queue["stacks"] if s.get("status") == "pending")
    logger.info(f"  [queue] {count}개 stack done 처리 — 남은 pending stack: {remaining}개")


# ─── 부산물 정리 ─────────────────────────────────────────────────────────────
#
# gemini가 작업 중 임시 파일을 BASE_DIR 어딘가에 떨어뜨릴 수 있다.
# 실행 시작 시점의 파일 스냅샷과 비교해서 새로 생긴 파일만 골라 삭제.
# output/ 아래 파일은 무조건 보존.

def snapshot_files() -> frozenset[Path]:
    return frozenset(p for p in BASE_DIR.rglob("*") if p.is_file())


def cleanup_byproducts(protected: frozenset[Path], start_time: float) -> None:
    logger.info("  [cleanup] 부산물 스캔 시작")
    deleted: list[Path] = []

    for path in sorted(BASE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(BASE_DIR)
        # output/ 내 파일은 절대 삭제하지 않음
        try:
            path.relative_to(OUTPUT_DIR)
            continue
        except ValueError:
            pass
        # 실행 전부터 있던 파일은 보존
        if path in protected:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime <= start_time:
            continue
        try:
            path.unlink()
            deleted.append(path)
            logger.info(f"  [cleanup] 삭제: {rel}")
        except OSError as e:
            logger.warning(f"  [cleanup] 삭제 실패: {rel} — {e}")

    logger.info(f"  [cleanup] 완료 — 삭제 {len(deleted)}개")

    # 빈 디렉터리 정리 (BASE_DIR 자체는 보존)
    for dirpath in sorted(BASE_DIR.rglob("*"), reverse=True):
        if dirpath.is_dir() and dirpath != BASE_DIR:
            try:
                dirpath.rmdir()
            except OSError:
                pass


# ─── 메인 ────────────────────────────────────────────────────────────────────

def run() -> None:
    logger.info("=" * 60)
    logger.info("run_batches.py 시작")
    logger.info("=" * 60)

    start_time = time.time()
    protected = snapshot_files()
    logger.info(f"초기화 완료 — 보호 파일 {len(protected)}개")

    with open(QUEUE_PATH, encoding="utf-8") as f:
        queue = json.load(f)

    pending_stacks = [s for s in queue["stacks"] if s.get("status") == "pending"]

    if not pending_stacks:
        logger.info("처리할 stack이 없습니다. (모두 done)")
        return

    plan_lines = []
    for s in pending_stacks:
        task_summary = ", ".join(
            f"{t['id']}({t.get('model') or DEFAULT_MODEL})" for t in s.get("tasks", [])
        )
        plan_lines.append(
            f"  - stack {s['id']}: refs={len(s.get('reference_files', []))}개 / tasks=[{task_summary}]"
        )
    logger.info(f"pending stack ({len(pending_stacks)}개):\n" + "\n".join(plan_lines))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # stack별 결과: {stack_id: (succeeded_task_ids, failed_task_ids)}
    stack_results: dict[str, tuple[list[str], list[str]]] = {}

    # stack은 순차 실행. 같은 stack 안의 task만 병렬.
    for stack in pending_stacks:
        sid = stack["id"]
        succeeded, failed = process_stack(stack)
        stack_results[sid] = (succeeded, failed)
        merge_stack_outputs(sid, succeeded)

    # 종합 리포트
    logger.info("\n" + "=" * 60)
    for sid, (succ, fail) in stack_results.items():
        logger.info(f"[stack {sid}] 완료: {sorted(succ) or '없음'} / 실패: {sorted(fail) or '없음'}")
    logger.info("=" * 60)

    update_queue_status(stack_results)
    cleanup_byproducts(protected, start_time)


if __name__ == "__main__":
    run()
