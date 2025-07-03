import os
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from feedgen.feed import FeedGenerator
from typing import Optional
from functools import lru_cache
from apscheduler.schedulers.background import BackgroundScheduler  # 改用 APScheduler
import subprocess
from scheduler.index import DailyArXivPipeline

# 从环境变量获取配置，便于Vercel部署
DATA_DIR = os.environ.get('DATA_DIR', 'data')
DEFAULT_LANGUAGE = os.environ.get('LANGUAGE', 'Chinese')

app = FastAPI(title="arXiv RSS API", 
              description="提供arXiv论文的RSS订阅服务", 
              version="1.0.0")

# 初始化 APScheduler
scheduler = BackgroundScheduler()

# 定义定时任务
def my_daily_task():
    print("✅ 定时任务执行：每 10 秒运行一次")

def my_scheduled_task():
    print("✅ 定时任务执行：每 10 秒运行一次")
    result = subprocess.run(["python", "-m","scheduler.index"])
    if result.returncode == 0:
        print("定时任务成功")
    else:
        print("定时任务失败")

# 启动调度器（在 FastAPI 启动时运行）
@app.on_event("startup")
async def startup_event():
    scheduler.add_job(my_scheduled_task, "interval", seconds=10)
    scheduler.add_job(
        my_daily_task,
        trigger="cron",
        hour=3,     
        minute=0    
    )
    scheduler.start()

# 关闭调度器（在 FastAPI 关闭时运行）
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

# 获取可用分类
@lru_cache(maxsize=1)
def get_allowed_categories():
    cat_env = os.environ.get('ARXIV_RSS_CATEGORIES', '').strip()
    if not cat_env:
        return set()
    return set([c.strip() for c in cat_env.split(',') if c.strip()])

def get_jsonl_by_date(date_str: str, lang: str = 'Chinese'):
    fname = f"{date_str}_AI_enhanced_{lang}.jsonl"
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f'未找到数据文件: {path}')
    return path

def format_rss_time(dt_str):
    # 处理ISO格式的时间字符串
    if 'T' in dt_str and 'Z' in dt_str:
        dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%SZ')
    # 处理日期格式的字符串 (YYYY-MM-DD)
    else:
        dt = datetime.strptime(dt_str, '%Y-%m-%d')
    # 添加UTC时区信息
    return dt.replace(tzinfo=timezone.utc)

def build_description(item):
    """Build a scholarly RSS description with simple HTML tags
    
    Args:
        item: Dictionary containing paper metadata and AI analysis
        
    Returns:
        str: Formatted description with basic HTML tags
    """
    # Extract data
    ai = item.get('AI', {})
    title = item.get('title', 'Untitled')
    authors = '; '.join(item.get('authors', ['Anonymous']))
    categories = ' | '.join(item.get('categories', []))
    
    # Build description with simple tags
    description = [
        f"<b>Title:</b> &nbsp;{title}<br>",
        f"<b>Authors:</b>&nbsp; {authors}<br>",
        f"<b>Categories:</b> &nbsp;{categories}<br>" if categories else "",
        "<br>",
        "<b>Research Motivation:</b>&nbsp;",
        ai.get('motivation', 'Not provided') + "<br>",
        "<br>",
        "<b>Methodology:</b>&nbsp;",
        ai.get('method', 'Not described') + "<br>",
        "<br>",
        "<b>Key Results:</b>&nbsp;",
        ai.get('result', 'Not available') + "<br>",
        "<br>",
        "<b>Conclusions:</b>&nbsp;",
        ai.get('conclusion', 'None drawn') + "<br>",
        "<br>",
        "<b>Abstract:</b>&nbsp;",
        item.get('summary', 'No abstract available') + "<br>"
    ]
    
    # Add comment if exists
    if item.get('comment'):
        description.extend([
            "<br>",
            "<b>Editorial Note:</b>&nbsp;",
            item['comment'] + "<br>"
        ])
    
    pdf_url = item.get('pdf', '')
    if pdf_url:
        description.extend([
            "<br>",
            "<b>Resources:</b>&nbsp;",
            f'<a href="{pdf_url}">PDF</a>'
        ])
    
    # Join and remove empty lines
    return ''.join(filter(None, description))

def load_items(date_str: str, lang: str = 'Chinese'):
    jsonl_path = get_jsonl_by_date(date_str, lang)
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def get_recent_dates(n=30):
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n)]

def load_items_multi(dates, lang: str = 'Chinese'):
    all_items = []
    seen_ids = set()
    for date_str in dates:
        try:
            items = load_items(date_str, lang)
            for item in items:
                pid = item.get('id')
                if pid and pid not in seen_ids:
                    item["published"] = date_str
                    all_items.append(item)
                    seen_ids.add(pid)
        except FileNotFoundError:
            continue
    return all_items

@lru_cache(maxsize=128)
def generate_rss_xml(cat: Optional[str], date_str: Optional[str], lang: str = 'Chinese'):
    if date_str:
        items = load_items(date_str, lang)
    else:
        dates = get_recent_dates(30)
        items = load_items_multi(dates, lang)
    fg = FeedGenerator()
    if cat is None:
        fg.title(f'arXiv 每日论文')
        fg.link(href=f'/feed', rel='self')
        fg.description(f'arXiv 每日论文总源')
        feed_items = items
    else:
        fg.title(f'arXiv 每日论文（{cat}）')
        fg.link(href=f'/feed/{cat}', rel='self')
        fg.description(f'arXiv 每日论文分类源：{cat}')
        feed_items = []
        for item in items:
            cats = item.get('categories')
            if cats and isinstance(cats, list) and cat in cats:
                feed_items.append(item)
    for item in feed_items:
        fe = fg.add_entry()
        ai = item.get('AI', {})
        zh = ai.get('tldr')
        title = item.get('title')
        if not title:
            continue
        if not zh:
            zh = '\n'.join([f"{k}: {v}" for k, v in ai.items()])
        fe.title(zh if zh else item.get('title', ''))
        fe.link(href=item.get('abs', ''))
        fe.description(build_description(item))
        fe.author({'name': ', '.join(item.get('authors', []))})
        if 'categories' in item and isinstance(item['categories'], list):
            for c in item['categories']:
                fe.category(term=c)
        # 确保日期有时区信息
        published_date = item.get('published')
        if published_date:
            fe.pubDate(format_rss_time(published_date))
        fe.guid(item.get('id', ''))
    return fg.rss_str(pretty=True)

@app.get('/feed', summary="获取所有分类的RSS源", response_description="RSS XML内容")
def rss_all(date: Optional[str] = Query(None, description="指定日期 (YYYY-MM-DD)，默认为最近30天"), 
           lang: Optional[str] = Query(DEFAULT_LANGUAGE, description="语言设置，默认为环境变量LANGUAGE或Chinese")):
    try:
        xml = generate_rss_xml(None, date, lang)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(content=xml, media_type='application/xml')

@app.get('/feed/{cat}', summary="获取特定分类的RSS源", response_description="RSS XML内容")
def rss_cat(cat: str, 
           date: Optional[str] = Query(None, description="指定日期 (YYYY-MM-DD)，默认为最近30天"), 
           lang: Optional[str] = Query(DEFAULT_LANGUAGE, description="语言设置，默认为环境变量LANGUAGE或Chinese")):
    allowed = get_allowed_categories()
    if allowed and cat not in allowed:
        raise HTTPException(status_code=404, detail=f'分类 {cat} 未被允许')
    try:
        xml = generate_rss_xml(cat, date, lang)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(content=xml, media_type='application/xml')
