#!/usr/bin/env python3
"""
每日AI资讯速览 - GitHub Actions 版 v2.1
自动抓取多个新闻源（36氪、IT之家、少数派、Hacker News、GitHub），
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
TIMEOUT = 25

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


def safe_text(el):
    """安全获取 XML 元素文本"""
    if el is not None and el.text:
        return el.text.strip()
    return ""


def parse_rss(url: str, source_name: str, max_items: int = 20) -> list:
    """通用 RSS 解析器"""
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not resp.ok:
            print(f"  [WARN] {source_name} RSS 请求失败: HTTP {resp.status_code}")
            return items
        root = ElementTree.fromstring(resp.content)
        feed_type = "rss" if root.tag == "rss" else "atom"

        if feed_type == "rss":
            channel = root.find("channel")
            entries = channel.findall("item") if channel is not None else []
        else:  # atom
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        for entry in entries[:max_items]:
            if feed_type == "rss":
                title = clean_html(safe_text(entry.find("title")))
                desc_el = entry.find("description")
                summary = clean_html(safe_text(desc_el)) if desc_el is not None else ""
                link_el = entry.find("link")
                link = safe_text(link_el) if link_el is not None else ""
            else:
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                title = clean_html(safe_text(title_el)) if title_el is not None else ""
                summary_el = entry.find("{http://www.w3.org/2005/Atom}summary")
                summary = clean_html(safe_text(summary_el)) if summary_el is not None else ""
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""

            if title:
                items.append({
                    "title": title,
                    "summary": summary,
                    "source": source_name,
                    "url": link
                })
    except ElementTree.ParseError as e:
        print(f"  [WARN] {source_name} XML 解析失败: {e}")
    except Exception as e:
        print(f"  [WARN] {source_name} 抓取失败: {e}")
    return items


# ============================================================
# AI 相关关键词（用于过滤非AI类新闻源）
# ============================================================

AI_KEYWORDS = [
    # 中文
    "人工智能", "大模型", "机器学习", "深度学", "神经网络", "自然语言",
    "计算机视觉", "强化学习", "AI", "ai", "GPT", "gpt", "Claude", "claude",
    "DeepSeek", "deepseek", "ChatGPT", "chatgpt", "Gemini", "gemini",
    "Llama", "llama", "Mistral", "mistral", "Stable Diffusion",
    "智能", "模型", "算法", "算力", "芯片", "机器人", "自动驾驶",
    "具身", "人形", "robot", "robotics", "机器学",
    "AI Infra", "AI infra", "ai infra",
    "开源", "大模型应用", "AI应用",
    "融资", "投资", "估值", "IPO", "上市", "募资",
    "英伟达", "NVIDIA", "nvidia", "AMD", "amd", "Intel", "intel",
    "OpenAI", "openai", "Anthropic", "anthropic", "Google AI",
    "百度", "腾讯", "阿里", "字节", "华为",
    "安全", "隐私", "伦理", "监管", "政策",
    "Transformer", "transformer", "Diffusion", "diffusion",
    "GPU", "gpu", "TPU", "tpu", "NPU", "npu", "HBM", "hbm",
    "半导体", "台积电", "TSMC", "tsmc",
    "AI PC", "AI手机", "AI硬件",
    "AI 搜索", "AI搜索", "AI搜索", "AI 编程", "AI编程",
    "大语言模型", "多模态", "多模态模型",
    "AI 视频", "AI视频", "AI 图片", "AI图片", "AI 音乐", "AI音乐",
    "AI 助手", "AI助手", "AI 代理", "AI代理", "AI Agent",
    "AI 眼镜", "AI眼镜", "智能穿戴",
    "数据中", "数据中心", "AI 数据",
    "AI 安全", "AI伦理", "AI监管",
    "AI 编程", "AI代码", "Copilot",
    "AI 医疗", "AI医疗", "AI 制药", "AI制药",
    "AI 教育", "AI教育", "AI 金融", "AI金融",
    "智能化", "数字化", "数字化转型",
    "AI 芯片", "AI芯片", "AI 算力", "AI算力",
    "云服务", "云计算", "边缘计算",
    "AI 创业", "AI创业", "AI 公司", "AI公司",
    "AI 工具", "AI工具", "AI 产品", "AI产品",
    "AI 平台", "AI平台", "AI 模型", "AI模型",
    "AI 训练", "AI训练", "AI 推理", "AI推理",
    "AI 生态", "AI生态", "AI 产业", "AI产业",
    "AI 人才", "AI人才", "AI 团队", "AI团队",
    "AI 技术", "AI技术", "AI 创新", "AI创新",
    "AI 发展", "AI发展", "AI 趋势", "AI趋势",
    "AI 大会", "AI大会", "AI 峰会", "AI峰会",
    "AI 报告", "AI报告", "AI 白皮书", "AI白皮书",
    "AI 标准", "AI标准", "AI 法规", "AI法规",
    "AI 投资", "AI投资", "AI 融资", "AI融资",
    "AI 项目", "AI项目", "AI 开源", "AI开源",
    "AI 创业公司", "AI创业公司", "AI 独角兽", "AI独角兽",
    "AI 应用", "AI应用", "AI 场景", "AI场景",
    "AI 能力", "AI能力", "AI 平台", "AI平台",
    "AI 基础设施", "AI基础设施", "AI 基础模型", "AI基础模型",
    "AI 数据", "AI数据", "AI 算法", "AI算法",
    "AI 框架", "AI框架", "AI 工具链", "AI工具链",
    "AI 服务", "AI服务", "AI 解决方案", "AI解决方案",
    "GPT-", "gpt-", "Claude ", "claude ", "Gemini ", "gemini ",
    "Llama ", "llama ", "Mistral ", "mistral ",
    "Sora", "sora", "视频生成", "文生图", "图生文",
    "AI 语音", "AI语音", "语音识别", "语音合成",
    "AI 翻译", "AI翻译", "机器翻译",
    "AI 推荐", "AI推荐", "推荐系统",
    "AI 搜索", "AI搜索", "搜索算法",
    "AI 广告", "AI广告", "广告算法",
    "AI 内容", "AI内容", "内容生成",
    "AI 创作", "AI创作", "AIGC",
    "AI 社交", "AI社交", "社交算法",
    "AI 游戏", "AI游戏", "游戏AI",
    "AI 电商", "AI电商", "电商算法",
    "AI 营销", "AI营销", "营销算法",
    "AI 运营", "AI运营", "运营算法",
    "AI 客服", "AI客服", "智能客服",
    "AI 风控", "AI风控", "风控算法",
    "AI 安全", "AI安全", "安全算法",
    "AI 自动驾驶", "自动驾驶", "无人驾驶",
    "AI 机器人", "机器人", "机器狗", "人形机器人",
    "AI 芯片", "芯片", "GPU", "gpu",
    "AI 算力", "算力",
    "AI 企业", "AI企业",
    "AI 市场", "AI市场",
    "AI 行业", "AI行业",
    "AI 时代", "AI时代",
    "AI 浪潮", "AI浪潮",
    "AI 革命", "AI革命",
    "AI 改变", "AI改变",
    "AI 颠覆", "AI颠覆",
    "AI 冲击", "AI冲击",
    "AI 影响", "AI影响",
    "AI 未来", "AI未来",
    "AI 世界", "AI世界",
    "AI 布局", "AI布局",
    "AI 竞争", "AI竞争",
    "AI 合作", "AI合作",
    "AI 联盟", "AI联盟",
    "AI 战略", "AI战略",
    "AI 转型", "AI转型",
    "AI 升级", "AI升级",
]


def has_ai_keywords(text: str) -> bool:
    """检查文本是否包含 AI 相关关键词"""
    return any(kw in text for kw in AI_KEYWORDS)


# ============================================================
# 各数据源抓取函数
# ============================================================

def fetch_36kr():
    """36氪 - 优质中文科技商业媒体 (RSS)"""
    print("  📡 36氪...", end=" ", flush=True)
    items = parse_rss("https://36kr.com/feed", "36氪", max_items=25)
    print(f"✓ {len(items)} 条")
    return items


def fetch_ithome():
    """IT之家 - 综合科技资讯 (RSS)，需要AI关键词过滤"""
    print("  📡 IT之家...", end=" ", flush=True)
    all_items = parse_rss("https://www.ithome.com/rss/", "IT之家", max_items=25)
    # IT之家是综合科技站，只保留AI相关内容
    ai_items = [it for it in all_items if has_ai_keywords(it["title"] + " " + it["summary"])]
    print(f"✓ {len(all_items)} 原始 / {len(ai_items)} AI相关")
    return ai_items


def fetch_sspai():
    """少数派 - 效率工具/科技生活 (RSS)"""
    print("  📡 少数派...", end=" ", flush=True)
    items = parse_rss("https://sspai.com/feed", "少数派", max_items=15)
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
        top_ids = resp.json()[:50]
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
                    "rlhf", "alignment", "agi", "llama", "mistral",
                    "computer vision", "nlp", "reinforcement learning",
                    "generative", "copilot", "embedding", "vector database",
                    "rag", "fine-tun", "sora", "stable diffusion",
                    "reasoning", "chain-of-thought",
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
        else:
            print(f"✗ HTTP {resp.status_code}")
            return items
        print(f"✓ {len(items)} 条")
    except Exception as e:
        print(f"✗ {e}")
    return items


# ============================================================
# 分类器 - 关键词匹配（严格版）
# ============================================================

def classify_news(item):
    """通过关键词将新闻分到7个维度"""
    title = item["title"]
    summary = item.get("summary", "")
    text = title + " " + summary
    t = text.lower()

    # 1. 🔥 核心头条 - 涉及巨头重大变动/里程碑/新品
    if any(kw in t for kw in [
        "openai", "anthropic", "google ai", "meta ai", "microsoft ai",
        "马斯克", "xai", "spacex", "合并", "收购",
        "万亿", "重磅", "首次", "里程碑",
        "apple intelligence", "谷歌", "百度", "腾讯", "阿里", "字节",
        "gemini", "gpt-5", "gpt5", "claude 4", "llama 4",
        "deepseek", "超越", "突破", "发布 ai",
        "ai 发布", "ai 新品", "ai 助手", "ai 搜索",
        "对话即", "大模型", "通用人工智能",
        "ai 代理", "ai agent", "ai 编程",
        "中国版", "ai 模型", "新模型",
        "open ai", "ai 创业公司",
        "最新", "更新", "升级 ai",
    ]):
        # 确保确实是 AI 相关
        if has_ai_keywords(t):
            return "headlines"

    # 2. 💰 融资动态
    if any(kw in t for kw in [
        "融资", "估值", "投资", "ipo", "上市", "募资",
        "funding", "valuation", "invest",
        "天使轮", "a轮", "b轮", "c轮", "战略投资",
        "出资", "亿元", "融资额", "领投", "跟投",
        "种子轮", "pre-", "pre ",
    ]):
        if has_ai_keywords(t):
            return "funding"

    # 3. 🏭 政策标准
    if any(kw in t for kw in [
        "政策", "标准", "法规", "监管", "治理", "工信部",
        "网信办", "regulation", "policy", "立法", "法案",
        "白宫", "欧盟", "中美", "出口管制", "限制",
        "合规", "备案", "安全评估",
        "ai 安全准则", "ai 伦理", "ai 监管",
        "数据安全", "个人信息", "数据出境",
        "ai 法案", "ai 治理",
    ]):
        return "policies"

    # 4. 💻 芯片算力
    if any(kw in t for kw in [
        "芯片", "gpu", "算力", "半导体", "hbm", "英伟达",
        "nvidia", "amd", "intel", "台积电", "处理器",
        "存储", "asic", "tpu", "npu", "soc",
        "寒武纪", "海光", "龙芯", "昇腾", "鲲鹏",
        "封装", "光刻", "晶圆", "制程",
        "数据中心", "云计算", "云服务",
    ]):
        return "chips"

    # 5. 🤖 机器人具身智能
    if any(kw in t for kw in [
        "机器人", "具身", "人形", "robot", "humanoid",
        "无人机", "evtol", "机器狗",
        "宇树", "特斯拉机器人", "optimu", "擎天柱",
        "波士顿动力", "figure", "机器臂", "灵巧手",
        "自动驾驶", "无人驾驶",
    ]):
        return "robots"

    # 6. 📊 产业链经济
    if any(kw in t for kw in [
        "产业链", "经济", "市场", "etf", "股市", "资本",
        "财报", "营收", "利润", "增长", "景气", "市值",
        "股价", "下跌", "上涨", "降息", "通胀",
        "供应链", "制造业", "出海", "关税",
        "生态", "产业", "行业报告",
    ]):
        if has_ai_keywords(t):
            return "economy"

    # 7. 🛡️ 安全治理
    if any(kw in t for kw in [
        "安全", "伦理", "偏见", "歧视", "幻觉", "隐私",
        "安全准则", "可信", "风险", "有害", "滥用",
        "safety", "alignment", "jailbreak", "对抗",
        "投毒", "深度伪造", "deepfake",
        "数据泄露", "网络攻击", "黑客",
    ]):
        if has_ai_keywords(t) or any(k in t for k in ["数据安", "隐私", "网络安"]):
            return "safety"

    # Fallback: 如果标题明确包含 AI 关键词但未匹配上面分类，作为核心头条
    if has_ai_keywords(t):
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

    for item in all_items:
        cat = classify_news(item)
        if cat in classified:
            classified[cat].append(item)

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

    all_items.extend(fetch_36kr())
    all_items.extend(fetch_ithome())
    all_items.extend(fetch_sspai())
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

    if total_classified == 0:
        print("   ❌ 没有可分类的资讯，但会尝试推送原始数据。")
        # 使用所有原始数据生成报告
        classified = {k: [] for k in CATEGORY_ORDER}
        for item in all_items[:10]:
            classified["headlines"].append(item)

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

    payload = {
        "title": title,
        "body": body,
        "group": "AI资讯",
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
