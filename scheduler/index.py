# 确保在导入其他twisted/scrapy模块之前安装reactor
from scrapy.utils.reactor import install_reactor
install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

import json
from datetime import datetime, timezone
import logging
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor,defer

from daily_arxiv.daily_arxiv.spiders.arxiv import ArxivSpider
from daily_arxiv.daily_arxiv.pipelines import DailyArxivPipeline
from ai.enhance import run_enhancement_process
from api.database import DatabaseManager
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

class DailyArXivProcessor:
    def __init__(self, language="Chinese"):
        self.language = language
        self.logger = self._setup_logger()
        self.db_manager = DatabaseManager()

    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def run(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.logger.info(f"--- 开始 {today} arXiv 处理流程 ---")
        try:
            # 1. 运行Scrapy爬虫（内存捕获）
            raw_data = self._run_scrapy_in_memory()
            # 2. AI增强处理（内存数据）
            # enhanced_data = run_enhancement_process(raw_data, self.language)
            
            # 3. 存储到数据库
            if self.db_manager.connect_and_create_table():
                self.db_manager.insert_data(raw_data)

            self.logger.info(f"--- 内存处理流程执行完毕，共抓取 {len(raw_data)} 条，增强 {len(raw_data)} 条 ---")
            return True
        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            return False

    def _run_scrapy_in_memory(self):
        results = []
        pipeline_instance = DailyArxivPipeline() # 实例化管道
        class CollectItemsSpider(ArxivSpider):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def parse(self, response):
                for item in super().parse(response):
                    processed_item = pipeline_instance.process_item(item, self) # 调用管道处理item
                    results.append(dict(processed_item))
                    yield processed_item
        runner = CrawlerRunner()
        @defer.inlineCallbacks
        def crawl():
            yield runner.crawl(CollectItemsSpider)
            reactor.stop()
        crawl()
        reactor.run()
        self.logger.info(f"Scrapy爬虫完成，捕获 {len(results)} 条数据")
        return results


if __name__ == "__main__":
    processor = DailyArXivProcessor(language="Chinese")
    if processor.run():
        print("处理成功！")
    else:
        print("处理失败")