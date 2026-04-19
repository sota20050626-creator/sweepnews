"""
sweepnews/collector.py
全ジャンルRSS収集スクリプト
毎朝6時にGitHub Actionsから実行
"""

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
DATA_DIR = Path("data/daily")
DATA_DIR.mkdir(parents=True, exist_ok=True)

GENRE_LABELS = {
    "ai_tech":       "🤖 AI・テクノロジー",
    "business":      "💼 ビジネス",
    "science":       "🔬 科学・研究",
    "world_news":    "🌍 世界ニュース",
    "finance":       "📈 金融・経済",
    "health":        "💊 健康・医療",
    "environment":   "🌿 環境・気候",
    "gaming_esports":"🎮 ゲーム・eスポーツ",
    "entertainment": "🎬 エンタメ",
    "japan":         "🇯🇵 日本",
    "dev_tools":     "💻 開発・ツール",
    "other":         "📰 その他",
}

RSS_SOURCES = {
    "ai_tech": [
        {"url": "https://hnrss.org/frontpage?q=AI+OR+LLM+OR+machine+learning", "name": "HackerNews AI"},
        {"url": "https://rss.arxiv.org/rss/cs.AI", "name": "arXiv AI"},
        {"url": "https://rss.arxiv.org/rss/cs.LG", "name": "arXiv ML"},
        {"url": "https://rss.arxiv.org/rss/cs.CL", "name": "arXiv NLP"},
        {"url": "https://rss.arxiv.org/rss/cs.CV", "name": "arXiv CV"},
        {"url": "https://feeds.feedburner.com/TechCrunch/", "name": "TechCrunch"},
        {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge"},
        {"url": "https://feeds.arstechnica.com/arstechnica/index", "name": "Ars Technica"},
        {"url": "https://venturebeat.com/feed/", "name": "VentureBeat"},
        {"url": "https://www.wired.com/feed/rss", "name": "WIRED"},
        {"url": "https://machinelearningmastery.com/feed/", "name": "ML Mastery"},
        {"url": "https://towardsdatascience.com/feed", "name": "Towards Data Science"},
        {"url": "https://openai.com/blog/rss.xml", "name": "OpenAI Blog"},
        {"url": "https://www.anthropic.com/rss.xml", "name": "Anthropic Blog"},
        {"url": "https://huggingface.co/blog/feed.xml", "name": "HuggingFace Blog"},
    ],
    "business": [
        {"url": "https://feeds.bloomberg.com/markets/news.rss", "name": "Bloomberg Markets"},
        {"url": "https://feeds.reuters.com/reuters/businessNews", "name": "Reuters Business"},
        {"url": "https://hnrss.org/frontpage?q=startup+OR+funding+OR+IPO", "name": "HN Business"},
        {"url": "https://www.ft.com/rss/home", "name": "Financial Times"},
        {"url": "https://fortune.com/feed/", "name": "Fortune"},
        {"url": "https://hbr.org/rss", "name": "Harvard Business Review"},
        {"url": "https://www.businessinsider.com/rss", "name": "Business Insider"},
        {"url": "https://inc.com/rss", "name": "Inc."},
        {"url": "https://www.fastcompany.com/rss", "name": "Fast Company"},
        {"url": "https://techcrunch.com/category/startups/feed/", "name": "TechCrunch Startups"},
    ],
    "science": [
        {"url": "https://rss.arxiv.org/rss/physics", "name": "arXiv Physics"},
        {"url": "https://rss.arxiv.org/rss/q-bio", "name": "arXiv Biology"},
        {"url": "https://www.nature.com/nature.rss", "name": "Nature"},
        {"url": "https://www.science.org/rss/news_current.xml", "name": "Science Magazine"},
        {"url": "https://www.newscientist.com/feed/home/", "name": "New Scientist"},
        {"url": "https://feeds.sciencedaily.com/sciencedaily/top_news/top_science", "name": "ScienceDaily"},
        {"url": "https://www.scientificamerican.com/feed/", "name": "Scientific American"},
        {"url": "https://phys.org/rss-feed/", "name": "Phys.org"},
        {"url": "https://www.popsci.com/feed/", "name": "Popular Science"},
    ],
    "world_news": [
        {"url": "https://feeds.reuters.com/reuters/topNews", "name": "Reuters Top"},
        {"url": "https://rss.cnn.com/rss/edition.rss", "name": "CNN"},
        {"url": "https://feeds.bbci.co.uk/news/rss.xml", "name": "BBC News"},
        {"url": "https://www.aljazeera.com/xml/rss/all.xml", "name": "Al Jazeera"},
        {"url": "https://feeds.japantimes.co.jp/japantimes/all", "name": "Japan Times"},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "name": "NYT World"},
        {"url": "https://www.theguardian.com/world/rss", "name": "Guardian World"},
        {"url": "https://feeds.washingtonpost.com/rss/world", "name": "Washington Post World"},
        {"url": "https://foreignpolicy.com/feed/", "name": "Foreign Policy"},
    ],
    "finance": [
        {"url": "https://feeds.reuters.com/reuters/financeNews", "name": "Reuters Finance"},
        {"url": "https://hnrss.org/frontpage?q=crypto+OR+bitcoin+OR+stocks", "name": "HN Finance"},
        {"url": "https://cointelegraph.com/rss", "name": "CoinTelegraph"},
        {"url": "https://decrypt.co/feed", "name": "Decrypt"},
        {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "name": "CoinDesk"},
        {"url": "https://feeds.bloomberg.com/economics/news.rss", "name": "Bloomberg Economics"},
        {"url": "https://seekingalpha.com/feed.xml", "name": "Seeking Alpha"},
        {"url": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_headline", "name": "Investopedia"},
    ],
    "health": [
        {"url": "https://rss.arxiv.org/rss/q-bio.NC", "name": "arXiv Neuroscience"},
        {"url": "https://feeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC", "name": "WebMD"},
        {"url": "https://www.medicalnewstoday.com/rss/", "name": "Medical News Today"},
        {"url": "https://feeds.reuters.com/reuters/healthNews", "name": "Reuters Health"},
        {"url": "https://www.healthline.com/nutrition/feed", "name": "Healthline"},
        {"url": "https://www.statnews.com/feed/", "name": "STAT News"},
        {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "name": "BBC Health"},
        {"url": "https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm", "name": "NEJM"},
    ],
    "environment": [
        {"url": "https://feeds.reuters.com/reuters/environment", "name": "Reuters Environment"},
        {"url": "https://www.theguardian.com/environment/rss", "name": "Guardian Environment"},
        {"url": "https://hnrss.org/frontpage?q=climate+OR+renewable+OR+sustainability", "name": "HN Environment"},
        {"url": "https://grist.org/feed/", "name": "Grist"},
        {"url": "https://e360.yale.edu/feed", "name": "Yale E360"},
        {"url": "https://www.carbonbrief.org/feed", "name": "Carbon Brief"},
        {"url": "https://insideclimatenews.org/feed/", "name": "Inside Climate News"},
    ],
    "gaming_esports": [
        {"url": "https://www.ign.com/feeds/news.xml", "name": "IGN"},
        {"url": "https://www.polygon.com/rss/index.xml", "name": "Polygon"},
        {"url": "https://dotesports.com/feed", "name": "Dot Esports"},
        {"url": "https://www.gamespot.com/feeds/news/", "name": "GameSpot"},
        {"url": "https://kotaku.com/rss", "name": "Kotaku"},
        {"url": "https://www.eurogamer.net/feed", "name": "Eurogamer"},
        {"url": "https://www.pcgamer.com/rss/", "name": "PC Gamer"},
        {"url": "https://www.gamesradar.com/rss/", "name": "GamesRadar"},
    ],
    "entertainment": [
        {"url": "https://variety.com/feed/", "name": "Variety"},
        {"url": "https://deadline.com/feed/", "name": "Deadline"},
        {"url": "https://www.hollywoodreporter.com/feed/", "name": "Hollywood Reporter"},
        {"url": "https://pitchfork.com/rss/news/feed.xml", "name": "Pitchfork"},
        {"url": "https://www.rollingstone.com/feed/", "name": "Rolling Stone"},
        {"url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "name": "BBC Entertainment"},
        {"url": "https://ew.com/feed/", "name": "Entertainment Weekly"},
    ],
    "japan": [
        {"url": "https://www3.nhk.or.jp/rss/news/cat0.xml", "name": "NHK総合"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat1.xml", "name": "NHK政治"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat3.xml", "name": "NHK経済"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat5.xml", "name": "NHKテクノロジー"},
        {"url": "https://www3.nhk.or.jp/rss/news/cat7.xml", "name": "NHK国際"},
        {"url": "https://www.asahi.com/rss/asahi/newsheadlines.rdf", "name": "朝日新聞"},
        {"url": "https://feeds.japantimes.co.jp/japantimes/all", "name": "Japan Times"},
        {"url": "https://jp.reuters.com/rssFeed/topNews/", "name": "Reuters Japan"},
    ],
    "dev_tools": [
        {"url": "https://hnrss.org/frontpage?q=programming+OR+developer+OR+open+source", "name": "HN Dev"},
        {"url": "https://github.com/trending.atom", "name": "GitHub Trending"},
        {"url": "https://dev.to/feed", "name": "DEV.to"},
        {"url": "https://stackoverflow.blog/feed/", "name": "Stack Overflow Blog"},
        {"url": "https://css-tricks.com/feed/", "name": "CSS Tricks"},
        {"url": "https://www.smashingmagazine.com/feed/", "name": "Smashing Magazine"},
        {"url": "https://thenewstack.io/feed/", "name": "The New Stack"},
        {"url": "https://www.infoq.com/feed/", "name": "InfoQ"},
        {"url": "https://changelog.com/feed", "name": "Changelog"},
    ],
}


def fetch_rss(url, name, timeout=10):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Sweepnews/1.0 RSS Reader"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = r.read().decode("utf-8", errors="replace")

        items = []
        entries = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)
        if not entries:
            entries = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)

        for entry in entries[:20]:
            title = extract_tag(entry, "title")
            link = extract_link(entry)
            pub_date = (extract_tag(entry, "pubDate") or
                        extract_tag(entry, "published") or
                        extract_tag(entry, "updated"))
            description = (extract_tag(entry, "description") or
                           extract_tag(entry, "summary") or
                           extract_tag(entry, "content"))

            if title and link:
                items.append({
                    "title": clean_text(title),
                    "url": link,
                    "source": name,
                    "published": pub_date,
                    "description": clean_text(description)[:200] if description else "",
                })

        return items
    except Exception as e:
        print(f"  ⚠ {name}: {str(e)[:60]}")
        return []


def extract_tag(text, tag):
    m = re.search(rf"<{tag}[^>]*><!\[CDATA\[(.*?)\]\]></{tag}>", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def extract_link(text):
    m = re.search(r'<link[^>]+href=["\']([^"\']+)["\']', text)
    if m:
        return m.group(1).strip()
    m = re.search(r"<link>([^<]+)</link>", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"<guid[^>]*>https?://[^<]+</guid>", text)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(0)).strip()
    return ""


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"')
                .replace("&#39;", "'").replace("&nbsp;", " ")
                .replace("&#8217;", "'").replace("&#8216;", "'")
                .replace("&#8220;", '"').replace("&#8221;", '"'))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def filter_recent(items, days=7):
    """7日以内の記事のみ残す"""
    import email.utils
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    result = []
    for item in items:
        pub = item.get("published", "")
        try:
            ts = email.utils.parsedate_to_datetime(pub).timestamp()
            if ts >= cutoff:
                result.append(item)
        except Exception:
            result.append(item)
    return result


def deduplicate(items):
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
        print(f"\n📂 {genre} ({len(sources)}ソース)")
        genre_items = []
        for source in sources:
            items = fetch_rss(source["url"], source["name"])
            for item in items:
                item["genre"] = genre
                item["genre_label"] = GENRE_LABELS.get(genre, "📰 その他")
            genre_items.extend(items)
            print(f"  ✓ {source['name']}: {len(items)}件")

        genre_items = deduplicate(genre_items)
        genre_counts[genre] = len(genre_items)
        all_items.extend(genre_items)

    all_items = deduplicate(all_items)
    all_items = filter_recent(all_items, days=7)
    print(f"  7日以内: {len(all_items)}件")

    # ジャンル別サマリー生成
    genre_summary = {}
    for genre, count in genre_counts.items():
        genre_summary[genre] = {
            "label": GENRE_LABELS.get(genre, "📰 その他"),
            "count": count,
        }

    output = {
        "date": TODAY,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_items),
        "genre_counts": genre_counts,
        "genre_summary": genre_summary,
        "items": all_items,
    }

    output_path = DATA_DIR / f"{TODAY}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 収集完了: {len(all_items)}件 → {output_path}")
    for genre, count in genre_counts.items():
        print(f"  {GENRE_LABELS.get(genre, genre)}: {count}件")


if __name__ == "__main__":
    main()
