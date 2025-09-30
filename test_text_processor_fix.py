#!/usr/bin/env python3
"""
测试文本处理器修复效果
验证A/B格式说话人识别和时间戳处理
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.processors.text_processor import TextProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 用户提供的测试数据（截取部分）
TEST_CONTENT = """[0:0:0]B:喂。<br/>[0:0:1]A:喂，你好你好你好，请问是尾号九八零九的机主本人吗？<br/>[0:0:2]B:嗯。<br/>[0:0:4]A:哎，你好啊，我这边是上海翼盟操盘手的，就是看到您今天下午啊有浏览登录咱们一盟操盘手这个股票分析软件。<br/>[0:0:5]B:嗯。<br/>[0:0:12]A:因为咱们很多重新下载的用户啊，就是反馈软件里面的功能不太会用。<br/>[0:0:13]B:嗯。<br/>[0:0:16]A:公司特地安排我来电啊，专门免费来教您使用的。<br/>[0:0:17]B:嗯。<br/>[0:0:19]A:就是您平时的话是手机看盘比较多，电脑看盘比较多呀。<br/>[0:0:20]B:嗯。<br/>[0:0:23]B:手机、电脑都有。<br/>[0:0:25]A:啊，行行，那您这样，您可以把这个软件打开，咱们耽误您几分钟这个时间啊。<br/>[0:1:0]A:啊，左上角这个对全景点开。<br/>[0:1:2]B:点开了嗯。<br/>[0:12:11]B:等会儿说吧，等会儿说吧，我还有事。<br/>[0:12:14]A:行，还有事。<br/>[0:12:15]A:大哥，那您这样，那您这样，您把您的微信打开，我先教你加一下我的微信，我把这个资料给您发到您的手机里面去嘛。<br/>[0:13:23]A:好的好的好的，我给你发过去。<br/>"""

async def test_text_processor():
    """测试文本处理器"""
    print("🚀 开始测试文本处理器修复效果...")
    
    processor = TextProcessor()
    
    try:
        # 处理测试内容
        result = await processor.process(TEST_CONTENT)
        
        print("\n📊 处理结果:")
        print(f"原始文本长度: {len(result['original_text'])} 字符")
        print(f"清理后文本长度: {len(result['cleaned_text'])} 字符")
        print(f"总对话数: {result['content_analysis']['total_dialogues']}")
        print(f"销售对话数: {result['content_analysis']['sales_dialogues']}")
        print(f"客户对话数: {result['content_analysis']['customer_dialogues']}")
        print(f"未知对话数: {result['content_analysis']['unknown_dialogues']}")
        
        # 统计信息
        stats = result['statistics']
        print(f"\n⏱️ 时长统计:")
        print(f"估算时长: {stats['estimated_duration_minutes']:.1f} 分钟")
        print(f"互动频率: {stats['interaction_frequency']:.1f} 次/分钟")
        
        # 显示前几个对话的识别结果
        print(f"\n🔍 说话人识别结果 (前10个):")
        for i, dialogue in enumerate(result['dialogues'][:10]):
            speaker_label = "🗣️销售" if dialogue['speaker'] == 'sales' else "👥客户" if dialogue['speaker'] == 'customer' else "❓未知"
            print(f"{i+1:2d}. [{dialogue.get('timestamp', 'N/A')}] {speaker_label}: {dialogue['content'][:50]}{'...' if len(dialogue['content']) > 50 else ''}")
        
        # 对话模式分析
        pattern = result['content_analysis']['conversation_pattern']
        print(f"\n🔄 对话模式 (前20个): {' -> '.join(pattern[:20])}")
        
        # 验证关键指标
        print(f"\n✅ 关键验证:")
        duration = stats['estimated_duration_minutes']
        sales_count = result['content_analysis']['sales_dialogues']
        customer_count = result['content_analysis']['customer_dialogues']
        interaction_rate = stats['interaction_frequency']
        
        success_criteria = []
        
        # 时长应该接近13分钟（从0:0:0到0:13:23）
        if 12 <= duration <= 15:
            success_criteria.append("✅ 时长计算正确")
        else:
            success_criteria.append("❌ 时长计算异常")
        
        # 应该有销售和客户对话
        if sales_count > 0 and customer_count > 0:
            success_criteria.append("✅ 说话人识别成功")
        else:
            success_criteria.append("❌ 说话人识别失败")
        
        # 互动频率应该合理（每分钟1-10次）
        if 1 <= interaction_rate <= 10:
            success_criteria.append("✅ 互动频率合理")
        else:
            success_criteria.append("❌ 互动频率异常")
        
        # HTML标签应该被清理
        if '<br/>' not in result['cleaned_text']:
            success_criteria.append("✅ HTML标签清理成功")
        else:
            success_criteria.append("❌ HTML标签清理失败")
        
        print("\n".join(success_criteria))
        
        # 详细时间戳分析
        timestamps = [d.get('timestamp') for d in result['dialogues'] if d.get('timestamp')]
        if timestamps:
            print(f"\n🕐 时间戳分析:")
            print(f"时间戳数量: {len(timestamps)}")
            print(f"开始时间: {timestamps[0]}")
            print(f"结束时间: {timestamps[-1]}")
        
        return len([c for c in success_criteria if c.startswith("✅")]) == len(success_criteria)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("📋 文本处理器修复验证测试")
    print("=" * 50)
    
    success = await test_text_processor()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！修复成功！")
        print("✅ A/B格式说话人识别正常")
        print("✅ 时间戳解析正确") 
        print("✅ 时长计算准确")
        print("✅ 互动频率合理")
        print("✅ HTML标签清理成功")
    else:
        print("⚠️  部分测试失败，需要进一步调试")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
