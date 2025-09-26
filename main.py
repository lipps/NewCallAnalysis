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
        )

        # 初始化引擎
        logger.info("初始化分析引擎...")
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()

        # 创建工作流
        workflow = CallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )

        # 执行分析
        logger.info(f"开始分析通话: {call_input.call_id}")
        result = await workflow.execute(call_input, config)

        logger.info(f"分析完成，置信度: {result.confidence_score:.2f}")

        return result.dict()

    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise


async def analyze_batch_calls(input_file: str, output_file: str, config_file: str = None):
    """批量分析通话"""

    try:
        # 加载输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            if input_file.endswith('.json'):
                input_data = json.load(f)
                if isinstance(input_data, list):
                    call_inputs = [CallInput(**item) for item in input_data]
                else:
                    call_inputs = [CallInput(**input_data)]
            else:
                # 文本文件，每行一个JSON对象
                call_inputs = []
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        call_inputs.append(CallInput(**data))
        
        logger.info(f"加载了 {len(call_inputs)} 个通话数据")
        
        # 加载配置
        config = AnalysisConfig()
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                config = AnalysisConfig(**config_data)
        
        # 初始化引擎
        logger.info("初始化分析引擎...")
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        # 创建工作流
        workflow = CallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        # 批量执行分析
        logger.info("开始批量分析...")
        results = await workflow.execute_batch(call_inputs, config, max_concurrency=3)
        
        # 保存结果
        output_data = [result.dict() for result in results]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # 统计信息
        success_count = sum(1 for r in results if r.confidence_score > 0.5)
        logger.info(f"批量分析完成，成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
        
        return output_data
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise


def generate_sample_data(output_file: str):
    """生成示例数据"""
    
    sample_calls = [
        {
            "call_id": "demo_001",
            "transcript": """销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。
客户：你好。
销售：是这样的，我们是腾讯投资的上市公司，专门为股民提供专业的分析服务。耽误您两分钟时间，我免费给您讲解一下我们的核心功能。
客户：好的，你说吧。
销售：我们的主要功能是买卖点提示，B点代表最佳买入时机，S点代表卖出信号。另外还有主力控盘资金指标，可以看到大资金的进出。
客户：听起来不错，有实际效果吗？
销售：根据历史回测数据，使用我们信号的客户平均提升了18%的收益率。咱们看看您现在持有什么股票，我给您具体分析一下。
客户：我持有招商银行和中国平安。
销售：好的，我们来看看这两只股票的买卖点情况。我们还有步步高VIP专属功能，能提供更精准的信号。
客户：这个功能收费吗？
销售：我们有不同的服务套餐，您可以先试用一下看效果。
客户：可以，我想了解一下。""",
            "customer_id": "customer_demo_001",
            "sales_id": "sales_demo_001",
            "call_time": "2024-01-15T10:30:00"
        },
        {
            "call_id": "demo_002",
            "transcript": """销售：您好，请问是张先生吗？
客户：是的，什么事？
销售：我这边是做股票投资咨询的，想了解一下您的投资情况。
客户：不需要，我没空。
销售：理解您很忙，不会耽误您太久的。我们有个很好的买卖点提示功能，能帮您把握机会。
客户：不感兴趣，谢谢。
销售：没关系，您如果有时间的话，我们可以约个时间详细聊聊。
客户：不用了，再见。""",
            "customer_id": "customer_demo_002",
            "sales_id": "sales_demo_002", 
            "call_time": "2024-01-15T14:20:00"
        }
    ]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_calls, f, ensure_ascii=False, indent=2)
    
    print(f"示例数据已生成: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="销售通话质检系统")
    parser.add_argument("command", choices=["analyze", "batch", "server", "dashboard", "sample"],
                       help="执行命令")
    
    # 分析参数
    parser.add_argument("--text", "-t", help="通话文本")
    parser.add_argument("--file", "-f", help="输入文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--config", "-c", help="配置文件路径")
    
    # 通话信息参数
    parser.add_argument("--call-id", help="通话ID")
    parser.add_argument("--customer-id", help="客户ID")
    parser.add_argument("--sales-id", help="销售员ID")
    
    # 服务参数
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        # 单个通话分析
        if not args.text:
            print("错误: 请提供通话文本 (--text)")
            return
        
        result = asyncio.run(analyze_single_call(
            transcript=args.text,
            call_id=args.call_id,
            customer_id=args.customer_id,
            sales_id=args.sales_id,
            config_file=args.config
        ))
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"分析结果已保存到: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "batch":
        # 批量分析
        if not args.file:
            print("错误: 请提供输入文件 (--file)")
            return
        
        if not args.output:
            print("错误: 请提供输出文件 (--output)")
            return
        
        asyncio.run(analyze_batch_calls(
            input_file=args.file,
            output_file=args.output,
            config_file=args.config
        ))
        
        print(f"批量分析完成，结果已保存到: {args.output}")
    
    elif args.command == "server":
        # 启动API服务器
        print(f"启动API服务器: http://{args.host}:{args.port}")
        
        import uvicorn
        from src.api.main import app
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=True
        )
    
    elif args.command == "dashboard":
        # 启动Dashboard
        print("启动Streamlit Dashboard...")
        os.system("streamlit run src/dashboard/streamlit_app.py")
    
    elif args.command == "sample":
        # 生成示例数据
        output_file = args.output or "sample_data.json"
        generate_sample_data(output_file)


if __name__ == "__main__":
    main()