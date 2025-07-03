import os
import json
import sys

import dotenv
import argparse

import langchain_core.exceptions
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import (
  ChatPromptTemplate,
  SystemMessagePromptTemplate,
  HumanMessagePromptTemplate,
)
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

    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="function_calling")
    print('Connect to:', model_name, file=sys.stderr)
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_content),
        HumanMessagePromptTemplate.from_template(template=template_content)
    ])

    chain = prompt_template | llm

    enhanced_data = []
    for idx, d in enumerate(data):
        try:
            response: Structure = chain.invoke({
                "language": language,
                "content": d['summary']
            })
            d['AI'] = response.model_dump()
            enhanced_data.append(d)
        except langchain_core.exceptions.OutputParserException as e:
            print(f"{d['id']} has an error: {e}", file=sys.stderr)
            # 不将失败数据添加到 enhanced_data
        except Exception as e:
            print(f"处理 {d['id']} 时发生未知错误: {e}", file=sys.stderr)
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
