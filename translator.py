"""
sweepnews/translator.py
収集した記事タイトルをClaude Haiku で日本語翻訳
summarizer.py の代替・超低コスト版
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
DATA_DIR = Path("data/daily")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

HAIKU_INPUT_PRICE  = 1.0 / 1_000_000
HAIKU_OUTPUT_PRICE = 5.0 / 1_000_000

total_cost = 0.0


def call_haiku(prompt, max_tokens=2000):
    global total_cost
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())

    usage = result.get("usage", {})
    cost = (usage.get("input_tokens", 0) * HAIKU_INPUT_PRICE +
            usage.get("output_tokens", 0) * HAIKU_OUTPUT_PRICE)
    total_cost += cost
    return result["content"][0]["text"]


def translate_batch(titles):
    """タイトルを一括翻訳（20件ずつ）"""
    numbered = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
    prompt = f"""以下の英語ニュースタイトルを自然な日本語に翻訳してください。

ルール：
- 番号付きリストで返す（1. 翻訳文）
- 翻訳のみ返す（説明不要）
- 日本語として自然な文体で
- 固有名詞はそのまま

{numbered}"""

    response = call_haiku(prompt, max_tokens=3000)

    results = {}
    import re
    for line in response.strip().split("\n"):
        m = re.match(r"(\d+)\.\s+(.+)", line.strip())
        if m:
            idx = int(m.group(1)) - 1
            results[idx] = m.group(2).strip()
    return results


def is_japanese(text):
    """日本語が含まれているか判定"""
    return any("\u3040" <= c <= "\u9fff" for c in text)


def main():
    print(f"Sweepnews Translator 起動... [{TODAY}]")

    input_path = DATA_DIR / f"{TODAY}.json"
    if not input_path.exists():
        print(f"  ✗ {input_path} が見つかりません")
        return

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    print(f"  収集済み記事: {len(items)}件")

    # 英語タイトルのみ翻訳対象
    to_translate = [(i, item) for i, item in enumerate(items) if not is_japanese(item.get("title", ""))]
    print(f"  翻訳対象: {len(to_translate)}件")

    # 20件ずつバッチ処理
    batch_size = 20
    for batch_start in range(0, len(to_translate), batch_size):
        batch = to_translate[batch_start:batch_start + batch_size]
        titles = [item["title"] for _, item in batch]

        print(f"  翻訳中... {batch_start+1}〜{min(batch_start+batch_size, len(to_translate))}件目")

        try:
            translated = translate_batch(titles)
            for local_idx, (global_idx, item) in enumerate(batch):
                if local_idx in translated:
                    items[global_idx]["title_ja"] = translated[local_idx]
                else:
                    items[global_idx]["title_ja"] = item["title"]
        except Exception as e:
            print(f"  ⚠ 翻訳エラー: {e}")
            for _, (global_idx, item) in enumerate(batch):
                items[global_idx]["title_ja"] = item["title"]

    # 日本語タイトルはそのままコピー
    for item in items:
        if "title_ja" not in item:
            item["title_ja"] = item.get("title", "")

    data["items"] = items
    data["translated_at"] = datetime.now(timezone.utc).isoformat()
    data["translation_cost_usd"] = round(total_cost, 6)

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 翻訳完了: {len(to_translate)}件")
    print(f"  コスト: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
