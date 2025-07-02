today=`date -u "+%Y-%m-%d"`
echo "--- 开始执行${today} arXiv 爬取和总结流程 ---"

cd daily_arxiv
python -m scrapy crawl arxiv -o ../data/${today}.jsonl

cd ../ai
python enhance.py --data ../data/${today}.jsonl

# cd ../to_md
# python convert.py --data ../data/${today}_AI_enhanced_${LANGUAGE}.jsonl

# cd ..
# python update_readme.py

# ls data/*.jsonl | sed 's|data/||' > assets/file-list.txt
echo "--- 每日 arXiv 流程执行完毕 ---"
