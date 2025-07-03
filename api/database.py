import os
import psycopg
import logging

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
                            ai_conclusion TEXT
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
                    for item in data:
                        ai_data = item.get('AI', {})
                        try:
                            cur.execute("""
                                INSERT INTO arxiv_papers (
                                    id, categories, pdf, abs, authors, title, comment, summary,
                                    ai_tldr, ai_motivation, ai_method, ai_result, ai_conclusion
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                                    ai_conclusion = EXCLUDED.ai_conclusion
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