#!/usr/bin/env python3
"""
每日AI资讯速览 - GitHub Actions 版
自动抓取多个新闻源，分类整理并推送至 iPhone (Bark)
"""

import os
import re
import json
import requests
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree

# ============================================================
# 配置
# ============================================================
BARK_KEY = os.environ.get("BARK_KEY", "")
BARK_URL = f"https://api.day.app/{BARK_KEY}/"
BEIJING_TZ = timezone(timedelta(hours=8))
NOW = datetime.now(BEIJING_TZ)
TODAY = NOW.strftime("%Y-%m-%d")
TODAY_CN = NOW.strftime("%Y年%m月%d日")

# ============================================================
# 新闻抓取
# ============================================================

def fetch_36kr_ai_news():
    """抓取 36氪 AI 资讯"""
    items = []
    try:
        # 36氪快讯 - AI相关
        url = "https://36kr.com/api/newsflash?per_page=20&biz_type=tech&category_id=17"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.ok:
            data = resp.json()
            for item in data.get("data", {}).get("items", []):
                title = item.get("title", "")
                if any(kw in title for kw in ["AI", "人工智能", "大模型", "智能", "芯片", "机器人",
                                               "算力", "模型", "GPT", "Claude", "DeepSeek", "融资"]):
                    items.append({
                        "title": title,
                        "summary": item.get("description", ""),
                        "source": "36氪",
                        "url": item.get("news_url", "")
                    })
    except Exception as e:
        print(f"[WARN] 36氪抓取失败: {e}")
    return items


def fetch_github_trending_ai():
    """抓取 GitHub 热门 AI 项目"""
    items = []
    try:
        url = "https://api.github.com/search/repositories?q=ai+llm+created:>2025-01-01&sort=stars&order=desc&per_page=10"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github.v3+json"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.ok:
            data = resp.json()
            for repo in data.get("items", [])[:5]:
                items.append({
                    "title": f"[开源] {repo.get('full_name', '')} - ⭐{repo.get('stargazers_count', 0)}",
                    "summary": repo.get("description", "") or "",
                    "source": "GitHub",
                    "url": repo.get("html_url", "")
                })
    except Exception as e:
        print(f"[WARN] GitHub 热门抓取失败: {e}")
    return items


def fetch_hackernews_ai():
    """抓取 Hacker News 上 AI 相关热门"""
    items = []
    try:
        # 获取 top stories
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        if not resp.ok:
            return items
        top_ids = resp.json()[:30]

        for story_id in top_ids:
            try:
                s_resp = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=10)
                if not s_resp.ok:
                    continue
                story = s_resp.json()
                title = story.get("title", "")
                if any(kw in title.lower() for kw in ["ai", "artificial intelligence", "llm", "gpt", "openai",
                                                        "anthropic", "deepseek", "machine learning", "neural",
                                                        "robot", "automation", "chatgpt", "claude", "gemini"]):
                    items.append({
                        "title": title,
                        "summary": story.get("text", "")[:200] if story.get("text") else "",
                        "source": "Hacker News",
                        "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                    })
            except:
                continue
            if len(items) >= 8:
                break
    except Exception as e:
        print(f"[WARN] HackerNews 抓取失败: {e}")
    return items


# ============================================================
# 分类器 - 关键词匹配
# ============================================================

def classify_news(item):
    """通过关键词将新闻分到7个维度"""
    title = item["title"]
    summary = item.get("summary", "")
    text = (title + " " + summary).lower()

    # 1. 核心头条 - 涉及巨头重大变动
    if any(kw in text for kw in ["openai", "anthropic", "google", "meta", "microsoft", "马斯克",
                                   "xai", "spacex", "合并", "收购", "解散", "估值", "万亿"]):
        return "headlines"

    # 2. 融资动态
    if any(kw in text for kw in ["融资", "估值", "投资", "ipo", "上市", "估值", "募资",
                                   "funding", "valuation", "invest"]):
        return "funding"

    # 3. 政策标准
    if any(kw in text for kw in ["政策", "标准", "法规", "监管", "治理", "工信部", "网信办",
                                   "regulation", "policy", "标准", "立法"]):
        return "policies"

    # 4. 芯片算力
    if any(kw in text for kw in ["芯片", "gpu", "算力", "半导体", "hbm", "英伟达", "nvidia",
                                   "amd", "intel", "台积电", "处理器", "存储", "asic"]):
        return "chips"

    # 5. 机器人具身智能
    if any(kw in text for kw in ["机器人", "具身", "人形", "robot", "humanoid", "无人机",
                                   "自动驾驶", "eVTOL", "机器狗"]):
        return "robots"

    # 6. 产业链经济
    if any(kw in text for kw in ["产业链", "经济", "市场", "etf", "股市", "资本", "财报",
                                   "营收", "利润", "增长", "景气"]):
        return "economy"

    # 7. 安全治理（默认放到最后）
    if any(kw in text for kw in ["安全", "伦理", "偏见", "歧视", "幻觉", "隐私", "数据",
                                   "安全准则", "可信", "风险", "有害"]):
        return "safety"

    return "other"


# ============================================================
# 报告生成
# ============================================================

CATEGORY_NAMES = {
    "headlines": ("🔥", "核心头条"),
    "funding": ("💰", "融资动态"),
    "policies": ("🏭", "政策标准"),
    "chips": ("💻", "芯片算力"),
    "robots": ("🤖", "机器人具身智能"),
    "economy": ("📊", "产业链经济"),
    "safety": ("🛡️", "安全治理"),
}

CATEGORY_ORDER = ["headlines", "funding", "policies", "chips", "robots", "economy", "safety"]


def generate_report(all_items):
    """生成结构化 Markdown 报告"""
    # 分类
    classified = {k: [] for k in CATEGORY_ORDER}
    for item in all_items:
        cat = classify_news(item)
        if cat in classified:
            classified[cat].append(item)

    # 去重（按标题关键词去重）
    seen = set()
    for cat in CATEGORY_ORDER:
        unique = []
        for item in classified[cat]:
            key = item["title"][:20]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        classified[cat] = unique

    # 构建报告
    sections = []
    for cat in CATEGORY_ORDER:
        items = classified[cat]
        if not items:
            continue
        emoji, name = CATEGORY_NAMES[cat]
        section = f"## {emoji} {name}\n\n"
        for item in items[:5]:
            section += f"- **{item['title']}**"
            if item.get("summary"):
                section += f"\n  {item['summary'][:100]}"
            section += f"\n  *来源: {item['source']}*\n\n"
        sections.append(section)

    report = (
        f"# 📰 每日AI资讯速览\n\n"
        f"> **日期**: {TODAY_CN}\n"
        f"> **数据来源**: 36氪 / Hacker News / GitHub\n\n"
        f"---\n\n"
        + "\n".join(sections) +
        f"\n---\n"
        f"> 📌 *本报告由 GitHub Actions 自动生成于 {NOW.strftime('%H:%M')}*\n"
    )
    return report


def generate_push_body(classified):
    """生成推送到 iPhone 的摘要正文"""
    lines = []
    for cat in CATEGORY_ORDER:
        items = classified[cat]
        if not items:
            continue
        emoji, name = CATEGORY_NAMES[cat]
        lines.append(f"{emoji}【{name}】")
        for item in items[:2]:
            title = item["title"][:30]
            lines.append(f"  • {title}")
        lines.append("")

    return "\n".join(lines).strip()


# ============================================================
# 主流程
# ============================================================

def main():
    print(f"🔍 每日AI资讯速览 - {TODAY}")
    print("=" * 40)

    # 1. 抓取所有新闻
    print("\n📡 正在抓取资讯...")
    all_items = []
    all_items.extend(fetch_36kr_ai_news())
    all_items.extend(fetch_hackernews_ai())
    all_items.extend(fetch_github_trending_ai())
    print(f"   共获取 {len(all_items)} 条原始资讯")

    # 2. 分类整理
    print("\n📋 正在分类整理...")
    classified = {k: [] for k in CATEGORY_ORDER}
    for item in all_items:
        cat = classify_news(item)
        if cat in classified:
            classified[cat].append(item)

    for cat in CATEGORY_ORDER:
        print(f"   {CATEGORY_NAMES[cat][0]} {CATEGORY_NAMES[cat][1]}: {len(classified[cat])} 条")

    # 3. 生成 Markdown 报告
    report = generate_report(all_items)

    os.makedirs("output", exist_ok=True)
    report_path = f"output/ai_news_{TODAY}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 报告已保存: {report_path}")

    # 4. 推送 Bark 通知
    body = generate_push_body(classified)
    if not body:
        body = f"今日暂未获取到AI相关资讯，请稍后查看完整报告。"
    title = f"📰 AI资讯速览 | {TODAY}"
    group = "AI资讯"

    payload = {
        "title": title,
        "body": body,
        "group": group,
        "icon": "https://emojicdn.elk.sh/📰"
    }

    print(f"\n📱 正在推送至 iPhone...")
    resp = requests.post(BARK_URL, json=payload, timeout=15)
    if resp.ok:
        print(f"   ✅ Bark 推送成功: {resp.json()}")
    else:
        print(f"   ❌ Bark 推送失败: {resp.status_code} {resp.text}")

    print("\n✅ 完成!")
    return report


if __name__ == "__main__":
    main()
