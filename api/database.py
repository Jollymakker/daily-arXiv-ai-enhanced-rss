import os
import psycopg
import logging
from typing import Optional

class DatabaseManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.conn_string = os.environ.get("DATABASE_URL")


    def connect_and_create_table(self):
        if not self.conn_string:
            return False
        try:
            with psycopg.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TIME ZONE 'Asia/Shanghai'")
                    # 创建 arxiv_papers 表
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS arxiv_papers (
                            id TEXT PRIMARY KEY,
                            categories TEXT[],
                            pdf TEXT,
                            abs TEXT,
                            authors TEXT[],
                            title TEXT,
                            comment TEXT,
                            summary TEXT,
                            ai_tldr TEXT,
                            ai_motivation TEXT,
                            ai_method TEXT,
                            ai_result TEXT,
                            ai_conclusion TEXT,
                            inserted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    # 创建 daily_movie 表
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS daily_movie (
                            mov_id TEXT PRIMARY KEY,
                            gettime BIGINT,
                            daily_word TEXT,
                            mov_title TEXT,
                            mov_text TEXT,
                            mov_link TEXT,
                            mov_rating TEXT,
                            mov_director TEXT,
                            mov_year INT,
                            mov_area TEXT,
                            mov_type TEXT[],
                            mov_pic TEXT,
                            mov_intro TEXT
                        )
                    """)
                    conn.commit()
                    self.logger.info("数据库表 'arxiv_papers' 和 'daily_movie' 已就绪。")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接或创建表失败: {e}")
            return False

    def insert_data(self, data: list):
        if not self.conn_string:
            self.logger.error("数据库连接字符串无效，跳过数据插入。")
            return 0
        inserted_count = 0
        try:
            with psycopg.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TIME ZONE 'Asia/Shanghai'")
                    for item in data:
                        ai_data = item.get('AI', {})
                        try:
                            cur.execute("""
                                INSERT INTO arxiv_papers (
                                    id, categories, pdf, abs, authors, title, comment, summary,
                                    ai_tldr, ai_motivation, ai_method, ai_result, ai_conclusion, inserted_at, updated_at
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                                ON CONFLICT (id) DO UPDATE SET
                                    title = EXCLUDED.title,
                                    summary = EXCLUDED.summary,
                                    authors = EXCLUDED.authors,
                                    categories = EXCLUDED.categories,
                                    pdf = EXCLUDED.pdf,
                                    abs = EXCLUDED.abs,
                                    comment = EXCLUDED.comment,
                                    ai_tldr = EXCLUDED.ai_tldr,
                                    ai_motivation = EXCLUDED.ai_motivation,
                                    ai_method = EXCLUDED.ai_method,
                                    ai_result = EXCLUDED.ai_result,
                                    ai_conclusion = EXCLUDED.ai_conclusion,
                                    updated_at = NOW()
                            """, (
                                item.get('id'),
                                item.get('categories'), 
                                item.get('pdf'),
                                item.get('abs'),
                                item.get('authors'),
                                item.get('title'),
                                item.get('comment'),
                                item.get('summary'),
                                ai_data.get('tldr'),
                                ai_data.get('motivation'),
                                ai_data.get('method'),
                                ai_data.get('result'),
                                ai_data.get('conclusion')
                            ))
                            if cur.rowcount > 0:
                                inserted_count += 1
                        except Exception as insert_e:
                            self.logger.error(f"插入或更新ID {item.get('id')} 时出错: {insert_e}")
                conn.commit()
            self.logger.info(f"数据库存储完成，成功插入 {inserted_count} 条数据。")
            return inserted_count
        except Exception as e:
            self.logger.error(f"数据库操作失败: {e}")
            return 0

    def get_papers_by_date(self, date_str: str, category: Optional[str] = None) -> list:
        if not self.conn_string:
            self.logger.error("数据库连接字符串无效，无法获取数据。")
            return []
        
        papers = []
        try:
            with psycopg.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    # Set the session timezone to Asia/Shanghai (Beijing time)
                    cur.execute("SET TIME ZONE 'Asia/Shanghai'")

                    # 构建查询
                    query = """
                        SELECT id, categories, pdf, abs, authors, title, comment, summary, updated_at,
                               ai_tldr, ai_motivation, ai_method, ai_result, ai_conclusion
                        FROM arxiv_papers
                        WHERE inserted_at::date = %s
                    """
                    params = [date_str]

                    if category:
                        query += " AND %s = ANY(categories)"
                        params.append(category)
                    
                    cur.execute(query, params)
                    columns = [desc[0] for desc in cur.description]
                    for row in cur.fetchall():
                        item = dict(zip(columns, row))
                        # 确保 categories 是列表，并处理 AI 字段
                        if item.get('categories') and not isinstance(item['categories'], list):
                            item['categories'] = item['categories'].strip('{}').split(',') if item['categories'] else []
                        elif item.get('categories') is None:
                            item['categories'] = []
                        
                        ai_data = {
                            'tldr': item.pop('ai_tldr'),
                            'motivation': item.pop('ai_motivation'),
                            'method': item.pop('ai_method'),
                            'result': item.pop('ai_result'),
                            'conclusion': item.pop('ai_conclusion')
                        }
                        item['AI'] = ai_data
                        papers.append(item)
            self.logger.info(f"从数据库获取 {len(papers)} 条数据，日期: {date_str}, 类别: {category}")
            return papers
        except Exception as e:
            self.logger.error(f"从数据库获取数据失败: {e}")
            return [] 

    def insert_daily_movie(self, data: dict):
        if not self.conn_string:
            self.logger.error("数据库连接字符串无效，跳过电影数据插入。")
            return 0
        try:
            with psycopg.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TIME ZONE 'Asia/Shanghai'")
                    cur.execute("""
                        INSERT INTO daily_movie (
                            mov_id, gettime, daily_word, mov_title, mov_text, mov_link, mov_rating, mov_director, mov_year, mov_area, mov_type, mov_pic, mov_intro
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (mov_id) DO UPDATE SET
                            gettime = EXCLUDED.gettime,
                            daily_word = EXCLUDED.daily_word,
                            mov_title = EXCLUDED.mov_title,
                            mov_text = EXCLUDED.mov_text,
                            mov_link = EXCLUDED.mov_link,
                            mov_rating = EXCLUDED.mov_rating,
                            mov_director = EXCLUDED.mov_director,
                            mov_year = EXCLUDED.mov_year,
                            mov_area = EXCLUDED.mov_area,
                            mov_type = EXCLUDED.mov_type,
                            mov_pic = EXCLUDED.mov_pic,
                            mov_intro = EXCLUDED.mov_intro
                    """,
                    (
                        data.get('mov_id'),
                        data.get('gettime'),
                        data.get('daily_word'),
                        data.get('mov_title'),
                        data.get('mov_text'),
                        data.get('mov_link'),
                        data.get('mov_rating'),
                        data.get('mov_director'),
                        data.get('mov_year'),
                        data.get('mov_area'),
                        data.get('mov_type'),
                        data.get('mov_pic'),
                        data.get('mov_intro')
                    ))
                conn.commit()
            self.logger.info(f"电影数据 {data.get('mov_id')} 插入/更新成功。")
            return 1
        except Exception as e:
            self.logger.error(f"插入电影数据失败: {e}")
            return 0

    def get_all_daily_movies(self):
        if not self.conn_string:
            self.logger.error("数据库连接字符串无效，无法获取电影数据。"); return []
        try:
            with psycopg.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TIME ZONE 'Asia/Shanghai'")
                    cur.execute("SELECT * FROM daily_movie ORDER BY gettime DESC")
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"获取全部电影数据失败: {e}")
            return [] 