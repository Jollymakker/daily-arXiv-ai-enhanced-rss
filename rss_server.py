import os
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from feedgen.feed import FeedGenerator
from typing import Optional
from functools import lru_cache
from scheduler.index import DailyArXivProcessor
from api.database import DatabaseManager
from utils.cache import memory_cache # 从新文件导入缓存实例

# 从环境变量获取配置，便于Vercel部署
DATA_DIR = os.environ.get('DATA_DIR', 'data')
DEFAULT_LANGUAGE = os.environ.get('LANGUAGE', 'Chinese')

app = FastAPI(title="arXiv RSS API", 
              description="提供arXiv论文的RSS订阅服务", 
              version="1.0.0")

db_manager = DatabaseManager()

# 获取可用分类
@lru_cache(maxsize=1)
def get_allowed_categories():
    cat_env = os.environ.get('ARXIV_RSS_CATEGORIES', '').strip()
    if not cat_env:
        return set()
    return set([c.strip() for c in cat_env.split(',') if c.strip()])

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

def load_items(date_str: str, category: Optional[str] = None) -> list:
    # 尝试从缓存中获取数据
    cached_items = memory_cache.get(date_str)
    if cached_items is not None:
        return cached_items

    # 如果缓存中没有，则从数据库获取
    items = db_manager.get_papers_by_date(date_str, category)
    if not items:
        # 如果数据库中没有数据，也将其缓存为空列表以避免重复查询
        memory_cache.set(date_str, [])
        return []
    
    # 将获取的数据存入缓存
    memory_cache.set(date_str, items)
    return items

def get_recent_dates(n=30):
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n)]

def load_items_multi(dates):
    all_items = []
    seen_ids = set()
    for date_str in dates:
        # 从数据库/缓存获取数据
        items = load_items(date_str)
        for item in items:
            pid = item.get('id')
            if pid and pid not in seen_ids:
                all_items.append(item)
                seen_ids.add(pid)
    return all_items

@lru_cache(maxsize=128)
def generate_rss_xml(cat: Optional[str], day: int):
    dates = get_recent_dates(day)
    items = load_items_multi(dates)
        
    
    if not items: # 如果没有获取到任何项目，抛出HTTP 404
        raise HTTPException(status_code=404, detail=f'未找到 {date_str} 或最近{day}天的论文。')

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
    
    # 如果指定了类别但没有找到相关项目，也应该抛出404
    if cat is not None and not feed_items:
        raise HTTPException(status_code=404, detail=f'未找到分类 {cat} 的论文。')

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
        published_date = item.get('updated_at')
        if published_date:
            utc_published_date = published_date.astimezone(timezone.utc)
            fe.pubDate(utc_published_date)
        fe.guid(item.get('id', ''))
    return fg.rss_str(pretty=True)

@app.get('/feed/day/{day}', summary="获取所有分类的RSS源", response_description="RSS XML内容")
def rss_all(day: int):
    try:
        xml = generate_rss_xml(None, day)
        return Response(content=xml, media_type="application/xml")
    except HTTPException as e:
        raise e # 重新抛出HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成RSS失败: {e}")

@app.get('/feed/cat/{cat}', summary="获取特定分类的RSS源", response_description="RSS XML内容")
def rss_cat(cat: str):
    allowed_categories = get_allowed_categories()
    if cat not in allowed_categories:
        raise HTTPException(status_code=404, detail=f"不支持的分类: {cat}. 可用分类: {', '.join(allowed_categories) if allowed_categories else '无'}")
    try:
        xml = generate_rss_xml(cat, 7)
        return Response(content=xml, media_type="application/xml")
    except HTTPException as e:
        raise e # 重新抛出HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成RSS失败: {e}")
