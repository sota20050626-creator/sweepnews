"""
sweepnews/collector.py
全ジャンルRSS収集スクリプト
毎朝6時にGitHub Actionsから実行
"""

import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
DATA_DIR = Path("data/daily")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================
# 全ジャンルRSSソース定義
# ============================
RSS_SOURCES = {
    "ai_tech": [
        {"url": "https://hnrss.org/frontpage?q=AI+OR+LLM+OR+machine+learning", "name": "HackerNews AI"},
        {"url": "https://rss.arxiv.org/rss/cs.AI", "name": "arXiv AI"},
        {"url": "https://rss.arxiv.org/rss/cs.LG", "name": "arXiv ML"},
        {"url": "https://rss.arxiv.org/rss/cs.CL", "name": "arXiv NLP"},
        {"url": "https://feeds.feedburner.com/TechCrunch/", "name": "TechCrunch"},
        {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge"},
        {"url": "https://feeds.arstechnica.com/arstechnica/index", "name": "Ars Technica"},
        {"url": "https://venturebeat.com/feed/", "name": "VentureBeat"},
        {"url": "https://www.wired.com/feed/rss", "name": "WIRED"},
    ],
    "business": [
        {"url": "https://feeds.bloomberg.com/markets/news.rss", "name": "Bloomberg Markets"},
        {"url": "https://feeds.reuters.com/reuters/businessNews", "name": "Reuters Business"},
        {"url": "https://hnrss.org/frontpage?q=startup+OR+funding+OR+IPO", "name": "HN Business"},
        {"url": "https://www.ft.com/rss/home", "name": "Financial Times"},
        {"url": "https://fortune.com/feed/", "name": "Fortune"},
        {"url": "https://hbr.org/rss", "name": "Harvard Business Review"},
    ],
    "science": [
        {"url": "https://rss.arxiv.org/rss/physics", "name": "arXiv Physics"},
        {"url": "https://rss.arxiv.org/rss/q-bio", "name": "arXiv Biology"},
        {"url": "https://www.nature.com/nature.rss", "name": "Nature"},
        {"url": "https://www.science.org/rss/news_current.xml", "name": "Science Magazine"},
        {"url": "https://www.newscientist.com/feed/home/?cmpid=RSS%7CNSNS-Home", "name": "New Scientist"},
        {"url": "https://feeds.sciencedaily.com/sciencedaily/top_news/top_science", "name": "ScienceDaily"},
    ],
    "world_news": [
        {"url": "https://feeds.reuters.com/reuters/topNews", "name": "Reuters Top"},
        {"url": "https://rss.cnn.com/rss/edition.rss", "name": "CNN"},
        {"url": "https://feeds.bbci.co.uk/news/rss.xml", "name": "BBC News"},
        {"url": "https://www.aljazeera.com/xml/rss/all.xml", "name": "Al Jazeera"},
        {"url": "https://feeds.japantimes.co.jp/japantimes/all", "name": "Japan Times"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat0.xml", "name": "NHK News"},
    ],
    "finance": [
        {"url": "https://feeds.reuters.com/reuters/financeNews", "name": "Reuters Finance"},
        {"url": "https://hnrss.org/frontpage?q=crypto+OR+bitcoin+OR+stocks", "name": "HN Finance"},
        {"url": "https://cointelegraph.com/rss", "name": "CoinTelegraph"},
        {"url": "https://decrypt.co/feed", "name": "Decrypt"},
        {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "name": "CoinDesk"},
    ],
    "health": [
        {"url": "https://rss.arxiv.org/rss/q-bio.NC", "name": "arXiv Neuroscience"},
        {"url": "https://feeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC", "name": "WebMD"},
        {"url": "https://www.medicalnewstoday.com/rss/", "name": "Medical News Today"},
        {"url": "https://feeds.reuters.com/reuters/healthNews", "name": "Reuters Health"},
    ],
    "environment": [
        {"url": "https://feeds.reuters.com/reuters/environment", "name": "Reuters Environment"},
        {"url": "https://www.theguardian.com/environment/rss", "name": "Guardian Environment"},
        {"url": "https://hnrss.org/frontpage?q=climate+OR+renewable+OR+sustainability", "name": "HN Environment"},
    ],
    "gaming_esports": [
        {"url": "https://www.ign.com/feeds/news.xml", "name": "IGN"},
        {"url": "https://www.polygon.com/rss/index.xml", "name": "Polygon"},
        {"url": "https://dotesports.com/feed", "name": "Dot Esports"},
        {"url": "https://www.gamespot.com/feeds/news/", "name": "GameSpot"},
    ],
    "entertainment": [
        {"url": "https://variety.com/feed/", "name": "Variety"},
        {"url": "https://deadline.com/feed/", "name": "Deadline"},
        {"url": "https://www.hollywoodreporter.com/feed/", "name": "Hollywood Reporter"},
    ],
    "japan": [
        {"url": "https://www3.nhk.or.jp/rss/news/cat0.xml", "name": "NHK総合"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat1.xml", "name": "NHK政治"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat3.xml", "name": "NHK経済"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat5.xml", "name": "NHKテクノロジー"},
        {"url": "https://www.asahi.com/rss/asahi/newsheadlines.rdf", "name": "朝日新聞"},
    ],
    "dev_tools": [
        {"url": "https://hnrss.org/frontpage?q=programming+OR+developer+OR+open+source", "name": "HN Dev"},
        {"url": "https://github.com/trending.atom", "name": "GitHub Trending"},
        {"url": "https://dev.to/feed", "name": "DEV.to"},
        {"url": "https://stackoverflow.blog/feed/", "name": "Stack Overflow Blog"},
    ],
}


def fetch_rss(url, name, timeout=8):
    """RSSフィードを取得してアイテムリストを返す"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Sweepnews/1.0 RSS Reader"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = r.read().decode("utf-8", errors="replace")

        items = []
        # Atomフィード対応
        entries = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)
        if not entries:
            # RSSフィード
            entries = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)

        for entry in entries[:15]:  # 各ソースから最大15件
            title = extract_tag(entry, "title")
            link = extract_link(entry)
            pub_date = extract_tag(entry, "pubDate") or extract_tag(entry, "published") or extract_tag(entry, "updated")
            description = extract_tag(entry, "description") or extract_tag(entry, "summary") or extract_tag(entry, "content")

            if title and link:
                items.append({
                    "title": clean_text(title),
                    "url": link,
                    "source": name,
                    "published": pub_date,
                    "description": clean_text(description)[:300] if description else "",
                })

        return items
    except Exception as e:
        print(f"  ⚠ {name}: {str(e)[:60]}")
        return []


def extract_tag(text, tag):
    """XMLタグから値を抽出"""
    # CDATA対応
    m = re.search(rf"<{tag}[^>]*><!\[CDATA\[(.*?)\]\]></{tag}>", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def extract_link(text):
    """リンクURLを抽出"""
    # Atomの<link href="...">
    m = re.search(r'<link[^>]+href=["\']([^"\']+)["\']', text)
    if m:
        return m.group(1).strip()
    # RSSの<link>
    m = re.search(r"<link>([^<]+)</link>", text)
    if m:
        return m.group(1).strip()
    # <guid>がURLの場合
    m = re.search(r"<guid[^>]*>https?://[^<]+</guid>", text)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(0)).strip()
    return ""


def clean_text(text):
    """HTMLタグ・特殊文字を除去"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def deduplicate(items):
    """URLで重複排除"""
    seen = set()
    result = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            result.append(item)
    return result


def main():
    print(f"Sweepnews Collector 起動... [{TODAY}]")
    all_items = []
    genre_counts = {}

    for genre, sources in RSS_SOURCES.items():
        print(f"\n📂 {genre}")
        genre_items = []
        for source in sources:
            items = fetch_rss(source["url"], source["name"])
            for item in items:
                item["genre"] = genre
            genre_items.extend(items)
            print(f"  ✓ {source['name']}: {len(items)}件")

        genre_items = deduplicate(genre_items)
        genre_counts[genre] = len(genre_items)
        all_items.extend(genre_items)

    all_items = deduplicate(all_items)

    output = {
        "date": TODAY,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_items),
        "genre_counts": genre_counts,
        "items": all_items,
    }

    output_path = DATA_DIR / f"{TODAY}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 収集完了: {len(all_items)}件 → {output_path}")
    for genre, count in genre_counts.items():
        print(f"  {genre}: {count}件")


if __name__ == "__main__":
    main()
