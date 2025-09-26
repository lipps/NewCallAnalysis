# 批量文件通话分析扩展需求说明（Streamlit & API 版本）

## 1. 背景与目标
- **业务背景**：运营团队需要在 Dashboard 中上传多个通话文本（JSON/CSV/TXT），并希望系统能对每个文件独立分析并返回对应的结果文件，避免手动拆分汇总结果。
- **技术背景**：后端现有 `SimpleCallAnalysisWorkflow.execute_batch` 支持批量处理 `CallInput` 列表；FastAPI 提供 `/analyze`（单次）与 `/analyze/batch`（后台任务）接口；Streamlit `render_batch_analysis` 目前仅为占位提示。
- **目标**：在不改动核心工作流/引擎的前提下，扩展 API 与 Dashboard，实现“多文件上传→逐文件分析→逐文件下载”的闭环体验，并兼顾错误溯源与运行可观测性。

## 2. 当前现状
- **工作流能力**：`SimpleCallAnalysisWorkflow.execute_batch`（`src/workflows/simplified_workflow.py:178`）已具备并发执行与异常兜底，只需重复调用即可处理多个文件。
- **API 层**：`/analyze/batch` 以后台任务形式运行，但缺乏结果持久化与查询机制，暂无法为前端同步获取分析结果提供支撑。
- **前端**：`render_batch_analysis`（`src/dashboard/streamlit_app.py:730`）已经提供多文件上传组件，但按钮逻辑仅提示“开发中”。
- **数据契约**：`CallInput`/`CallAnalysisResult`（`src/models/schemas.py`）定义完善，支持 `dict()` 序列化；批量输入结构 `BatchAnalysisInput` 已可复用。

## 3. 需求范围
- **包含**：
  1. 新增同步批量分析 API（或完善现有异步路径），支持一次请求返回多个文件的分析结果；
  2. Streamlit 批量上传流程，包括文件解析、调用 API、展示进度、结果下载；
  3. 结果按源文件拆分保存/导出，提供失败提示与重试引导；
  4. 日志、监控、配置项补齐。
- **不包含**：
  - 引擎/模型能力变更；
  - 大规模异步调度、任务队列的实现；
  - 将结果持久化至数据库或外部存储（可作为后续扩展）。

## 4. 详细功能需求
### 4.1 文件解析与输入标准化
- 支持文件类型：`.json`、`.jsonl`、`.csv`、`.txt`。
- **JSON**：兼容以下结构：
  - `List[CallInput]`；
  - `{"calls": [...]}`；
  - 单个 `CallInput` 对象（视为单条通话）。
- **CSV**：要求存在至少 `transcript` 列，其他列（`call_id/customer_id/sales_id/call_time`) 可选；没有 `call_id` 时在加载时自动生成。
- **TXT**：默认“一文件一通话”；如需支持多条，需明确分隔符或格式约定。
- 解析失败时记录文件名、失败原因，支持配置：
  - `continue_on_error=true`（默认）：跳过失败文件；
  - `fail_fast=true`：出错即终止并返回错误。

### 4.2 后端接口扩展
- 新增 `POST /analyze/batch/sync`（示例命名），请求体示例：
  ```json
  {
    "batch_id": "20241024-001",
    "files": [
      {
        "source_name": "李某案001.txt",
        "calls": [CallInput, ...]
      }
    ],
    "config": { ... 可选 ... }
  }
  ```
- 响应体：
  ```json
  {
    "batch_id": "20241024-001",
    "files": [
      {
        "source_name": "李某案001.txt",
        "status": "success",
        "result": [CallAnalysisResult, ...],
        "metrics": {
          "call_count": 12,
          "duration_seconds": 8.2,
          "avg_confidence": 0.74
        }
      },
      {
        "source_name": "张某案002.json",
        "status": "failed",
        "error": "解析失败: JSON 格式错误"
      }
    ],
    "statistics": {
      "total_files": 3,
      "successful": 2,
      "failed": 1,
      "total_calls": 120,
      "duration_seconds": 45.3
    }
  }
  ```
- 保留现有异步 `/analyze/batch`；如需异步处理，扩展 `/tasks/{task_id}` 查询接口（可选）。
- 统一在 `src/models/schemas.py` 中定义新模型：`BatchFileInput`、`BatchFileResult`、`BatchFileResponse`。

### 4.3 结果保存策略
- **默认（前端下载）**：Streamlit 接收响应后按文件创建 `BytesIO`，命名 `<源文件名>.analysis.json`，通过 `st.download_button` 提供下载。
- **可选（后端落盘）**：在 API 中写入 `results/<batch_id>/<source_name>.json` 并返回下载 URL；需要设置保留时长及清理脚本。

### 4.4 Streamlit 交互流程
1. 上传后展示文件列表（序号、名称、大小、预估通话条数）。
2. “开始批量分析”按钮：
   - 若采用同步 API：一次提交所有文件，显示 `st.spinner` 与实时统计。
   - 若采用异步 API：提交后进入轮询模式，利用 `st.session_state` 保存 `task_id` 并定时刷新进度。
3. 单文件结果卡片：
   - 成功：显示 `call_count`、平均置信度、TOP N 命中项；提供下载。
   - 失败：显示错误信息，提供“重新分析”按钮（仅提交该文件）。
4. 汇总面板：展示成功率、总耗时、各模块平均耗时，配合图表（可复用 Plotly 组件）。
5. 允许用户导出汇总索引（JSON/CSV），包含每个文件的状态与统计。

### 4.5 配置与可扩展性
- `.env` 可新增：
  - `BATCH_MAX_FILES=20`
  - `BATCH_MAX_CALLS=2000`
  - `BATCH_CONTINUE_ON_ERROR=true`
  - `BATCH_RESULT_STORAGE=LOCAL|MEMORY`
- Streamlit 侧可在 Sidebar 新增设置：最大并发、是否启用向量检索/LLM（复用现有开关）。

### 4.6 日志与监控
- API：每个文件输出日志 `batch=<id> file=<name> calls=<n> duration=<s> status=<success|failed>`。
- Streamlit：将进度写入 `st.status` 或 `st.write`，便于用户观察；失败时弹出 `st.error`。
- 若部署在生产，可将统计信息上报至现有监控系统，追踪批量任务耗时分布。

## 5. 非功能性需求
- **性能**：确保单批不重复初始化向量/LLM 引擎；当文件较多时分批提交（可配置批量大小）。
- **可靠性**：出现网络或服务异常时，给出明确提示并允许重试；保留部分成功结果。
- **安全性**：限制单文件最大 200 MB；在后端对上传内容做二次校验，避免执行任意代码；清理临时文件。
- **可维护性**：核心解析与执行逻辑抽离至独立模块，编写单元测试；响应模型统一维护在 `schemas`。

## 6. 边界情况
- 所有文件为空或解析失败 → 返回 `BatchFileResponse`，`statistics.successful=0`，Streamlit 显示“全部失败”的警告。
- 文件名重复 → 允许，但下载时需附加时间戳或索引防止覆盖。
- 单个文件 `CallInput` 数量巨大 → 允许，但超过 `BATCH_MAX_CALLS` 时提前阻断并提示。
- 引擎降级（向量/LLM 关闭）→ 仍返回结果，但在 `files[].result` 中添加 `warnings` 字段，提示命中率可能受影响。

## 7. 测试计划
- **单元测试**：
  - 文件解析函数覆盖正常/异常路径；
  - API handler 在 mock workflow 下验证 `success`/`failed` 返回；
  - Streamlit 辅助函数验证下载内容、状态更新。
- **集成测试**：
  - 本地启动 FastAPI + Streamlit，上传 3 个文件（含 1 个错误文件），确认前端结果展示正确；
  - 压测大文件（>100 通话）以验证性能和日志输出。
- **回归测试**：
  - 确保原有单次分析、CLI 批处理仍能正常使用。

## 8. 开发步骤与里程碑
1. 明确 API 请求/响应模型，评审接口设计。
2. 实现文件解析与标准化工具（后端 + 前端共享）。
3. 编写同步批量接口逻辑与统计信息收集。
4. 更新 Streamlit 批量分析页面，加入进度与下载。
5. 编写/更新自动化测试与 README 文档。
6. 联调验证，处理边界场景，准备上线。

## 9. 待确认问题
- 是否需要历史批次列表（需后端存储支持）？
- TXT 文件是否可能包含多通话？若是，需要额外字段或语法解析方案。
- 上传文件量是否会超出 Streamlit 当前 200 MB 限制？如需更大，需要调整部署策略。

## 10. 参考资料
- `src/workflows/simplified_workflow.py`
- `src/api/main.py`
- `src/dashboard/streamlit_app.py`
- `src/models/schemas.py`
- 示例输出：`batch_demo_results.json`

## 11. 需求不合理之处

-  1. 同步API的超时风险:
-    - 问题：大批量文件的同步处理可能导致HTTP超时
-    - 建议：采用异步+轮询模式，或实现流式响应
-  2. 内存安全问题:
-    - 问题：20个文件×2000通话可能消耗过多内存
-    - 建议：实现流式处理和分批加载
-  3. 结果持久化策略模糊:
-    - 问题：内存存储在并发场景下不安全
-    - 建议：必须实现持久化存储