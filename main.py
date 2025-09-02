"""主入口文件"""

import asyncio
import argparse
import json
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import CallInput, AnalysisConfig
from src.workflows.call_analysis_workflow import CallAnalysisWorkflow
from src.engines.vector_engine import get_vector_engine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import get_llm_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def analyze_single_call(
    transcript: str,
    call_id: str = None,
    customer_id: str = None,
    sales_id: str = None,
    config_file: str = None
) -> dict:
    """分析单个通话"""
    
    try:
        # 加载配置
        config = AnalysisConfig()
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                config = AnalysisConfig(**config_data)
        
        # 创建输入
        call_input = CallInput(
            call_id=call_id or f"call_{int(asyncio.get_event_loop().time())}",
            transcript=transcript,
            customer_id=customer_id,
            sales_id=sales_id
        )\n        \n        # 初始化引擎\n        logger.info(\"初始化分析引擎...\")\n        vector_engine = await get_vector_engine()\n        rule_engine = RuleEngine()\n        llm_engine = get_llm_engine()\n        \n        # 创建工作流\n        workflow = CallAnalysisWorkflow(\n            vector_engine=vector_engine,\n            rule_engine=rule_engine,\n            llm_engine=llm_engine\n        )\n        \n        # 执行分析\n        logger.info(f\"开始分析通话: {call_input.call_id}\")\n        result = await workflow.execute(call_input, config)\n        \n        logger.info(f\"分析完成，置信度: {result.confidence_score:.2f}\")\n        \n        return result.dict()\n        \n    except Exception as e:\n        logger.error(f\"分析失败: {e}\")\n        raise\n\n\nasync def analyze_batch_calls(input_file: str, output_file: str, config_file: str = None):\n    \"\"\"批量分析通话\"\"\"\n    \n    try:\n        # 加载输入文件\n        with open(input_file, 'r', encoding='utf-8') as f:\n            if input_file.endswith('.json'):\n                input_data = json.load(f)\n                if isinstance(input_data, list):\n                    call_inputs = [CallInput(**item) for item in input_data]\n                else:\n                    call_inputs = [CallInput(**input_data)]\n            else:\n                # 文本文件，每行一个JSON对象\n                call_inputs = []\n                for line in f:\n                    line = line.strip()\n                    if line:\n                        data = json.loads(line)\n                        call_inputs.append(CallInput(**data))\n        \n        logger.info(f\"加载了 {len(call_inputs)} 个通话数据\")\n        \n        # 加载配置\n        config = AnalysisConfig()\n        if config_file and os.path.exists(config_file):\n            with open(config_file, 'r', encoding='utf-8') as f:\n                config_data = json.load(f)\n                config = AnalysisConfig(**config_data)\n        \n        # 初始化引擎\n        logger.info(\"初始化分析引擎...\")\n        vector_engine = await get_vector_engine()\n        rule_engine = RuleEngine()\n        llm_engine = get_llm_engine()\n        \n        # 创建工作流\n        workflow = CallAnalysisWorkflow(\n            vector_engine=vector_engine,\n            rule_engine=rule_engine,\n            llm_engine=llm_engine\n        )\n        \n        # 批量执行分析\n        logger.info(\"开始批量分析...\")\n        results = await workflow.execute_batch(call_inputs, config, max_concurrency=3)\n        \n        # 保存结果\n        output_data = [result.dict() for result in results]\n        with open(output_file, 'w', encoding='utf-8') as f:\n            json.dump(output_data, f, ensure_ascii=False, indent=2)\n        \n        # 统计信息\n        success_count = sum(1 for r in results if r.confidence_score > 0.5)\n        logger.info(f\"批量分析完成，成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)\")\n        \n        return output_data\n        \n    except Exception as e:\n        logger.error(f\"批量分析失败: {e}\")\n        raise\n\n\ndef generate_sample_data(output_file: str):\n    \"\"\"生成示例数据\"\"\"\n    \n    sample_calls = [\n        {\n            \"call_id\": \"demo_001\",\n            \"transcript\": \"\"\"销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。\n客户：你好。\n销售：是这样的，我们是腾讯投资的上市公司，专门为股民提供专业的分析服务。耽误您两分钟时间，我免费给您讲解一下我们的核心功能。\n客户：好的，你说吧。\n销售：我们的主要功能是买卖点提示，B点代表最佳买入时机，S点代表卖出信号。另外还有主力控盘资金指标，可以看到大资金的进出。\n客户：听起来不错，有实际效果吗？\n销售：根据历史回测数据，使用我们信号的客户平均提升了18%的收益率。咱们看看您现在持有什么股票，我给您具体分析一下。\n客户：我持有招商银行和中国平安。\n销售：好的，我们来看看这两只股票的买卖点情况。我们还有步步高VIP专属功能，能提供更精准的信号。\n客户：这个功能收费吗？\n销售：我们有不同的服务套餐，您可以先试用一下看效果。\n客户：可以，我想了解一下。\"\"\",\n            \"customer_id\": \"customer_demo_001\",\n            \"sales_id\": \"sales_demo_001\",\n            \"call_time\": \"2024-01-15T10:30:00\"\n        },\n        {\n            \"call_id\": \"demo_002\",\n            \"transcript\": \"\"\"销售：您好，请问是张先生吗？\n客户：是的，什么事？\n销售：我这边是做股票投资咨询的，想了解一下您的投资情况。\n客户：不需要，我没空。\n销售：理解您很忙，不会耽误您太久的。我们有个很好的买卖点提示功能，能帮您把握机会。\n客户：不感兴趣，谢谢。\n销售：没关系，您如果有时间的话，我们可以约个时间详细聊聊。\n客户：不用了，再见。\"\"\",\n            \"customer_id\": \"customer_demo_002\",\n            \"sales_id\": \"sales_demo_002\", \n            \"call_time\": \"2024-01-15T14:20:00\"\n        }\n    ]\n    \n    with open(output_file, 'w', encoding='utf-8') as f:\n        json.dump(sample_calls, f, ensure_ascii=False, indent=2)\n    \n    print(f\"示例数据已生成: {output_file}\")\n\n\ndef main():\n    \"\"\"主函数\"\"\"\n    parser = argparse.ArgumentParser(description=\"销售通话质检系统\")\n    parser.add_argument(\"command\", choices=[\"analyze\", \"batch\", \"server\", \"dashboard\", \"sample\"],\n                       help=\"执行命令\")\n    \n    # 分析参数\n    parser.add_argument(\"--text\", \"-t\", help=\"通话文本\")\n    parser.add_argument(\"--file\", \"-f\", help=\"输入文件路径\")\n    parser.add_argument(\"--output\", \"-o\", help=\"输出文件路径\")\n    parser.add_argument(\"--config\", \"-c\", help=\"配置文件路径\")\n    \n    # 通话信息参数\n    parser.add_argument(\"--call-id\", help=\"通话ID\")\n    parser.add_argument(\"--customer-id\", help=\"客户ID\")\n    parser.add_argument(\"--sales-id\", help=\"销售员ID\")\n    \n    # 服务参数\n    parser.add_argument(\"--host\", default=\"0.0.0.0\", help=\"服务器地址\")\n    parser.add_argument(\"--port\", type=int, default=8000, help=\"服务器端口\")\n    \n    args = parser.parse_args()\n    \n    if args.command == \"analyze\":\n        # 单个通话分析\n        if not args.text:\n            print(\"错误: 请提供通话文本 (--text)\")\n            return\n        \n        result = asyncio.run(analyze_single_call(\n            transcript=args.text,\n            call_id=args.call_id,\n            customer_id=args.customer_id,\n            sales_id=args.sales_id,\n            config_file=args.config\n        ))\n        \n        if args.output:\n            with open(args.output, 'w', encoding='utf-8') as f:\n                json.dump(result, f, ensure_ascii=False, indent=2)\n            print(f\"分析结果已保存到: {args.output}\")\n        else:\n            print(json.dumps(result, ensure_ascii=False, indent=2))\n    \n    elif args.command == \"batch\":\n        # 批量分析\n        if not args.file:\n            print(\"错误: 请提供输入文件 (--file)\")\n            return\n        \n        if not args.output:\n            print(\"错误: 请提供输出文件 (--output)\")\n            return\n        \n        asyncio.run(analyze_batch_calls(\n            input_file=args.file,\n            output_file=args.output,\n            config_file=args.config\n        ))\n        \n        print(f\"批量分析完成，结果已保存到: {args.output}\")\n    \n    elif args.command == \"server\":\n        # 启动API服务器\n        print(f\"启动API服务器: http://{args.host}:{args.port}\")\n        \n        import uvicorn\n        from src.api.main import app\n        \n        uvicorn.run(\n            app,\n            host=args.host,\n            port=args.port,\n            reload=True\n        )\n    \n    elif args.command == \"dashboard\":\n        # 启动Dashboard\n        print(\"启动Streamlit Dashboard...\")\n        os.system(\"streamlit run src/dashboard/streamlit_app.py\")\n    \n    elif args.command == \"sample\":\n        # 生成示例数据\n        output_file = args.output or \"sample_data.json\"\n        generate_sample_data(output_file)\n\n\nif __name__ == \"__main__\":\n    main()"