# 确保在导入其他twisted/scrapy模块之前安装reactor
from scrapy.utils.reactor import install_reactor
install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

import json
from datetime import datetime, timezone, timedelta
import logging
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor,defer
from concurrent.futures import ThreadPoolExecutor

import arxiv

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
        # 抑制arxiv库的INFO级别日志
        logging.getLogger('arxiv').setLevel(logging.WARNING)
        return logging.getLogger(__name__)

    def _fetch_paper_details(self, item):
        search = arxiv.Search(
            id_list=[item["id"]],
        )
        paper = next(arxiv.Client().results(search))
        item["authors"] = [a.name for a in paper.authors]
        item["title"] = paper.title
        item["categories"] = paper.categories
        item["comment"] = paper.comment
        item["summary"] = paper.summary
        return item

    def run(self):
        # 定义北京时区 (UTC+8)
        beijing_tz = timezone(timedelta(hours=8))
        # 获取当前北京时间并格式化日期
        today = datetime.now(beijing_tz).strftime("%Y-%m-%d")
        self.logger.info(f"--- 开始 {today} arXiv 处理流程 ---")
        try:
            # 1. 运行Scrapy爬虫（内存捕获）
            raw_data = self._run_scrapy_in_memory()
            
            # 2. 并行获取论文详细信息
            self.logger.info(f"--- 开始并行获取论文详细信息 ---")
            with ThreadPoolExecutor(max_workers=20) as executor:
                detailed_data = list(executor.map(self._fetch_paper_details, raw_data))
            self.logger.info(f"--- 论文详细信息获取完毕，共 {len(detailed_data)} 条 ---")

            # 3. AI增强处理（内存数据）
            enhanced_data = run_enhancement_process(detailed_data)
            
            # 4. 存储到数据库
            if self.db_manager.connect_and_create_table():
                self.db_manager.insert_data(enhanced_data)
            self.logger.info(f"--- 执行完毕，共抓取 {len(raw_data)} 条，增强 {len(enhanced_data)} 条 ---")
            return True
        except Exception as e:
            print(e)
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