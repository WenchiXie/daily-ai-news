#!/usr/bin/env python3
"""
每日AI资讯速览 - GitHub Actions 版 v2.0
自动抓取多个新闻源（机器之心、IT之家、36氪、雷锋网、Hacker News、GitHub），
分类整理并推送至 iPhone (Bark)
"""

import os
import re
import html
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
TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ============================================================
# 工具函数
# ============================================================

def clean_html(raw: str) -> str:
    """去除 HTML 标签，保留纯文本"""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


def parse_rss(url: str, source_name: str, max_items: int = 20) -> list:
    """通用 RSS 解析器"""
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not resp.ok:
            print(f"  [WARN] {source_name} RSS 请求失败: HTTP {resp.status_code}")
            return items
        root = ElementTree.fromstring(resp.content)
        # RSS 2.0: /rss/channel/item
        for entry in root.iter("item"):
            title = ""
            summary = ""
            link = ""
            title_el = entry.find("title")
            if title_el is not None and title_el.text:
                title = clean_html(title_el.text)
            desc_el = entry.find("description")
            if desc_el is not None and desc_el.text:
                summary = clean_html(desc_el.text)
            link_el = entry.find("link")
            if link_el is not None and link_el.text:
                link = link_el.text.strip()
            if title:
                items.append({
                    "title": title,
                    "summary": summary,
                    "source": source_name,
                    "url": link
                })
            if len(items) >= max_items:
                break
    except ElementTree.ParseError as e:
        print(f"  [WARN] {source_name} XML 解析失败: {e}")
    except Exception as e:
        print(f"  [WARN] {source_name} 抓取失败: {e}")
    return items


def scrape_leiphone_ai(max_items: int = 15) -> list:
    """爬取雷锋网 AI 分类（移动版）"""
    items = []
    try:
        url = "https://m.leiphone.com/category/ai"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not resp.ok:
            print(f"  [WARN] 雷锋网请求失败: HTTP {resp.status_code}")
            return items

        html_text = resp.text
        # 匹配文章卡片: <h2 class="tle"><a href="...">title</a></h2>
        # 或带 class="tit" 的链接
        # 雷锋网 m 站典型结构:
        # <li class="item">
        #   <h2 class="tle"><a href="/category/ai/xxx.html">标题</a></h2>
        #   <p class="text">摘要...</p>
        #   <span class="time">时间</span>
        # </li>
        article_pattern = re.compile(
            r'<h2[^>]*class="tle"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        for href, title_html in article_pattern.findall(html_text)[:max_items]:
            title = clean_html(title_html)
            if not title:
                continue
            url_full = f"https://m.leiphone.com{href}" if href.startswith("/") else href
            items.append({
                "title": title,
                "summary": "",
                "source": "雷锋网",
                "url": url_full
            })

        # 尝试提取摘要
        summary_pattern = re.compile(
            r'<p[^>]*class="text"[^>]*>(.*?)</p>',
            re.DOTALL
        )
        summaries = summary_pattern.findall(html_text)
        for i, s in enumerate(summaries[:max_items]):
            if i < len(items):
                items[i]["summary"] = clean_html(s)

    except Exception as e:
        print(f"  [WARN] 雷锋网抓取失败: {e}")
    return items


# ============================================================
# 各数据源抓取函数
# ============================================================

def fetch_jiqizhixin():
    """机器之心 - AI专业媒体 (RSS)"""
    print("  📡 机器之心...", end=" ", flush=True)
    items = parse_rss("https://www.jiqizhixin.com/rss", "机器之心", max_items=20)
    print(f"✓ {len(items)} 条")
    return items


def fetch_ithome():
    """IT之家 - 综合科技资讯 (RSS)"""
    print("  📡 IT之家...", end=" ", flush=True)
    items = parse_rss("https://www.ithome.com/rss/", "IT之家", max_items=20)
    print(f"✓ {len(items)} 条")
    return items


def fetch_36kr():
    """36氪 - 科技商业媒体 (RSS)"""
    print("  📡 36氪...", end=" ", flush=True)
    items = parse_rss("https://36kr.com/feed", "36氪", max_items=20)
    print(f"✓ {len(items)} 条")
    return items


def fetch_leiphone():
    """雷锋网 AI 频道 (爬虫)"""
    print("  📡 雷锋网AI...", end=" ", flush=True)
    items = scrape_leiphone_ai(max_items=15)
    print(f"✓ {len(items)} 条")
    return items


def fetch_hackernews():
    """Hacker News - 国际AI资讯"""
    print("  📡 Hacker News...", end=" ", flush=True)
    items = []
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=TIMEOUT
        )
        if not resp.ok:
            print("✗")
            return items
        top_ids = resp.json()[:40]
        count = 0
        for story_id in top_ids:
            try:
                s_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10
                )
                if not s_resp.ok:
                    continue
                story = s_resp.json()
                title = story.get("title", "")
                keywords = [
                    "ai", "artificial intelligence", "llm", "gpt", "openai",
                    "anthropic", "deepseek", "machine learning", "neural",
                    "robot", "automation", "chatgpt", "claude", "gemini",
                    "transformer", "diffusion", "language model", "agent",
                    "rlhf", "alignment", "agi", "llama", "mistral"
                ]
                if any(kw in title.lower() for kw in keywords):
                    items.append({
                        "title": title,
                        "summary": (story.get("text") or "")[:200],
                        "source": "Hacker News",
                        "url": story.get(
                            "url",
                            f"https://news.ycombinator.com/item?id={story_id}"
                        )
                    })
                    count += 1
                    if count >= 10:
                        break
            except Exception:
                continue
        print(f"✓ {len(items)} 条")
    except Exception as e:
        print(f"✗ {e}")
    return items


def fetch_github_trending():
    """GitHub 热门 AI 开源项目"""
    print("  📡 GitHub...", end=" ", flush=True)
    items = []
    try:
        url = (
            "https://api.github.com/search/repositories"
            "?q=ai+llm+created:>2025-01-01&sort=stars&order=desc&per_page=10"
        )
        headers_gh = {**HEADERS, "Accept": "application/vnd.github.v3+json"}
        resp = requests.get(url, headers=headers_gh, timeout=TIMEOUT)
        if resp.ok:
            data = resp.json()
            for repo in data.get("items", [])[:5]:
                items.append({
                    "title": (
                        f"[开源] {repo.get('full_name', '')} "
                        f"- ⭐{repo.get('stargazers_count', 0)}"
                    ),
                    "summary": (repo.get("description") or "")[:200],
                    "source": "GitHub",
                    "url": repo.get("html_url", "")
                })
        print(f"✓ {len(items)} 条")
    except Exception as e:
        print(f"✗ {e}")
    return items


# ============================================================
# 分类器 - 关键词匹配（增强版）
# ============================================================

def classify_news(item):
    """通过关键词将新闻分到7个维度"""
    title = item["title"]
    summary = item.get("summary", "")
    text = title + " " + summary

    t = text.lower()

    # 1. 🔥 核心头条 - 涉及巨头重大变动/里程碑
    if any(kw in t for kw in [
        "openai", "anthropic", "google", "meta", "microsoft",
        "马斯克", "xai", "spacex", "合并", "收购", "解散",
        "万亿", "重磅", "首次", "里程碑", "发布", "新品",
        "apple intelligence", "谷歌", "百度", "腾讯", "阿里",
        "字节", "推出", "上线", "重大", "突破", "超越",
        "gemini", "gpt-5", "gpt5", "claude 4", "llama 4",
        "deepseek", "发布", "新品", "中国版",
    ]):
        return "headlines"

    # 2. 💰 融资动态
    if any(kw in t for kw in [
        "融资", "估值", "投资", "ipo", "上市", "募资",
        "funding", "valuation", "invest", "series",
        "天使轮", "a轮", "b轮", "c轮", "战略投资",
        "出资", "亿元", "融资额",
    ]):
        return "funding"

    # 3. 🏭 政策标准
    if any(kw in t for kw in [
        "政策", "标准", "法规", "监管", "治理", "工信部",
        "网信办", "regulation", "policy", "立法", "法案",
        "白宫", "欧盟", "中美", "出口管制", "限制",
        "合规", "备案", "安全评估",
    ]):
        return "policies"

    # 4. 💻 芯片算力
    if any(kw in t for kw in [
        "芯片", "gpu", "算力", "半导体", "hbm", "英伟达",
        "nvidia", "amd", "intel", "台积电", "处理器",
        "存储", "asic", "cpu", "tpu", "npu", "soc",
        "寒武纪", "海光", "龙芯", "昇腾", "鲲鹏",
        "封装", "光刻", "晶圆", "制程",
    ]):
        return "chips"

    # 5. 🤖 机器人具身智能
    if any(kw in t for kw in [
        "机器人", "具身", "人形", "robot", "humanoid",
        "无人机", "自动驾驶", "evtol", "机器狗",
        "宇树", "特斯拉机器人", "optimu", "擎天柱",
        "波士顿动力", "figure", "机器臂", "灵巧手",
    ]):
        return "robots"

    # 6. 📊 产业链经济
    if any(kw in t for kw in [
        "产业链", "经济", "市场", "etf", "股市", "资本",
        "财报", "营收", "利润", "增长", "景气", "市值",
        "股价", "下跌", "上涨", "降息", "通胀",
        "供应链", "制造业", "出海", "关税",
    ]):
        return "economy"

    # 7. 🛡️ 安全治理
    if any(kw in t for kw in [
        "安全", "伦理", "偏见", "歧视", "幻觉", "隐私",
        "安全准则", "可信", "风险", "有害", "滥用",
        "safety", "alignment", "jailbreak", "对抗",
        "投毒", "深度伪造", "deepfake",
    ]):
        return "safety"

    # 如果标题明确包含 AI 关键词但未匹配上面分类，作为核心头条
    if any(kw in t for kw in [
        "ai", "人工智能", "大模型", "智能", "模型",
        "机器学习", "深度学", "gpt", "llm",
    ]):
        return "headlines"

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


def classify_items(all_items):
    """分类并去重"""
    classified = {k: [] for k in CATEGORY_ORDER}
    others = []

    for item in all_items:
        cat = classify_news(item)
        if cat in classified:
            classified[cat].append(item)
        else:
            others.append(item)

    # 去重（按标题开头15个字去重）
    seen = set()
    for cat in CATEGORY_ORDER:
        unique = []
        for item in classified[cat]:
            key = item["title"][:15]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        classified[cat] = unique

    return classified


def generate_report(all_items):
    """生成结构化 Markdown 报告"""
    classified = classify_items(all_items)

    sections = []
    for cat in CATEGORY_ORDER:
        items = classified[cat]
        if not items:
            continue
        emoji, name = CATEGORY_NAMES[cat]
        section = f"## {emoji} {name}\n\n"
        for i, item in enumerate(items[:6]):
            section += f"**{i+1}. {item['title']}**\n\n"
            if item.get("summary"):
                summary = item["summary"][:150]
                section += f"> {summary}\n\n"
            section += f"*来源: {item['source']}*\n\n"
        sections.append(section)

    # 统计
    total_classified = sum(len(classified[c]) for c in CATEGORY_ORDER)
    source_list = " / ".join(sorted(set(
        item["source"] for item in all_items
    )))

    report = (
        f"# 📰 每日AI资讯速览\n\n"
        f"> **日期**: {TODAY_CN}\n"
        f"> **数据来源**: {source_list}\n"
        f"> **共收录**: {total_classified} 条精选资讯（来自{len(all_items)}条原始数据）\n\n"
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
            lines.append(f"{CATEGORY_NAMES[cat][0]}【{CATEGORY_NAMES[cat][1]}】暂无")
            lines.append("")
            continue
        emoji, name = CATEGORY_NAMES[cat]
        lines.append(f"{emoji}【{name}】")
        for item in items[:2]:
            title = item["title"]
            if len(title) > 35:
                title = title[:35] + "…"
            lines.append(f"  • {title}")
        lines.append("")

    return "\n".join(lines).strip()


# ============================================================
# 主流程
# ============================================================

def main():
    print(f"🔍 每日AI资讯速览 - {TODAY}")
    print("=" * 45)

    # 1. 抓取所有新闻
    print("\n📡 正在抓取资讯...")
    all_items = []

    # 按顺序抓取，全部并行在各自的函数里打印状态
    all_items.extend(fetch_jiqizhixin())
    all_items.extend(fetch_ithome())
    all_items.extend(fetch_36kr())
    all_items.extend(fetch_leiphone())
    all_items.extend(fetch_hackernews())
    all_items.extend(fetch_github_trending())

    print(f"\n   共获取 {len(all_items)} 条原始资讯")

    if not all_items:
        print("   ❌ 未获取到任何资讯，退出。")
        return

    # 2. 分类整理
    print("\n📋 正在分类整理...")
    classified = classify_items(all_items)

    for cat in CATEGORY_ORDER:
        count = len(classified[cat])
        if count > 0:
            print(f"   {CATEGORY_NAMES[cat][0]} {CATEGORY_NAMES[cat][1]}: {count} 条 ✅")
        else:
            print(f"   {CATEGORY_NAMES[cat][0]} {CATEGORY_NAMES[cat][1]}: 暂无")

    total_classified = sum(len(classified[c]) for c in CATEGORY_ORDER)
    print(f"\n   共分类 {total_classified} 条有效资讯")

    # 3. 生成 Markdown 报告
    report = generate_report(all_items)

    os.makedirs("output", exist_ok=True)
    report_path = f"output/ai_news_{TODAY}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 报告已保存: {report_path}")

    # 输出报告预览
    print(f"\n{'='*45}")
    print(report[:800])
    print("...")
    print(f"{'='*45}")

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
        "icon": "https://emojicdn.elk.sh/📰",
        "isArchive": 1,
        "automaticallyCopy": 0,
    }

    print(f"\n📱 正在推送至 iPhone...")
    print(f"   标题: {title}")
    print(f"   正文预览: {body[:80]}...")
    try:
        resp = requests.post(BARK_URL, json=payload, timeout=15)
        if resp.ok:
            result = resp.json()
            print(f"   ✅ Bark 推送成功: {result}")
        else:
            print(f"   ❌ Bark 推送失败: HTTP {resp.status_code}")
            print(f"   响应: {resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ Bark 推送异常: {e}")

    print(f"\n✅ 完成! 共抓取 {len(all_items)} 条，精选 {total_classified} 条")

    return report


if __name__ == "__main__":
    main()
