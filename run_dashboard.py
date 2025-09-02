"""Dashboard启动脚本"""

import os
import sys
from pathlib import Path
import subprocess

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # 确保必要的目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("🎨 启动销售通话质检系统 Dashboard")
    print("📊 Dashboard地址: http://localhost:8501")
    print("⚡ 确保API服务器已启动: python run_server.py")
    
    # 启动Streamlit应用
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "src/dashboard/streamlit_app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ])