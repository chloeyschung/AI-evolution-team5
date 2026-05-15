"""Modal vLLM 요약 엔드포인트 직접 검증 스크립트.

Usage:
    uv run python scripts/test_modal_summarize.py
    uv run python scripts/test_modal_summarize.py --url https://en.wikipedia.org/wiki/Large_language_model
"""

import argparse
import asyncio
import os
import re
import sys

import httpx

# .env 로드 (python-dotenv 없을 경우 직접 파싱)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

MODAL_ENDPOINT = os.getenv("MODAL_ENDPOINT", "").rstrip("/")
TOKEN_ID = os.getenv("MODAL_PROXY_TOKEN_ID", "")
TOKEN_SECRET = os.getenv("MODAL_PROXY_TOKEN_SECRET", "")
MODEL = os.getenv("SUMMARY_MODEL", "")

SAMPLE_ARTICLE = (
    "OpenAI released GPT-4o in May 2024, a multimodal model that processes text, audio, "
    "and images natively. It achieves GPT-4 Turbo-level performance while being 2x faster "
    "and 50% cheaper via API. Real-time voice conversation is supported without pipeline "
    "delays — the model responds directly to audio input. GPT-4o shows substantial "
    "improvement in non-English language tasks and can analyse charts, screenshots, and "
    "documents in-context. It is available in ChatGPT Free and API tiers as of mid-2024."
)

SUMMARIZE_PROMPT = (
    "Summarize as exactly 3 bullet points.\n"
    "Rules:\n"
    "- Start each bullet with '• '\n"
    "- Max 70 characters per bullet — be ruthlessly brief\n"
    "- One concrete fact per bullet\n"
    "- Output ONLY the 3 bullets, nothing else\n\n"
    "CONTENT:\n{content}"
)


async def discover_model(client: httpx.AsyncClient, headers: dict) -> str:
    r = await client.get(f"{MODAL_ENDPOINT}/v1/models", headers=headers, timeout=180)
    r.raise_for_status()
    models = r.json().get("data", [])
    return models[0]["id"] if models else ""


async def fetch_url_text(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as c:
        r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:6000]


async def call_summarize(text: str) -> str:
    auth_headers = {
        "content-type": "application/json",
        "Modal-Key": TOKEN_ID,
        "Modal-Secret": TOKEN_SECRET,
    }

    async with httpx.AsyncClient(timeout=180) as client:
        model = MODEL
        if not model:
            print("  모델명 조회 중...")
            model = await discover_model(client, auth_headers)
            if not model:
                raise RuntimeError("vLLM 서버에서 모델명을 가져올 수 없습니다. SUMMARY_MODEL을 .env에 직접 지정하세요.")
        print(f"  모델: {model}")

        payload = {
            "model": model,
            "max_tokens": 150,
            "messages": [
                {"role": "user", "content": SUMMARIZE_PROMPT.format(content=text)}
            ],
            "chat_template_kwargs": {"enable_thinking": False},
        }

        r = await client.post(
            f"{MODAL_ENDPOINT}/v1/chat/completions",
            headers=auth_headers,
            json=payload,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Modal 요약 엔드포인트 테스트")
    parser.add_argument("--url", help="요약할 웹 문서 URL (생략 시 샘플 텍스트 사용)")
    args = parser.parse_args()

    if not MODAL_ENDPOINT:
        print("오류: MODAL_ENDPOINT가 .env에 없습니다.")
        sys.exit(1)
    if not TOKEN_ID or not TOKEN_SECRET:
        print("오류: MODAL_PROXY_TOKEN_ID 또는 MODAL_PROXY_TOKEN_SECRET가 없습니다.")
        sys.exit(1)

    print(f"엔드포인트: {MODAL_ENDPOINT}")

    if args.url:
        print(f"URL 로드 중: {args.url}")
        text = await fetch_url_text(args.url)
        print(f"텍스트 추출: {len(text)}자\n")
    else:
        print("샘플 텍스트 사용\n")
        text = SAMPLE_ARTICLE

    print("요약 중... (첫 요청 시 cold start로 최대 60초 소요)")
    try:
        summary = await call_summarize(text)
        print("\n--- 요약 결과 ---")
        sys.stdout.buffer.write((summary + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()
        print("--- 완료 ---")
    except httpx.HTTPStatusError as e:
        print(f"\n오류 {e.response.status_code}: {e.response.text}")
        print("\n인증 실패 시 확인사항:")
        print("  - MODAL_PROXY_TOKEN_ID / MODAL_PROXY_TOKEN_SECRET 값이 올바른지 확인")
        print("  - Modal 대시보드에서 엔드포인트 proxy auth 설정 확인")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
