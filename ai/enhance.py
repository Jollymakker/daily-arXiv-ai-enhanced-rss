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

def run_enhancement_process(data: list, language: str):
    model_name = os.environ.get("MODEL_NAME", 'deepseek-chat')
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "template.txt")
    system_path = os.path.join(current_dir, "system.txt")

    try:
        template_content = open(template_path, "r").read()
        system_content = open(system_path, "r").read()
    except FileNotFoundError as e:
        print(f"无法读取AI模板或系统文件: {e}", file=sys.stderr)
        raise

    llm_client = openai.OpenAI() # 初始化OpenAI客户端
    print('Connect to:', model_name, file=sys.stderr)
    
    # 构建消息列表
    messages_template = [
        {"role": "system", "content": system_content},
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
            response: Structure = llm_client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_model=Structure # 直接指定Pydantic模型进行结构化输出
            )
            d['AI'] = response.model_dump()
            enhanced_data.append(d)
        # except langchain_core.exceptions.OutputParserException as e: # 移除langchain异常
        except Exception as e: # 捕获更通用的异常，Pydantic验证错误也在此处理
            print(f"{d['id']} has an error: {e}", file=sys.stderr)
            # 不将失败数据添加到 enhanced_data

        print(f"Finished {idx+1}/{len(data)}", file=sys.stderr)
    
    return enhanced_data

def main():
    args = parse_args()
    # model_name = os.environ.get("MODEL_NAME", 'deepseek-chat') # 不再需要，由run_enhancement_process处理
    language = os.environ.get("LANGUAGE", 'Chinese')

    data = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)

    data = unique_data

    print('Open:', args.data, file=sys.stderr)

    # 调用新的增强函数
    enhanced_result = run_enhancement_process(data, language)

    # main函数仍然负责写入文件，以保持独立脚本的功能
    output_file_path = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_file_path, "w") as f:
        for d in enhanced_result:
            f.write(json.dumps(d) + "\n")

    print(f"Enhanced data written to {output_file_path}", file=sys.stderr)

if __name__ == "__main__":
    main()
