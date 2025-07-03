import os
import json
import sys

import dotenv
import argparse

import openai # 使用openai库
# import langchain_core.exceptions # 移除langchain异常导入
# from langchain_community.chat_models import ChatOpenAI # 移除langchain模型导入
# from langchain.prompts import (
#   ChatPromptTemplate,
#   SystemMessagePromptTemplate,
#   HumanMessagePromptTemplate,
# ) # 移除langchain提示模板导入
from ai.structure import Structure
if os.path.exists('.env'):
    dotenv.load_dotenv()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    return parser.parse_args()

def run_enhancement_process(data: list):
    model_name = os.environ.get("MODEL_NAME", 'deepseek-r1')
    language = os.environ.get("language", 'Chinese')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "template.txt")
    system_path = os.path.join(current_dir, "system.txt")

    try:
        template_content = open(template_path, "r").read()
        system_content = open(system_path, "r").read()
    except FileNotFoundError as e:
        print(f"无法读取AI模板或系统文件: {e}", file=sys.stderr)
        raise

    llm_client = openai.OpenAI() 
    print('Connect to:', model_name, file=sys.stderr)
    
    # 构建消息列表
    # 格式化系统内容
    formatted_system_content = system_content.format(language=language)
    messages_template = [
        {"role": "system", "content": formatted_system_content},
        {"role": "user", "content": template_content}
    ]

    enhanced_data = []
    for idx, d in enumerate(data):
        # 格式化用户内容
        user_content = messages_template[1]["content"].format(language=language, content=d['summary'])
        messages = [
            messages_template[0],
            {"role": "user", "content": user_content}
        ]
        try:
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"} # 明确请求JSON输出
            )
            # 手动解析响应为Structure对象
            response_content = response.choices[0].message.content
            # 移除Markdown代码块标记
            if response_content.startswith("```json") and response_content.endswith("```"):
                response_content = response_content[len("```json\n"):-len("```")]
            
            parsed_response = Structure.model_validate_json(response_content)
            d['AI'] = parsed_response.model_dump()
            enhanced_data.append(d)
        except Exception as e: #
            print(f"{d['id']} has an error: {e}", file=sys.stderr)

        print(f"Finished {idx+1}/{len(data)}", file=sys.stderr)
    return enhanced_data
