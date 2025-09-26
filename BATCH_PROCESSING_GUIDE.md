# 批量文件处理功能使用指南

## 📋 概述

批量文件处理功能是销售通话质检系统的重要扩展，支持一次性上传和分析多个通话文件，大幅提升批量数据处理效率。

## ✨ 核心特性

### 🎯 支持的文件格式
- **JSON**: 支持 `[CallInput...]`, `{"calls": [...]}`, 单个 `CallInput` 对象
- **JSONL**: 每行一个JSON对象格式
- **CSV**: 至少包含 `transcript` 列，可选 `call_id`, `customer_id`, `sales_id`, `call_time`
- **TXT**: 一个文件一个通话，支持分隔符分割多通话

### 📊 处理能力
- 最多 **20个文件**/批次
- 最多 **2000条通话**/批次
- 单个文件最大 **200MB**
- 最大并发处理 **3个文件**

### 🔧 核心功能
- **智能文件解析**: 自动检测编码，支持多种文件结构
- **并发处理**: 多文件并行分析，提升处理效率
- **实时进度**: 详细的进度跟踪和状态反馈
- **结果存储**: 按文件独立保存分析结果，支持批量下载
- **错误隔离**: 单文件失败不影响其他文件处理
- **完善监控**: 内存使用、处理耗时、成功率统计

## 🚀 快速开始

### 1. 环境准备

确保系统服务正常运行：
```bash
# 启动API服务器
python main.py server

# 启动Dashboard（新终端）
python main.py dashboard
```

### 2. 使用Web界面

1. 访问 http://localhost:8501
2. 切换到 **"批量分析"** 标签
3. 配置批量处理参数（可选）
4. 上传文件并开始分析

### 3. 使用API接口

```bash
# 获取批量配置信息
curl -X GET "http://localhost:8000/analyze/batch/config"

# 提交批量处理请求
curl -X POST "http://localhost:8000/analyze/batch/files" \
  -H "Content-Type: application/json" \
  -d @batch_request.json

# 查询处理状态
curl -X GET "http://localhost:8000/analyze/batch/{batch_id}/status"
```

## 📁 文件格式详解

### JSON 格式示例

**格式1: 直接数组**
```json
[
  {
    "call_id": "call_001",
    "transcript": "销售：您好，我是益盟操盘手专员...",
    "customer_id": "customer_001",
    "sales_id": "sales_001"
  },
  {
    "call_id": "call_002",
    "transcript": "销售：我们有BS买卖点功能..."
  }
]
```

**格式2: calls包装**
```json
{
  "calls": [
    {
      "call_id": "call_001",
      "transcript": "销售通话内容..."
    }
  ]
}
```

**格式3: 单个对象**
```json
{
  "call_id": "single_call",
  "transcript": "单个通话记录...",
  "metadata": {"source": "manual_input"}
}
```

### CSV 格式示例

```csv
call_id,transcript,customer_id,sales_id,call_time
call_001,"销售：您好，我是益盟操盘手专员。客户：好的。",cust_001,sales_001,2024-01-01T10:00:00
call_002,"销售：我们的BS买卖点功能很强大。客户：听起来不错。",cust_002,sales_002,2024-01-01T11:00:00
```

### TXT 格式示例

**单通话文件 (call_001.txt):**
```
销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。
客户：你好。
销售：是这样的，我们是腾讯投资的上市公司，专门为股民提供专业的分析服务。
客户：好的，你说吧。
```

**多通话文件（使用分隔符）:**
```
销售：第一通电话内容...
客户：好的。

---

销售：第二通电话内容...
客户：了解。
```

### JSONL 格式示例

```jsonl
{"call_id": "call_001", "transcript": "第一通通话记录..."}
{"call_id": "call_002", "transcript": "第二通通话记录..."}
{"call_id": "call_003", "transcript": "第三通通话记录..."}
```

## 🔧 API 接口详解

### 1. 批量文件处理接口

**端点**: `POST /analyze/batch/files`

**请求体**:
```json
{
  "batch_id": "batch_20241024_001",
  "files": [
    {
      "source_filename": "calls.json",
      "file_size_bytes": 10240,
      "parse_status": "success",
      "calls": [
        {
          "call_id": "call_001",
          "transcript": "通话内容..."
        }
      ],
      "parse_warnings": [],
      "parsed_at": "2024-01-24T10:30:00"
    }
  ],
  "config": {
    "enable_vector_search": true,
    "enable_llm_validation": true,
    "confidence_threshold": 0.6
  },
  "processing_options": {
    "continue_on_error": true,
    "max_concurrency": 3,
    "result_storage": "local"
  }
}
```

**响应体**:
```json
{
  "batch_id": "batch_20241024_001",
  "status": "success",
  "files": [
    {
      "source_filename": "calls.json",
      "status": "success",
      "results": [...],
      "metrics": {
        "call_count": 10,
        "processing_duration_seconds": 15.3,
        "average_confidence": 0.78
      },
      "processed_at": "2024-01-24T10:45:00",
      "result_file_path": "./batch_results/batch_001/calls.analysis.json"
    }
  ],
  "statistics": {
    "total_files": 1,
    "successful_files": 1,
    "failed_files": 0,
    "total_calls_processed": 10,
    "total_duration_seconds": 20.1,
    "overall_success_rate": 1.0
  },
  "processing_start_time": "2024-01-24T10:30:00",
  "processing_end_time": "2024-01-24T10:30:20"
}
```

### 2. 其他关键接口

- **查询状态**: `GET /analyze/batch/{batch_id}/status`
- **下载结果**: `GET /analyze/batch/{batch_id}/download/{filename}`
- **清理批次**: `DELETE /analyze/batch/{batch_id}`
- **获取配置**: `GET /analyze/batch/config`
- **清理过期**: `POST /analyze/batch/cleanup-expired`

## ⚙️ 配置参数

### 环境变量配置

在 `.env` 文件中添加：

```bash
# 批量处理配置
BATCH_MAX_FILES=20                    # 每批次最大文件数
BATCH_MAX_CALLS=2000                  # 每批次最大通话数
BATCH_MAX_FILE_SIZE_MB=200            # 单文件最大大小(MB)
BATCH_MAX_CONCURRENCY=3               # 最大并发处理文件数
BATCH_RESULT_STORAGE_PATH=./batch_results  # 结果存储路径
BATCH_RESULT_RETENTION_HOURS=24       # 结果保留时长(小时)
BATCH_ENABLE_PROGRESS_TRACKING=true   # 启用进度跟踪
BATCH_ENABLE_AUTO_CLEANUP=true        # 启用自动清理过期结果
```

### Dashboard 配置选项

在Streamlit界面的侧边栏中可配置：

- **跳过错误文件继续处理**: 单文件失败时是否继续处理其他文件
- **最大并发文件数**: 1-5个文件并发处理
- **启用结果持久化存储**: 是否保存结果到服务器

## 📈 性能优化建议

### 1. 文件准备优化
- **文件大小**: 单文件控制在50MB以内可获得最佳性能
- **通话数量**: 每个文件100-500条通话记录为最佳
- **编码格式**: 使用UTF-8编码，避免编码转换开销
- **文件格式**: JSON格式解析最快，CSV次之，TXT最慢

### 2. 批次规划优化
- **并发数量**: 根据服务器性能调整，建议2-5个并发
- **批次大小**: 每批次10-15个文件，总通话数控制在1000以内
- **时间规划**: 避免高峰时段提交大批量任务

### 3. 系统资源优化
- **内存**: 确保系统可用内存 > 2GB
- **存储**: 预留足够磁盘空间存储结果文件
- **网络**: 稳定的网络连接，避免上传中断

## 🚨 错误处理与故障排除

### 常见错误及解决方案

**1. 文件解析失败**
- **错误**: `JSON格式错误`
- **解决**: 检查JSON语法，使用在线JSON验证工具
- **建议**: 使用标准的JSON格式化工具生成文件

**2. 文件大小超限**
- **错误**: `文件大小 XXX MB 超过限制 200MB`
- **解决**: 分割大文件或压缩文件内容
- **建议**: 使用JSONL格式可以更容易分割

**3. 通话数量超限**
- **错误**: `总通话数量 XXX 超过限制 2000`
- **解决**: 减少文件数量或分批次处理
- **建议**: 按时间段或客户群体分批处理

**4. API超时**
- **错误**: `请求超时`
- **解决**: 减少批次大小，检查网络连接
- **建议**: 大批次使用异步处理模式

**5. 内存不足**
- **错误**: `内存使用过高`
- **解决**: 重启服务，减少并发数量
- **建议**: 监控服务器内存使用情况

### 日志查看

```bash
# 查看API服务器日志
tail -f logs/app.log | grep batch

# 查看特定批次的处理日志
grep "batch_20241024_001" logs/app.log
```

## 🔒 安全考虑

### 1. 文件安全
- 系统会验证文件类型和大小
- 不执行文件中的任意代码
- 自动清理临时文件

### 2. 数据隐私
- 结果文件存储在本地服务器
- 支持自动清理过期数据
- 不会外传敏感通话内容

### 3. 访问控制
- API接口需要在内网环境使用
- 支持设置结果文件访问权限
- 建议配置防火墙规则

## 🔧 维护与监控

### 1. 定期维护
```bash
# 手动清理过期批次结果
curl -X POST "http://localhost:8000/analyze/batch/cleanup-expired"

# 检查磁盘使用情况
du -sh batch_results/

# 检查服务状态
curl -X GET "http://localhost:8000/health"
```

### 2. 监控指标
- **处理成功率**: 目标 > 95%
- **平均处理时间**: < 30秒/100条通话
- **系统资源使用**: 内存 < 80%, CPU < 70%
- **存储空间**: 保持 > 20% 可用空间

### 3. 性能基准
- **小批次** (5文件/500通话): < 60秒
- **中批次** (10文件/1000通话): < 150秒
- **大批次** (20文件/2000通话): < 300秒

## 📞 技术支持

如遇到问题，请提供以下信息：

1. **错误信息**: 完整的错误提示和堆栈跟踪
2. **文件信息**: 文件格式、大小、通话数量
3. **系统环境**: 操作系统、Python版本、可用内存
4. **日志片段**: 相关的应用日志内容

联系方式: 提交issue到项目GitHub仓库

---

*最后更新: 2024-01-24*
*版本: v1.1.0*