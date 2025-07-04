import os
import json
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.responses import Response
from api.database import DatabaseManager
import requests
from fastapi import APIRouter

def get_movie_data_path():
    return os.environ.get('MOVIE_DATA_PATH', 'data/daily_movie.json')

def load_daily_movie():
    db = DatabaseManager()
    return db.get_all_daily_movies()

def generate_movie_rss():
    movies = load_daily_movie()
    if not movies:
        return None

    fg = FeedGenerator()
    fg.title('每日电影推荐')
    fg.link(href='/movie_feed', rel='self')
    fg.description('每日精选电影推荐')

    for movie in movies:
        fe = fg.add_entry()
        fe.title(movie.get('mov_title', '无标题'))
        fe.link(href=movie.get('mov_link', ''))
        fe.description(
            f"<b>每日一言：</b>{movie.get('daily_word', '')}<br>"
            f"<b>简介：</b>{movie.get('mov_intro', '')}<br>"
            f"<b>导演：</b>{movie.get('mov_director', '')}<br>"
            f"<b>年份：</b>{movie.get('mov_year', '')}<br>"
            f"<b>地区：</b>{movie.get('mov_area', '')}<br>"
            f"<b>类型：</b>{'、'.join(movie.get('mov_type', []))}<br>"
            f"<b>评分：</b>{movie.get('mov_rating', '')}<br>"
            f"<img src='{movie.get('mov_pic', '')}' width='200'/><br>"
            f"<b>金句：</b>{movie.get('mov_text', '')}<br>"
        )
        fe.guid(movie.get('mov_id', ''))
        pub_time = movie.get('gettime', 0)
        if pub_time:
            fe.pubDate(datetime.fromtimestamp(pub_time, tz=timezone.utc))
    return fg.rss_str(pretty=True)

router = APIRouter()

@router.get('/fetch_movie_daily', summary="手动抓取并保存每日电影数据")
def fetch_movie_daily():
    url = 'https://www.cikeee.com/api?app_key=pub_23020990025'
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return {"success": False, "msg": f"请求失败: {resp.status_code}"}
    data = resp.json()
    db = DatabaseManager()
    ok = db.insert_daily_movie(data)
    if ok:
        return {"success": True, "msg": "已写入数据库", "mov_id": data.get('mov_id')}
    else:
        return {"success": False, "msg": "写入数据库失败"}
