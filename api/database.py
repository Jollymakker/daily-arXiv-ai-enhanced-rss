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
                    conn.commit()
                    self.logger.info("数据库表 'arxiv_papers' 已就绪。")
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