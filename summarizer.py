"""
sweepnews/summarizer.py
Claude APIでジャンル自動分類＋日本語要約
毎朝6時にGitHub Actionsから実行
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
DATA_DIR = Path("data/daily")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

GENRE_LABELS = {
    "ai_tech": "🤖 AI・テクノロジー",
    "business": "💼 ビジネス",
    "science": "🔬 科学・研究",
    "world_news": "🌍 世界ニュース",
    "finance": "📈 金融・経済",
    "health": "💊 健康・医療",
    "environment": "🌿 環境・気候",
    "gaming_esports": "🎮 ゲーム・eスポーツ",
    "entertainment": "🎬 エンタメ",
    "japan": "🇯🇵 日本",
    "dev_tools": "💻 開発・ツール",
    "other": "📰 その他",
}

SONNET_INPUT_PRICE = 3.0 / 1_000_000
SONNET_OUTPUT_PRICE = 15.0 / 1_000_000

total_cost = 0.0


def call_claude(prompt, max_tokens=2000):
    global total_cost
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
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
    cost = (usage.get("input_tokens", 0) * SONNET_INPUT_PRICE +
            usage.get("output_tokens", 0) * SONNET_OUTPUT_PRICE)
    total_cost += cost
    return result["content"][0]["text"]


def classify_and_summarize_batch(items):
    """複数記事を一括でジャンル分類＋日本語要約"""
    items_text = "\n".join([
        f"[{i+1}] タイトル: {item['title']}\n    説明: {item.get('description', '')[:200]}\n    ソース: {item.get('source', '')}"
        for i, item in enumerate(items)
    ])

    genres_list = "\n".join([f"- {k}: {v}" for k, v in GENRE_LABELS.items()])

    prompt = f"""以下の記事リストについて、各記事を分析してください。

【記事リスト】
{items_text}

【ジャンル一覧】
{genres_list}

各記事について以下を判定・生成してください：
1. genre: 最も適切なジャンルキー（ai_tech, business, science等）
2. genre_sub: サブジャンル（任意・例：「大規模言語モデル」「スタートアップ資金調達」）
3. title_ja: 日本語タイトル（自然な日本語で、元のニュアンスを保って）
4. summary_ja: 日本語要約（3〜4文、なぜ重要かまで含めて）
5. importance: 重要度スコア（1〜10、業界への影響度・新規性・話題性で判断）
6. keywords: キーワード（3〜5個、カンマ区切り）

必ず以下のJSON配列形式のみで返してください（説明文不要）：
[
  {{
    "index": 1,
    "genre": "ai_tech",
    "genre_sub": "サブジャンル",
    "title_ja": "日本語タイトル",
    "summary_ja": "日本語要約",
    "importance": 8,
    "keywords": "キーワード1, キーワード2, キーワード3"
  }},
  ...
]"""

    response = call_claude(prompt, max_tokens=4000)

    try:
        import re
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"  ⚠ JSONパースエラー: {e}")
    return []


def main():
    print(f"Sweepnews Summarizer 起動... [{TODAY}]")

    input_path = DATA_DIR / f"{TODAY}.json"
    if not input_path.exists():
        print(f"  ✗ {input_path} が見つかりません。collector.pyを先に実行してください。")
        return

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    print(f"  収集済み記事: {len(items)}件")

    # 重要度の高そうな記事を優先（各ジャンルから最大10件）
    genre_items = {}
    for item in items:
        genre = item.get("genre", "other")
        if genre not in genre_items:
            genre_items[genre] = []
        if len(genre_items[genre]) < 10:
            genre_items[genre].append(item)

    # バッチ処理（10件ずつ）
    target_items = []
    for genre, gitems in genre_items.items():
        target_items.extend(gitems[:8])  # 各ジャンル最大8件

    print(f"  要約対象: {len(target_items)}件")

    summarized = []
    batch_size = 10

    for i in range(0, len(target_items), batch_size):
        batch = target_items[i:i + batch_size]
        print(f"  バッチ処理中... {i+1}〜{min(i+batch_size, len(target_items))}件目")

        results = classify_and_summarize_batch(batch)

        for result in results:
            idx = result.get("index", 0) - 1
            if 0 <= idx < len(batch):
                original = batch[idx]
                summarized.append({
                    "title": original.get("title", ""),
                    "title_ja": result.get("title_ja", original.get("title", "")),
                    "url": original.get("url", ""),
                    "source": original.get("source", ""),
                    "genre": result.get("genre", original.get("genre", "other")),
                    "genre_label": GENRE_LABELS.get(result.get("genre", "other"), "📰 その他"),
                    "genre_sub": result.get("genre_sub", ""),
                    "summary_ja": result.get("summary_ja", ""),
                    "importance": result.get("importance", 5),
                    "keywords": result.get("keywords", ""),
                    "published": original.get("published", ""),
                })

    # 重要度順でソート
    summarized.sort(key=lambda x: x.get("importance", 0), reverse=True)

    # ジャンル別集計
    genre_summary = {}
    for item in summarized:
        genre = item.get("genre", "other")
        if genre not in genre_summary:
            genre_summary[genre] = {
                "label": item.get("genre_label", ""),
                "count": 0,
                "top_items": []
            }
        genre_summary[genre]["count"] += 1
        if len(genre_summary[genre]["top_items"]) < 3:
            genre_summary[genre]["top_items"].append(item.get("title_ja", ""))

    # 結果を保存
    output = {
        "date": TODAY,
        "summarized_at": datetime.now(timezone.utc).isoformat(),
        "total_collected": len(items),
        "total_summarized": len(summarized),
        "genre_summary": genre_summary,
        "cost_usd": round(total_cost, 6),
        "items": summarized,
    }

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 要約完了: {len(summarized)}件")
    print(f"  コスト: ${total_cost:.4f}")
    print("\nジャンル別:")
    for genre, info in genre_summary.items():
        print(f"  {info['label']}: {info['count']}件")


if __name__ == "__main__":
    main()
