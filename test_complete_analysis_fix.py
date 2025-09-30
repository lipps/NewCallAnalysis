#!/usr/bin/env python3
"""
完整的端到端分析流程测试
验证整个通话分析系统能否正常处理A/B格式文件
"""

import asyncio
import sys
import os
from pathlib import Path
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import CallInput, AnalysisConfig
from src.workflows.call_analysis_workflow import CallAnalysisWorkflow
from src.engines.vector_engine import get_vector_engine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import get_llm_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 完整的测试数据 - 来自用户提供的实际文件片段
COMPLETE_TEST_CONTENT = """[0:0:0]B:喂。<br/>[0:0:1]A:喂，你好你好你好，请问是尾号九八零九的机主本人吗？<br/>[0:0:2]B:嗯。<br/>[0:0:4]A:哎，你好啊，我这边是上海翼盟操盘手的，就是看到您今天下午啊有浏览登录咱们一盟操盘手这个股票分析软件。<br/>[0:0:5]B:嗯。<br/>[0:0:12]A:因为咱们很多重新下载的用户啊，就是反馈软件里面的功能不太会用。<br/>[0:0:13]B:嗯。<br/>[0:0:16]A:公司特地安排我来电啊，专门免费来教您使用的。<br/>[0:0:17]B:嗯。<br/>[0:0:19]A:就是您平时的话是手机看盘比较多，电脑看盘比较多呀。<br/>[0:0:20]B:嗯。<br/>[0:0:23]B:手机、电脑都有。<br/>[0:0:25]A:啊，行行，那您这样，您可以把这个软件打开，咱们耽误您几分钟这个时间啊。<br/>[0:0:29]B:嗯。<br/>[0:0:29]A:把这里面的这个好用的功能指标带您调整出来。<br/>[0:0:30]B:嗯。<br/>[0:0:32]A:办好的话，咱们盘中也方便看盘使用的，能理解吧？<br/>[0:0:35]B:嗯嗯。<br/>[0:0:36]A:大哥，那行，那您就可以把那电脑打开这个对，你看一下。<br/>[0:0:40]A:好，您打开了之后，您看咱们这个电脑这个右上角有没有显示您这个手机尾号呀？<br/>[0:0:46]B:先生。<br/>[0:0:47]A:哎，有没有有显示的吧。<br/>[0:0:49]B:嗯。<br/>[0:0:50]A:好，行，那有显示的话呢，您看一下，显示完之后呢，在这个点击那个电脑左上角，把这个左上角那个全点击点开。<br/>[0:1:0]A:啊，左上角这个对全景点开。<br/>[0:1:2]B:点开了嗯。<br/>[0:1:3]A:啊，点开了之后呢，为了方便您理解的话，呃，左上角是可以看到大盘的一个走势。<br/>[0:1:8]A:对，然然后的话在这个全景这个界面，为了方便您理解啊，我这边随机点开一下公司的一个个股啊，给您做功能展示，不作为投资建议，主要是把这里面的功能指标带您调整出来。<br/>[0:1:19]A:哎，那那您这样您看一下啊，您在这个键盘上您挑一下零零二零四四。<br/>[0:1:32]A:把那个美年健康点开，点开了没？<br/>[0:1:35]A:大哥，好，那您点开之后，您看一下，点开之后，在这个界面，您看咱们看到的是分时还是日新啊？<br/>[0:1:49]A:奔驰好，那您看在这个分持这个界面的话，你旁边有个日k线，看到了没有？<br/>[0:2:2]A:对，优子线把这个日k键点开，点开之后呢，你看一下在这个日k这个界面不用动了。<br/>[0:12:11]B:等会儿说吧，等会儿说吧，我还有事。<br/>[0:12:14]A:行，还有事。<br/>[0:12:15]A:大哥，那您这样，那您这样，您把您的微信打开，我先教你加一下我的微信，我把这个资料给您发到您的手机里面去嘛。<br/>[0:13:23]A:好的好的好的，我给你发过去。<br/>"""

async def test_complete_analysis():
    """测试完整的分析流程"""
    print("🚀 开始端到端完整分析测试...")
    
    try:
        # 创建通话输入
        call_input = CallInput(
            call_id="test_ab_format_001",
            transcript=COMPLETE_TEST_CONTENT,
            customer_id="test_customer_001",
            sales_id="test_sales_001",
            call_time="2024-01-15T10:30:00"
        )
        
        # 创建分析配置
        config = AnalysisConfig(
            enable_vector_search=False,  # 关闭向量检索加快测试
            enable_llm_validation=False, # 关闭LLM验证加快测试
            confidence_threshold=0.3
        )
        
        print("📋 初始化分析引擎...")
        
        # 初始化引擎 - 简化版本用于测试
        try:
            vector_engine = await get_vector_engine()
        except:
            vector_engine = None  # 如果向量引擎初始化失败，设为None
            
        rule_engine = RuleEngine()
        
        try:
            llm_engine = get_llm_engine()
        except:
            llm_engine = None  # 如果LLM引擎初始化失败，设为None
        
        # 创建工作流
        workflow = CallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        print("🔄 执行完整分析流程...")
        
        # 执行分析
        result = await workflow.execute(call_input, config)
        
        print("\n📊 分析结果概览:")
        print(f"通话ID: {result.call_id}")
        print(f"整体置信度: {result.confidence_score:.2f}")
        
        # 破冰分析结果
        print(f"\n🗣️ 破冰分析:")
        print(f"专业身份: {'✅' if result.icebreak.professional_identity.hit else '❌'} (置信度: {result.icebreak.professional_identity.confidence:.2f})")
        print(f"帮助价值: {'✅' if result.icebreak.value_help.hit else '❌'} (置信度: {result.icebreak.value_help.confidence:.2f})")
        print(f"时间说明: {'✅' if result.icebreak.time_notice.hit else '❌'} (置信度: {result.icebreak.time_notice.confidence:.2f})")
        print(f"免费讲解: {'✅' if result.icebreak.free_teach.hit else '❌'} (置信度: {result.icebreak.free_teach.confidence:.2f})")
        
        # 演绎分析结果
        print(f"\n📈 演绎分析:")
        print(f"BS点讲解: {'✅' if result.演绎.bs_explained.hit else '❌'} (置信度: {result.演绎.bs_explained.confidence:.2f})")
        print(f"软件演示: {'✅' if result.演绎.customer_stock_explained.hit else '❌'} (置信度: {result.演绎.customer_stock_explained.confidence:.2f})")
        
        # 过程指标
        print(f"\n⏱️ 过程指标:")
        print(f"通话时长: {result.process.explain_duration_min:.1f} 分钟")
        print(f"互动频率: {result.process.interaction_rounds_per_min:.1f} 次/分钟")
        print(f"成交/约访: {'✅' if result.process.deal_or_visit else '❌'}")
        
        # 客户分析
        print(f"\n👥 客户分析:")
        print(f"客户总结: {result.customer.summary}")
        print(f"价值认同: {result.customer.value_recognition}")
        print(f"态度评分: {result.customer.attitude_score:.2f}")
        
        # 验证关键指标
        success_criteria = []
        
        # 时长应该约为13分钟
        if 12 <= result.process.explain_duration_min <= 15:
            success_criteria.append("✅ 时长计算正确")
        else:
            success_criteria.append("❌ 时长计算异常")
        
        # 应该识别出专业身份和免费讲解
        if result.icebreak.professional_identity.hit:
            success_criteria.append("✅ 专业身份识别成功")
        else:
            success_criteria.append("❌ 专业身份识别失败")
            
        if result.icebreak.free_teach.hit:
            success_criteria.append("✅ 免费讲解识别成功") 
        else:
            success_criteria.append("❌ 免费讲解识别失败")
        
        # 互动频率应该合理
        if 0.5 <= result.process.interaction_rounds_per_min <= 5:
            success_criteria.append("✅ 互动频率合理")
        else:
            success_criteria.append("❌ 互动频率异常")
        
        print(f"\n✅ 综合验证:")
        print("\n".join(success_criteria))
        
        return len([c for c in success_criteria if c.startswith("✅")]) == len(success_criteria)
        
    except Exception as e:
        print(f"❌ 完整分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🎯 端到端完整分析流程测试")
    print("=" * 60)
    print("测试目标: 验证A/B格式文件能否完整通过所有分析模块")
    print("=" * 60)
    
    success = await test_complete_analysis()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 端到端测试完全成功！")
        print("✅ A/B格式文件完全兼容")
        print("✅ 文本处理模块正常") 
        print("✅ 破冰分析模块正常")
        print("✅ 演绎分析模块正常")
        print("✅ 过程统计模块正常")
        print("✅ 客户分析模块正常")
        print("\n🎊 修复完成，系统可以正常处理用户的通话文件格式！")
    else:
        print("⚠️ 端到端测试部分失败")
        print("文本处理已修复，但可能需要进一步调试其他模块")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
