#!/usr/bin/env python3
"""Dashboard调试脚本"""

import requests
import time
import json
from datetime import datetime

def test_api_connection():
    """测试API连接"""
    print("🔍 测试API服务器连接...")
    
    try:
        # 测试健康检查
        start_time = time.time()
        response = requests.get("http://localhost:8000/health", timeout=10)
        end_time = time.time()
        
        print(f"✅ 健康检查成功: {response.status_code}")
        print(f"⏱️  响应时间: {(end_time - start_time)*1000:.2f}ms")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"📊 系统状态: {health_data.get('status', 'unknown')}")
            
            # 检查组件状态
            components = health_data.get('components', {})
            for name, status in components.items():
                print(f"   {name}: {status.get('status', 'unknown')}")
        
    except requests.exceptions.Timeout:
        print("❌ 健康检查超时")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        return False
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False
    
    return True

def test_analysis_endpoint():
    """测试分析端点"""
    print("\n🔍 测试分析端点...")
    
    # 测试数据
    test_data = {
        "call_input": {
            "call_id": "debug_test",
            "transcript": "销售：您好，我是益盟操盘手专员。客户：你好。销售：我们提供专业的股票分析服务。",
            "customer_id": "debug_customer",
            "sales_id": "debug_sales",
            "call_time": datetime.now().isoformat()
        },
        "config": {
            "enable_vector_search": True,
            "enable_llm_validation": False,
            "confidence_threshold": 0.7
        }
    }
    
    try:
        print("📤 发送分析请求...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:8000/analyze",
            json=test_data,
            timeout=120,  # 2分钟超时
            headers={"Content-Type": "application/json"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ 分析请求完成: {response.status_code}")
        print(f"⏱️  总耗时: {duration:.2f}秒")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 分析结果: 置信度 {result.get('confidence_score', 0):.3f}")
            return True
        else:
            print(f"❌ 分析失败: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 分析请求超时 (120秒)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_dashboard_connection():
    """测试Dashboard连接"""
    print("\n🔍 测试Dashboard连接...")
    
    try:
        response = requests.get("http://localhost:8501", timeout=10)
        print(f"✅ Dashboard响应: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Dashboard连接失败: {e}")
        return False

def test_network_latency():
    """测试网络延迟"""
    print("\n🔍 测试网络延迟...")
    
    # 测试本地回环延迟
    localhost_times = []
    for i in range(5):
        try:
            start_time = time.time()
            response = requests.get("http://localhost:8000/", timeout=5)
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            localhost_times.append(latency)
            print(f"   本地请求 {i+1}: {latency:.2f}ms")
        except Exception as e:
            print(f"   本地请求 {i+1}: 失败 - {e}")
    
    if localhost_times:
        avg_latency = sum(localhost_times) / len(localhost_times)
        print(f"📊 平均本地延迟: {avg_latency:.2f}ms")
        
        if avg_latency > 1000:  # 超过1秒
            print("⚠️  本地延迟较高，可能存在性能问题")

def main():
    """主函数"""
    print("🚀 Dashboard调试诊断工具")
    print("=" * 50)
    
    # 测试API连接
    api_ok = test_api_connection()
    
    # 测试分析端点
    if api_ok:
        analysis_ok = test_analysis_endpoint()
    else:
        print("⚠️  跳过分析测试（API连接失败）")
        analysis_ok = False
    
    # 测试Dashboard连接
    dashboard_ok = test_dashboard_connection()
    
    # 测试网络延迟
    test_network_latency()
    
    # 总结
    print("\n" + "=" * 50)
    print("📋 诊断总结:")
    print(f"   API服务器: {'✅ 正常' if api_ok else '❌ 异常'}")
    print(f"   分析端点: {'✅ 正常' if analysis_ok else '❌ 异常'}")
    print(f"   Dashboard: {'✅ 正常' if dashboard_ok else '❌ 异常'}")
    
    if not api_ok:
        print("\n🔧 建议:")
        print("   1. 检查API服务器是否正在运行: python run_server.py")
        print("   2. 检查端口8000是否被占用")
        print("   3. 查看API服务器日志")
    
    if not analysis_ok:
        print("\n🔧 建议:")
        print("   1. 检查工作流配置")
        print("   2. 检查向量引擎和规则引擎状态")
        print("   3. 查看详细错误日志")
    
    if not dashboard_ok:
        print("\n🔧 建议:")
        print("   1. 检查Dashboard是否正在运行: python run_dashboard.py")
        print("   2. 检查端口8501是否被占用")
        print("   3. 查看Streamlit日志")

if __name__ == "__main__":
    main() 