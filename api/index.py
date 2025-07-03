from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入rss_server中的应用和函数
from rss_server import app, generate_rss_xml

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 添加健康检查端点
@app.get("/")
def read_root():
    return {"status": "ok", "message": "arXiv RSS API is running"}

# 添加API文档路由
@app.get("/api-docs")
def api_docs():
    return {
        "endpoints": [
            {
                "path": "/",
                "method": "GET",
                "description": "健康检查端点"
            },
            {
                "path": "/feed",
                "method": "GET",
                "description": "获取所有分类的RSS源",
                "params": [
                    {"name": "date", "type": "string", "required": False, "description": "指定日期 (YYYY-MM-DD)，默认为最近30天"}, 
                    {"name": "lang", "type": "string", "required": False, "description": "语言，默认为Chinese"}
                ]
            },
            {
                "path": "/feed/{cat}",
                "method": "GET",
                "description": "获取特定分类的RSS源",
                "params": [
                    {"name": "cat", "type": "string", "required": True, "description": "arXiv分类代码，如cs.CL, cs.CV等"},
                    {"name": "date", "type": "string", "required": False, "description": "指定日期 (YYYY-MM-DD)，默认为最近30天"},
                    {"name": "lang", "type": "string", "required": False, "description": "语言，默认为Chinese"}
                ]
            }
        ]
    }