本补丁包将 Gemini CLI 深度集成到 Cursor：
- A: `cursor.rules` —— 让智能建议默认优先推荐 Gemini 用于大代码库分析
- B: `.vscode/tasks.json` —— 在 Cursor/VSCode 内一键运行常用 Gemini 命令
- C: `mcp-gemini-cli/server.js` —— 将 Gemini CLI 变成 MCP 工具，供 Agent 自动调用


## 先决条件
- 系统已安装 **Gemini CLI**，并且 `gemini` 在 PATH 中可用
- 已安装 Node.js (≥16)


## 安装
1. 将本补丁包复制到你的仓库根目录（与 `README.md` 同级）
2. 赋予执行权限（Mac/Linux）：
```bash
chmod +x mcp-gemini-cli/server.js