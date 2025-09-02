"""检查系统配置"""

import os
from src.config.settings import settings

def check_openai_config():
    """检查 OpenAI 配置"""
    print("🔍 检查 OpenAI 配置")
    print("=" * 50)
    
    # 检查环境变量
    env_key = os.getenv("OPENAI_API_KEY")
    print(f"环境变量 OPENAI_API_KEY: {'已设置' if env_key else '未设置'}")
    
    # 检查设置文件
    settings_key = settings.model.openai_api_key
    print(f"设置文件 API Key: {'已配置' if settings_key else '未配置'}")
    print(f"Base URL: {settings.model.openai_base_url}")
    print(f"模型: {settings.model.llm_model}")
    
    # 检查 .env 文件
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        print(f"✅ .env 文件存在")
        with open(env_file_path, 'r') as f:
            content = f.read()
            if "OPENAI_API_KEY" in content:
                print("✅ .env 文件包含 OPENAI_API_KEY")
            else:
                print("❌ .env 文件不包含 OPENAI_API_KEY")
    else:
        print("❌ .env 文件不存在")
    
    return bool(env_key or settings_key)

def suggest_fix():
    """建议修复方案"""
    print("\n💡 修复建议:")
    print("1. 创建 .env 文件并添加:")
    print("   OPENAI_API_KEY=your_api_key_here")
    print("2. 或者设置环境变量:")
    print("   export OPENAI_API_KEY=your_api_key_here")
    print("3. 禁用 LLM 验证以仅使用规则引擎:")
    print("   在分析配置中设置 enable_llm_validation=False")

if __name__ == "__main__":
    has_key = check_openai_config()
    
    if not has_key:
        suggest_fix()
    else:
        print("\n✅ OpenAI 配置正常")