"""服务启动脚本"""

import uvicorn
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings

if __name__ == "__main__":
    # 确保必要的目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print(f"🚀 启动 {settings.app_name} v{settings.version}")
    print(f"📡 服务地址: http://{settings.server.host}:{settings.server.port}")
    print(f"📚 API文档: http://{settings.server.host}:{settings.server.port}/docs")
    print(f"🔍 ReDoc: http://{settings.server.host}:{settings.server.port}/redoc")
    
    # 启动服务器
    uvicorn.run(
        "src.api.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.logging.log_level.lower(),
        access_log=True
    )