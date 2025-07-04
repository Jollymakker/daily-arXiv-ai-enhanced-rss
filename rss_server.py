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
from ai.movie_daily import generate_movie_rss, router as movie_router

# 从环境变量获取配置，便于Vercel部署
DATA_DIR = os.environ.get('DATA_DIR', 'data')
DEFAULT_LANGUAGE = os.environ.get('LANGUAGE', 'Chinese')

app = FastAPI(title="arXiv RSS API", 
              description="提供arXiv论文的RSS订阅服务", 
              version="1.0.0")

db_manager = DatabaseManager()

# 确保数据库表自动创建
DatabaseManager().connect_and_create_table()

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
    title = str(item.get('title', 'Untitled'))

    authors_list = item.get('authors')
    authors = '; '.join(str(a) for a in authors_list) if authors_list else 'Anonymous'

    categories_list = item.get('categories')
    categories = ' | '.join(str(c) for c in categories_list) if categories_list else ''
    
    # Build description with simple tags
    description = [
        f"<b>Title:</b> &nbsp;{title}<br>",
        f"<b>Authors:</b>&nbsp; {authors}<br>",
        f"<b>Categories:</b> &nbsp;{categories}<br>" if categories else "",
        "<br>",
        "<b>Research Motivation:</b>&nbsp;",
        str(ai.get('motivation', 'Not provided')) + "<br>",
        "<br>",
        "<b>Methodology:</b>&nbsp;",
        str(ai.get('method', 'Not described')) + "<br>",
        "<br>",
        "<b>Key Results:</b>&nbsp;",
        str(ai.get('result', 'Not available')) + "<br>",
        "<br>",
        "<b>Conclusions:</b>&nbsp;",
        str(ai.get('conclusion', 'None drawn')) + "<br>",
        "<br>",
        "<b>Abstract:</b>&nbsp;",
        str(item.get('summary', 'No abstract available')) + "<br>"
    ]
    
    # Add comment if exists
    comment_text = item.get('comment')
    if comment_text is not None:
        description.extend([
            "<br>",
            "<b>Editorial Note:</b>&nbsp;",
            str(comment_text) + "<br>"
        ])
    
    pdf_url = str(item.get('pdf', ''))
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

    # 检查哪些条目没有AI数据
    need_enhance = []
    for item in items:
        ai = item.get('AI', {})
        # 判断AI字段是否全为空或全为None
        if not ai or all(v is None or v == '' for v in ai.values()):
            need_enhance.append(item)
    # 如果有需要增强的条目，进行AI增强并更新数据库和缓存
    if need_enhance:
        from ai.enhance import run_enhancement_process
        enhanced = run_enhancement_process(need_enhance)
        # 用增强后的数据替换原有条目
        id2enh = {d['id']: d for d in enhanced}
        for idx, item in enumerate(items):
            if item['id'] in id2enh:
                items[idx] = id2enh[item['id']]
        # 更新数据库
        db_manager.insert_data(enhanced)
        # 更新缓存
        memory_cache.set(date_str, items)
    else:
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
def generate_rss_xml(cat: Optional[str], day: int, keys: Optional[str] = None):
    dates = get_recent_dates(day)
    items = load_items_multi(dates)
        
    # 根据关键字过滤
    if keys:
        keywords = [k.strip().lower() for k in keys.split(',') if k.strip()]
        if keywords:
            items = [item for item in items if 
                     item.get('summary') and any(keyword in item['summary'].lower() for keyword in keywords)]

    if not items: # 如果没有获取到任何项目，抛出HTTP 404
        raise HTTPException(status_code=404, detail=f'未找到最近{day}天的论文。')

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
        fe.author({'name': ', '.join(str(a) for a in item.get('authors', []))})
        if 'categories' in item and isinstance(item['categories'], list):
            for c in item['categories']:
                fe.category(term=str(c))
        published_date = item.get('updated_at')
        if published_date:
            utc_published_date = published_date.astimezone(timezone.utc)
            fe.pubDate(utc_published_date)
        fe.guid(item.get('id', ''))
    return fg.rss_str(pretty=True)

@app.get('/feed', summary="获取统一的RSS源（按天或按分类）", response_description="RSS XML内容")
def rss_unified(day: int = Query(1, description="获取最近的天数"), 
                cat: Optional[str] = Query(None, description="按分类筛选"),
                keys: Optional[str] = Query(None, description="按关键字过滤摘要")):
    allowed_categories = get_allowed_categories()
    if cat and cat not in allowed_categories:
        raise HTTPException(status_code=404, detail=f"不支持的分类: {cat}. 可用分类: {', '.join(allowed_categories) if allowed_categories else '无'}")
    try:
        xml = generate_rss_xml(cat, day, keys)
        return Response(content=xml, media_type="application/xml")
    except HTTPException as e:
        raise e # 重新抛出HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成RSS失败: {e}")


@app.get('/movie_feed', summary="获取每日电影RSS", response_description="RSS XML内容")
def movie_feed():
    xml = generate_movie_rss()
    if not xml:
        raise HTTPException(status_code=404, detail="暂无每日电影数据")
    return Response(content=xml, media_type="application/xml")

app.include_router(movie_router) 