# Mining Risk Agent — 使用说明（已重写）

本 README 已重写为可运行与演示优先的说明文件。去除原始 README 中不一致或误导性的内容，聚焦如何在本地启动、演示与排查常见问题。

## 一、概览

这是一个演示级的“工矿企业风险预警智能体”项目，包含：
- FastAPI 后端（api/）—— 提供决策、数据管理、知识库、模型迭代等接口；
- React + Vite 前端（frontend/）—— 演示用 Dashboard（4 个标签页）；
- 演示优先的 Mock 回退：当模型或外部 LLM 不可用时，系统会返回结构化 Mock 响应，保证前端演示不中断。

## 二、快速启动（开发模式）

先决条件：Python 3.10+, Node.js（含 npm）。

1. 克隆仓库并进入目录：

```bash
git clone <repo-url>
cd new_version_of_mining_security-main
```

2. 后端（推荐在命令行/PowerShell/CMD）：

```bash
python -m api.main
# 或
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

3. 前端（另开终端）：

```bash
cd frontend
npm install
npm run dev   # 监听 http://localhost:5173
```

4. 访问：
- 开发模式前端： http://localhost:5173
- 前端容器/生产打包后（默认文档）： http://localhost:8501
- 后端 OpenAPI： http://localhost:8000/docs
- 健康检查： http://localhost:8000/health

提示：仓内提供 `start_backend_cmd.bat` 与 `start_frontend_cmd.bat` 以便在 Windows CMD 下快速启动。

## 三、重要说明

- /health 返回的 version 来自 `config.yaml` 的 `project.version`，前端 StatusBar 与 Sidebar 使用该字段显示运行时版本。
- 前端会定期调用 `/api/v1/iteration/status` 来显示迭代状态；若后端未加载 iteration 子模块，后端会提供安全回退响应（前端显示“无法获取迭代状态”或本地回退文本）。
- 决策相关接口（/api/v1/agent/*）在决策模块不可用时会返回结构化 Mock（含 march_result/monte_carlo_result/three_d_risk 字段），以满足前端展示需求。

## 四、关键接口速查

- GET  /health — 返回 {status, version}
- POST /api/v1/agent/decision — 触发决策工作流（或 Mock 回退）
- POST /api/v1/agent/decision/stream — SSE 流式节点状态（text/event-stream）
- POST /api/v1/agent/scenario/{scenario_id} — 切换场景（chemical/metallurgy/dust）
- GET  /api/v1/iteration/status — 查询模型迭代状态（可能为回退响应）
- POST /api/v1/iteration/trigger — 手动触发迭代（回退接口会返回不可用信息）

管理接口（如写知识库、LLM 配置）需要 `X-Admin-Token`（环境变量 MRA_ADMIN_TOKEN）。

## 五、常见问题与排查

- 前端提示找不到 ./data/demoData：已修复（frontend/src/demoData.ts），请确保你在 frontend 中执行 `npm install` 并 `npm run dev`。
- 后端启动因日志目录/权限失败：logger 已做容错，若出现文件写入错误，检查 `logs/` 权限或禁用文件日志。
- /api/v1/iteration/status 返回 404 或内容为“无法获取迭代状态”：这是回退行为。要恢复真实迭代状态，请确保 `iteration` 模块的依赖与数据准备完备并无导入错误（检查后端启动日志）。

## 六、开发与提交

- 代码已针对演示做了若干稳定性修复（路由按模块单独导入、agent/iteration 回退、前端 demoData 引入、StatusBar/Sidebar 显示 runtime version）。
- 若需提交更改，本地环境可能缺少 pwsh，建议使用普通 git CLI：

```bash
git add -A
git commit -m "Fix: update README and add runtime fallbacks"
```

---
