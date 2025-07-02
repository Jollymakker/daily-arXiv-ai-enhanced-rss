#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成静态RSS文件的脚本

此脚本用于生成静态RSS文件，可以在GitHub Actions中运行，
也可以在本地运行。生成的RSS文件将保存在static/rss目录下。

用法:
    python generate_rss.py [--output-dir OUTPUT_DIR] [--language LANGUAGE]

参数:
    --output-dir: 输出目录，默认为static/rss
    --language: 语言，默认为Chinese
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional, List, Dict, Any

# 导入feedgen库用于生成RSS
try:
    from feedgen.feed import FeedGenerator
except ImportError:
    print("请安装feedgen库: pip install feedgen")
    sys.exit(1)


# 常量定义
DATA_DIR = 'data'

# 从rss_server.py提取的函数
def get_allowed_categories():
    """获取允许的分类列表"""
    cat_env = os.environ.get('ARXIV_RSS_CATEGORIES', '').strip()
    if not cat_env:
        return set()
    return set([c.strip() for c in cat_env.split(',') if c.strip()])

def get_jsonl_by_date(date_str: str, lang: str = 'Chinese'):
    """根据日期获取JSONL文件路径"""
    fname = f"{date_str}_AI_enhanced_{lang}.jsonl"
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f'未找到数据文件: {path}')
    return path

def format_rss_time(dt_str):
    """格式化RSS时间"""
    # 处理ISO格式的时间字符串
    if 'T' in dt_str and 'Z' in dt_str:
        dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%SZ')
    # 处理日期格式的字符串 (YYYY-MM-DD)
    else:
        dt = datetime.strptime(dt_str, '%Y-%m-%d')
    # 添加UTC时区信息
    return dt.replace(tzinfo=timezone.utc)

def build_description(item):
    """构建RSS描述
    
    Args:
        item: 包含论文元数据和AI分析的字典
        
    Returns:
        str: 使用基本HTML标签格式化的描述
    """
    # 提取数据
    ai = item.get('AI', {})
    title = item.get('title', 'Untitled')
    authors = '; '.join(item.get('authors', ['Anonymous']))
    categories = ' | '.join(item.get('categories', []))
    
    # 使用简单标签构建描述
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
    
    # 如果存在评论则添加
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
    
    # 连接并移除空行
    return ''.join(filter(None, description))

def load_items(date_str: str, lang: str = 'Chinese'):
    """加载指定日期的数据项"""
    jsonl_path = get_jsonl_by_date(date_str, lang)
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def get_recent_dates(n=30):
    """获取最近n天的日期列表"""
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n)]

def load_items_multi(dates, lang: str = 'Chinese'):
    """加载多个日期的数据项"""
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

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="生成静态RSS文件")
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="static/rss", 
        help="输出目录，默认为static/rss"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default=os.environ.get("LANGUAGE", "Chinese"), 
        help="语言，默认为环境变量LANGUAGE或Chinese"
    )
    return parser.parse_args()

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def generate_all_rss(output_dir, language):
    """生成所有RSS文件
    
    Args:
        output_dir: 输出目录
        language: 语言
    """
    print(f"开始生成RSS文件，输出目录: {output_dir}, 语言: {language}")
    
    # 确保输出目录存在
    ensure_dir(output_dir)
    
    # 生成所有分类的RSS
    print("生成所有分类的RSS文件...")
    xml = generate_rss_xml(None, None, language)
    output_path = os.path.join(output_dir, "all.xml")
    with open(output_path, "wb") as f:
        f.write(xml)
    print(f"已生成: {output_path}")
    
    # # 获取环境变量中的分类，如果没有设置，则使用默认值
    # categories_str = os.environ.get("CATEGORIES", "cs.CL,cs.CV,cs.AI")
    # categories = [cat.strip() for cat in categories_str.split(",") if cat.strip()]
    
    # # 为每个分类生成RSS
    # for cat in categories:
    #     print(f"生成分类 {cat} 的RSS文件...")
    #     try:
    #         xml = generate_rss_xml(cat, None, language)
    #         # 将分类名中的点替换为下划线，以便于文件系统使用
    #         safe_cat = cat.replace(".", "_")
    #         output_path = os.path.join(output_dir, f"{safe_cat}.xml")
    #         with open(output_path, "wb") as f:
    #             f.write(xml)
    #         print(f"已生成: {output_path}")
    #     except Exception as e:
    #         print(f"生成分类 {cat} 的RSS文件时出错: {e}")
    
    print("RSS文件生成完成！")


def main():
    """主函数"""
    args = parse_args()
    generate_all_rss(args.output_dir, args.language)


if __name__ == "__main__":
    main()