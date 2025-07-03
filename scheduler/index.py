# 确保在导入其他twisted/scrapy模块之前安装reactor
from scrapy.utils.reactor import install_reactor
install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

import json
from datetime import datetime, timezone
import logging
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor,defer

from daily_arxiv.daily_arxiv.spiders.arxiv import ArxivSpider
from ai.enhance import run_enhancement_process
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

class DailyArXivPipeline:
    def __init__(self, language="Chinese"):
        self.language = language
        self.logger = self._setup_logger()
        self.data_pipeline = {
            'raw_data': [],
            'enhanced_data': [],
        }
    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def run(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.logger.info(f"--- 开始内存版 {today} arXiv 处理流程 ---")
        try:
            # 1. 运行Scrapy爬虫（内存捕获）
            raw_data = self._run_scrapy_in_memory()
            self.data_pipeline['raw_data'] = raw_data
            # 2. AI增强处理（内存数据）
            enhanced_data = run_enhancement_process(raw_data, self.language)
            self.data_pipeline['enhanced_data'] = enhanced_data
            self.logger.info(f"--- 内存处理流程执行完毕，共抓取 {len(raw_data)} 条，增强 {len(enhanced_data)} 条 ---")
            return True
        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            return False

    def _run_scrapy_in_memory(self):
        results = []
        class CollectItemsSpider(ArxivSpider):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def parse(self, response):
                for item in super().parse(response):
                    results.append(dict(item))
                    yield item
        runner = CrawlerRunner()
        @defer.inlineCallbacks
        def crawl():
            yield runner.crawl(CollectItemsSpider)
            reactor.stop()
        crawl()
        reactor.run()
        self.logger.info(f"Scrapy爬虫完成，捕获 {len(results)} 条数据")
        return results

    def get_enhanced_data(self):
        return self.data_pipeline['enhanced_data']

if __name__ == "__main__":
    pipeline = DailyArXivPipeline(language="Chinese")
    if pipeline.run():
        print("处理成功！")
        result = pipeline.get_enhanced_data()
        print(f"获取到 {len(result)} 条增强数据")
    else:
        print("处理失败")