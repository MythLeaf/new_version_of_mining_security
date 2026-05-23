# 当前前端页面全量要素清单

本文档用于向 AI 完整说明当前项目前端长什么样、有哪些功能、页面、组件、交互、图表、表格、配色和接口，方便后续在不丢功能的前提下重构更美观的前端。

盘点对象：`new_version_of_mining_security/frontend` 下的当前 React + Vite 前端，主入口是 `frontend/src/main.tsx` 和 `frontend/src/App.tsx`。

## 1. 技术栈与入口

### 主技术栈

| 类别 | 当前使用 |
|---|---|
| 框架 | React 18 + TypeScript |
| 构建工具 | Vite 5 |
| 图表库 | ECharts 5、echarts-for-react、echarts-gl |
| 样式 | 单文件全局 CSS：`frontend/src/styles/scada.css` |
| 路由 | 没有使用 React Router，使用 App 内部 `activeTab` 状态切换页面 |
| 图标 | 主要使用 Emoji 作为页面、按钮、标签和状态图标 |
| API | 原生 `fetch`，封装在 `frontend/src/api/client.ts` |

### 入口文件

- `frontend/src/main.tsx`：挂载 React 根组件，引入全局样式 `scada.css`。
- `frontend/src/App.tsx`：应用总壳，负责健康检查、场景切换、顶部状态栏、侧栏和主标签页切换。
- `frontend/vite.config.ts`：开发服务器端口 `5173`，将 `/api` 与 `/health` 代理到 `VITE_DEV_API_TARGET`，默认 `http://localhost:8000`。

### 应用主标签页

`App.tsx` 内定义 5 个一级标签页：

| Tab ID | 页面标题 | 对应组件 |
|---|---|---|
| `risk` | 🎯 企业风险预测 | `RiskPredictionPage` |
| `visualization` | 📈 数据可视化 | `VisualizationPage` |
| `knowledge` | 📚 知识库与记忆系统 | `KnowledgeMemoryPage` |
| `iteration` | 🔄 模型迭代与CI/CD | `IterationPage` |
| `config` | ⚙️ 系统配置与API文档 | `SystemConfigPage` |

## 2. 全局布局

### 顶部状态栏

组件：`frontend/src/components/StatusBar.tsx`

显示要素：

- 在线状态圆点：绿色表示 `SYS ONLINE`，红色表示 `SYS OFFLINE`。
- 后端版本号：显示 `v{version}`，无版本时显示 `v—`。
- 当前业务场景：`场景: 危险化学品 / 冶金 / 粉尘涉爆`。
- 当前时间：每秒刷新，24 小时制中文时间。

交互与数据：

- `App.tsx` 首次加载调用 `fetchHealth()`，并每 30 秒刷新一次健康状态。

### 左侧侧栏

组件：`frontend/src/components/Sidebar.tsx`

显示要素：

- 标题：`🛡️ 风险预警智能体`
- 副标题：`SCADA DASHBOARD v1.0`
- 后端状态：`后端服务正常` 或 `后端离线 (Mock)`，带状态圆点。
- 场景配置下拉框：
  - `🧪 危险化学品`
  - `🔩 冶金`
  - `💨 粉尘涉爆`
- 系统状态：
  - 当前迭代状态中文名或英文状态。
  - 待审批数量，例如 `⏳ 待审批: 1 项`。
  - 无审批时显示 `无待审批事项`。
- 路演控制：
  - 复选框：`演示模式`
  - 开启后显示 `✨ 自动轮播已启用`
- 底部提示：
  - `Harness 工程化管控`
  - `推荐 1920×1080 投影`

接口：

- 场景切换调用 `POST /api/v1/agent/scenario/{scenarioId}`。
- 迭代状态调用 `GET /api/v1/iteration/status`。

### 主内容区

结构：

- 顶部为一级标签页按钮条。
- 内容区域根据 `activeTab` 条件渲染对应页面组件。
- 主内容区背景为深色工业监控风，带轻微径向蓝色光效。

## 3. 全局设计系统

### 视觉风格

当前前端是“深色 SCADA 工业控制室 / 风险监控大屏”风格：

- 深色背景。
- 卡片化信息面板。
- 蓝、青、绿、红、橙、黄作为状态和风险色。
- 大量发光文字、边框、阴影、脉冲动画。
- 信息密度高，适合投屏演示和后台监控。

### 核心配色

CSS 变量定义在 `frontend/src/styles/scada.css`：

| 用途 | 色值 |
|---|---|
| 最深背景 | `#060a14` |
| 深背景 | `#0a0e1a` |
| 面板背景 | `#0f172a` |
| 卡片背景 | `#141c2e` |
| 卡片 Hover | `#1a2540` |
| 输入框背景 | `#0c1220` |
| 暗边框 | `#1e293b` |
| 中亮边框 | `#2d3a4f` |
| 亮边框 | `#3b4f6b` |
| 主文本 | `#f1f5f9` |
| 次文本 | `#94a3b8` |
| 弱文本 | `#64748b` |
| 蓝色强调 | `#3b82f6` |
| 青色强调 | `#06b6d4` |
| 绿色成功 | `#10b981` |
| 黄色/琥珀 | `#f59e0b` |
| 橙色风险 | `#f97316` |
| 红色风险 | `#ef4444` |
| 紫色 | `#8b5cf6` |

风险等级配色：

| 等级 | 色值 | 语义 |
|---|---|---|
| 红 | `#ef4444` | 极高风险，立即处置 |
| 橙 | `#f97316` | 高风险，限期整改 |
| 黄 | `#eab308` | 中等风险，加强监控 |
| 蓝 | `#3b82f6` | 低风险，常规巡检 |

### 字体

- 普通文本：`Inter`, `Noto Sans SC`, `PingFang SC`, `Microsoft YaHei`, sans-serif。
- 数字、ID、代码：`JetBrains Mono`, `Roboto Mono`, `SF Mono`, monospace。
- CSS 中通过 Google Fonts 引入 `Inter` 和 `JetBrains Mono`。

### 通用组件与样式类

| 类型 | 类名/组件 | 用途 |
|---|---|---|
| 卡片 | `ScadaCard` / `.scada-card` | KPI 和面板容器 |
| 标签页 | `Tabs` / `.tabs-bar` / `.tab-button` | 一级 Tab |
| 子标签 | `.sub-tab-bar` / `.sub-tab` | 页面内二级 Tab |
| 表单 | `.scada-input` / `.scada-textarea` / `.scada-select` | 输入框、文本域、下拉 |
| 按钮 | `.scada-btn` | 主按钮 |
| 次按钮 | `.scada-btn.secondary` | 次级按钮 |
| 危险按钮 | `.scada-btn.danger` | 危险操作 |
| 成功按钮 | `.scada-btn.success` | 成功操作 |
| 表格 | `.scada-table` | 数据表格 |
| 标签 | `.tag`、`.tag-red` 等 | 状态、分类、等级标签 |
| 时间线 | `.timeline-container` / `.timeline-node` | 工作流节点日志 |
| 校验卡 | `.validation-card` | MARCH、蒙特卡洛、三维风险校验 |
| JSON | `JsonView` / `.json-code-block` | 原始 JSON 展示 |
| 空状态 | `.empty-state` | 无数据提示 |
| 加载 | `.tech-spinner` | 科技感 Spinner |
| 分页 | `.pagination` 或内联分页按钮 | 上一页/下一页 |
| 进度条 | `.scada-progress-track` / `.scada-progress-fill` | 灰度比例、流水线进度 |

### 动效

- 在线状态点绿色呼吸动画：`breathe-green`。
- 红色风险卡片脉冲：`risk-red-pulse`。
- 蓝色运行节点脉冲：`pulse-blue`。
- 卡片 hover 上浮和蓝色光晕。
- 进度条 shimmer 扫光。
- ECharts 3D 曲面自动旋转。

## 4. 页面一：企业风险预测

文件：`frontend/src/pages/RiskPredictionPage.tsx`

页面标题：

- `🎯 企业风险预测 — 上传数据 → 模型预测 → 决策建议 → 三重风控拦截`

### 左侧输入面板

功能与控件：

| 控件 | 类型 | 说明 |
|---|---|---|
| 企业 ID | 输入框 | 默认 `ENT-DEMO-001` |
| 当前场景 | 只读文本 | 显示危险化学品 / 冶金 / 粉尘涉爆 |
| 🎲 模拟数据填充 | 按钮 | 将当前场景的 demo JSON 写入文本域 |
| 企业数据（JSON） | 文本域 | 用于输入企业数据 JSON |
| 或上传 CSV/Excel | 文件上传 | 支持 `.csv`, `.xlsx`, `.xls` |
| 上传状态 | 文本提示 | 显示上传失败或 `已加载 X 行 × Y 列` |
| 使用 SSE 实时节点流 | 复选框 | 默认开启 |
| 🚀 执行预测 | 主按钮 | 加载时显示 `执行中...` |
| 错误提示 | Alert | JSON 格式错误、后端无响应等 |

接口：

- `POST /api/v1/data/upload`：上传 CSV/Excel。
- `POST /api/v1/agent/decision/stream`：SSE 工作流节点流。
- `POST /api/v1/agent/decision`：普通预测请求，SSE 失败后回退。

降级：

- 后端无响应时显示错误，并调用本地 `generateMockDecision()` 生成 Mock 决策。

### 右侧结果区状态

| 状态 | 展示 |
|---|---|
| 初始空状态 | `👈 在左侧输入企业数据并点击「执行预测」查看结果` |
| 加载中 | Spinner + `SYSTEM INITIALIZING WORKFLOW...` |
| SSE 过程中 | `📡 SSE 实时节点` 卡片 + Timeline |
| 完成后 | 决策详情视图 |

### 决策摘要卡

显示：

- 企业 ID。
- 当前场景名称。
- `MOCK` 标签。
- 大号风险等级：`红级风险 / 橙级风险 / 黄级风险 / 蓝级风险`。
- 最终状态标签：如 `APPROVE`、`HUMAN_REVIEW`、`REJECT`。
- 红级风险时卡片边框和脉冲动画增强。

### KPI 卡片

4 个 ScadaCard：

| 标题 | 内容 |
|---|---|
| 判定状态 | `final_status` |
| 判定置信度 | 最大概率百分比 |
| 三维风险 | `three_d_risk.risk_level`，副标题 `score=...` |
| 蒙特卡洛 | `monte_carlo_result.confidence`，副标题 `valid x/y` |

### 风险评分与等级分析

模块标题：`🎯 风险评分与等级分析`

包含 3 个并排卡片：

| 卡片 | 图表/元素 | 说明 |
|---|---|---|
| 综合风险评分 | ECharts Gauge | 0 到 1 风险仪表盘，颜色从绿到红 |
| 三维风险曲面 | ECharts GL 3D Surface + Scatter3D | 维度：严重性、相关性、不可逆性，自动旋转 |
| 风险因子贡献度 | 横向进度条列表 | 取 SHAP Top5，正贡献红色，负贡献绿色 |

风险等级配置：

- 红色预警：`≥ 0.80`，极高风险，需立即处置。
- 橙色预警：`0.60-0.79`，高风险，需限期整改。
- 黄色预警：`0.40-0.59`，中等风险，需加强监控。
- 蓝色预警：`0.20-0.39`，低风险，常规巡检。

### 风险分析报告

显示：

- 企业 ID。
- 预测等级。
- 综合评分。
- 根因分析。
- 三维风险评估结果：严重性、相关性、不可逆性、总分、是否触发拦截。
- 红级风险额外提示：立即启动应急响应、人员撤离、设备断电、通知属地应急管理部门。
- 橙级风险额外提示：限期整改、72 小时专项检查、加强设备监控。

### 概率分布图

组件：`ProbabilityChart`

- ECharts 环形饼图。
- 中心显示判定等级。
- 图例数据来自 `probability_distribution`。
- 颜色按红橙黄蓝风险等级映射。

### SHAP 归因图

组件：`ShapChart`

- ECharts 横向柱状图。
- 默认 Top5。
- 正贡献为红色，负贡献为绿色。
- Y 轴显示特征名，柱尾显示贡献值。

### 决策建议

双列卡片：

1. `🏛️ 政府干预建议`
   - 主责部门名称。
   - 联系角色。
   - 主责行动。
   - 行动清单。
   - 处置期限小时数。

2. `🏭 企业管控建议`
   - 设备 ID。
   - 操作建议。
   - 参数 JSON。
   - 人员行动清单。

### 风控拦截状态

3 个校验卡片：

| 卡片 | 通过/拦截依据 |
|---|---|
| MARCH 三重隔离校验 | `march_result.passed` |
| 蒙特卡洛置信采样 | `monte_carlo_result.passed` |
| 三维风险评估 | `three_d_risk.blocked === false` 表示通过 |

每个卡片显示：

- `✅ 通过` 或 `❌ 拦截`。
- detail 文本。
- retry、confidence、threshold、reason 等额外信息。

### 折叠详情

- `📡 SSE 实时日志（工作流节点执行状态）`
  - 时间线节点：completed 显示 ✓，failed 显示 ✗，running 显示 ⟳。
  - 节点名和详情。
- `🔍 原始决策 JSON`
  - 使用 `JsonView` 展示完整决策对象。

## 5. 页面二：数据可视化

文件：`frontend/src/pages/VisualizationPage.tsx`

页面标题：

- `📈 数据可视化仪表盘`
- 副标题：`基于真实企业数据的统计分析图表 | Data Visualization Dashboard`

### 加载与错误状态

- 加载态：`📊 正在加载数据可视化图表...`
- 错误态：红色边框错误框，显示 `错误: ...`

### 首屏数据图表

页面加载时并发请求 8 个接口：

- `GET /api/v1/visualization/trend`
- `GET /api/v1/visualization/scatter`
- `GET /api/v1/visualization/heatmap`
- `GET /api/v1/visualization/enterprise-stats`
- `GET /api/v1/visualization/module-trend`
- `GET /api/v1/visualization/storage-trend`
- `GET /api/v1/visualization/category-priority-heatmap`
- `GET /api/v1/visualization/enterprise-category-heatmap`

图表顺序：

1. `三模块时间趋势对比（预警生成 / 入库 / 分类关联）`
   - 折线图。
   - 支持 dataZoom 拖拽缩放。
   - 三条线：预警生成、入库数量、分类关联。

2. `2024-2025年矿山安全预警生成趋势`
   - 折线图。
   - 系列：预警总数、高风险预警、中风险预警、低风险预警。
   - 有平均值 markLine 和峰值 markPoint。

3. `文件入库时间趋势`
   - 折线图。
   - 系列：入库总数、已处理、待处理。
   - 支持 dataZoom。
   - 显示平均入库线。

4. `相关性散点图`
   - 散点图 + 趋势线 + 均值星标。
   - 右侧 visualMap 按 Y 维度着色。
   - 左上角显示相关系数。

5. `矿山安全指标相关性热力图`
   - 相关矩阵热力图。
   - 底部 visualMap 从负相关到正相关。
   - 下方列出强相关变量对。

6. `分类×优先级关联热力图`
   - X 轴优先级，Y 轴分类。
   - 单元格显示关联强度。

7. `企业×分类关联热力图`
   - X 轴分类，Y 轴企业。
   - 单元格显示关联强度。

### 数据概览卡

根据已加载数据显示：

- 预警趋势数据：天数、总预警次数。
- 相关性分析样本：企业数量、相关系数。
- 安全指标维度：指标数量、强相关组数。
- 三模块趋势数据：天数、支持拖拽缩放。

### 企业深度数据挖掘分析

标题：`🏭 企业深度数据挖掘分析`

副标题说明基于 `new_data` 数据库，按企业名称长度降序。

#### 核心指标卡片

6 个 KPI：

- 企业总数
- 高危企业
- 平均安全评分
- 年度检查次数
- 违规次数
- 合规率

#### 模型统计指标卡片

5 个 KPI：

- 累计样本数
- F1 分数
- 模型准确率
- 召回率
- 精确率

#### 企业统计图表

| 标题 | 图表类型 | 内容 |
|---|---|---|
| 企业行业分布 | 环形饼图 | 行业名称、数量、百分比 |
| 季度风险等级分布趋势 | 堆叠柱状图 | 风险等级随季度变化 |
| 企业规模分布 | 横向柱状图 | 企业规模区间、数量、占比 |
| 安全评分分布 | 柱状直方图 | 安全评分区间 |
| 月度综合趋势分析 | 多折线图 | 企业数量、风险事件、安全检查、违规次数 |
| TOP 8 高风险企业预警 | 表格 | 排名、企业名称、行业类型、风险评分、风险等级、事故次数 |

TOP 8 表格样式：

- 前 3 名使用红色圆形排名标识。
- 风险评分按阈值显示红、橙、黄。
- 风险等级用半透明色块标签。

## 6. 页面三：知识库与记忆系统

文件：`frontend/src/pages/KnowledgeMemoryPage.tsx`

页面标题：

- `📚 预警经验管理系统`

### 二级标签页

| Key | 标签 |
|---|---|
| `overview` | 📊 总览仪表盘 |
| `data` | 📊 数据管理 |
| `risk` | 🎯 风险评估 |
| `import` | 📥 导入预测 |
| `experience` | ⚡ 预警经验 |
| `short` | 🧠 短期记忆 |
| `long` | 💾 长期记忆 |
| `approval` | 📋 审批管理 |
| `audit` | 🔍 审计日志 |

### 通用导出面板

组件：`ExportDialog`

入口：

- 预警经验导出。
- 短期记忆导出。
- 长期记忆导出。
- 导入预测页的快捷导出。

控件：

- 标题：`📤 导出 短期记忆 / 长期记忆 / 预警经验`
- `✕ 关闭` 按钮。
- 导出格式下拉：Excel `.xlsx`、CSV `.csv`、PDF `.pdf`。
- 起始时间日期选择。
- 截止时间日期选择。
- 分类筛选下拉。
- 优先级下拉：全部、P0、P1、P2、P3。
- 企业 ID 输入框。
- `📥 执行导出` 按钮。
- 导出中显示 `导出中...`。
- 成功/失败状态 Alert。

接口：

- `POST /api/v1/memory/export`

### 6.1 总览仪表盘

按钮：

- `🔄 刷新`

接口：

- `GET /api/v1/memory/stats`
- `GET /api/v1/visualization/module-trend`

KPI 卡片：

- 记忆总量
- 短期记忆
- 长期记忆
- 预警经验
- 待审批
- 迭代次数
- 审计日志
- 财务影响(万元)

图表：

| 标题 | 类型 |
|---|---|
| 📈 三模块时间趋势对比（支持拖拽缩放） | 折线图 + dataZoom |
| 🎯 3D多维度记忆曲面 | ECharts GL 3D Surface |
| 🌐 记忆结构旭日图 | Sunburst |
| ⏱️ 系统状态仪表盘 | 双 Gauge |
| 📊 三模块分类对比（堆叠柱状图） | 堆叠柱状图 |
| 📈 优先级分布对比 | 分组柱状图 |

底部分类卡：

- `🧠 短期记忆分类`
- `💾 长期记忆分类`
- `⚡ 预警等级分布`

空状态：

- `📊 点击刷新加载统计数据`

### 6.2 数据管理

标题：`📊 数据实时更新流式清洗 Pipeline`

顶部计数标签：

- 数据表数量
- 企业数
- 长期记忆数量
- 短期记忆数量
- 预警经验数量

按钮：

- `📁 从 new_data/ 导入Excel数据`
- `🔄 刷新统计`

状态：

- 正在扫描并导入。
- 导入成功：显示行数。
- 导入失败：显示错误。

KPI 卡片：

- 记忆条目
- 数据表
- 企业数量
- 预警经验

数据源展示：

- `📁 已导入数据源`
- 使用多个 `tag-cyan` 标签展示 source 名称。

接口：

- `POST /api/v1/memory/import-new-data`
- `GET /api/v1/memory/enterprise-data-summary`
- `GET /api/v1/memory/stats`

### 6.3 风险评估

标题：`🎯 批量风险评估与预警经验生成`

按钮：

- `🚀 执行批量风险评估`
- 运行中显示 `评估中...`

接口：

- `POST /api/v1/memory/batch-assess`
- `GET /api/v1/memory/enterprise-risk-history/{enterprise_id}`

空状态：

- `🎯 点击"执行批量风险评估"开始风险分析`

图表：

| 标题 | 类型 |
|---|---|
| 📊 风险等级分布 | 饼图 |
| 📈 风险评分趋势 | 折线图，含红级/橙级阈值线 |
| 🔥 企业风险热力图 | 热力图 |
| 📈 企业风险历史 - {enterpriseId} | 企业历史折线图 |

详细表格：

标题：`📋 详细评估结果（按名称长度降序）`

列：

- 企业ID
- 企业名称
- 场景
- 风险评分
- 风险等级
- 评估时间
- 预警经验
- 历史

每行操作：

- `📈` 按钮：查看该企业风险历史。

### 6.4 导入预测

标题：`📥 Excel文件导入与预测分析`

按钮/控件：

- `🔍 选择文件进行预测分析`：隐藏文件 input，支持 `.xlsx`, `.xls`, `.csv`。
- `💾 导入到长期记忆库`：隐藏文件 input，支持 `.xlsx`, `.xls`, `.csv`。
- `📤 导出长期记忆`
- `📤 导出短期记忆`

接口：

- `POST /api/v1/memory/assess-enterprise`
- `POST /api/v1/memory/import-excel`
- `POST /api/v1/memory/export`

状态：

- 正在导入并预测。
- 成功显示分析条数、源文件总行数、生成预警经验条数。
- 未识别企业记录时显示警告和识别列提示。
- 导入长期记忆成功显示行列数。
- 导出成功/失败提示。

结果 KPI：

- 有效企业
- 红橙风险
- 平均评分
- 需关注占比

图表与表格：

| 标题 | 类型 |
|---|---|
| 📊 风险等级分布 | 饼图 |
| 📈 风险评分区间 | 分布图 |
| 🏭 Top 10 风险企业 | 图表 |
| 🧭 关键风险因子均值 | 雷达图 |
| 🚨 重点关注处置清单 | 表格 |
| 📋 场景与等级汇总 | 表格 |
| 📋 详细预测结果（按风险评分排序） | 表格 |

重点关注处置清单列：

- 企业名称
- 评分
- 等级
- 建议动作：红=立即核查，橙=限期整改，黄=持续监测，蓝=常规巡检。

详细预测结果列：

- 企业名称
- 风险评分
- 风险等级
- 场景
- 关键指标

### 6.5 预警经验

标题：`⚡ 预警经验库`

顶部元素：

- 总计标签：`总计: X 条`
- `📤 导出` 按钮
- 搜索输入：`搜索预警经验...`
- 风险等级筛选：全部等级、红色、橙色、黄色、蓝色
- `🔍 搜索` 按钮

接口：

- `GET /api/v1/memory/warning-experiences`
- `GET /api/v1/memory/stats`
- `POST /api/v1/memory/export`

KPI：

- 预警经验总数
- 红色预警
- 场景类型
- 财务影响(万元)

图表：

| 标题 | 类型 |
|---|---|
| 📊 风险等级分布 | 饼图 |
| 📈 预警生成趋势 | 折线图，带 dataZoom |
| 💰 财务影响仪表盘 | Gauge |
| 🎯 场景分布 | 柱状图 |
| 🔥 等级×场景关联热力图 | 热力图 |

列表结构：

- 每条经验是可展开卡片。
- 收起时显示：风险等级、企业名称、评分、生成时间、展开箭头。
- 展开后显示：
  - 根本原因
  - 运营影响
  - 财务影响
  - 行业基准
  - 处置措施标签
  - 关键风险因素表格

关键风险因素表格列：

- 指标
- 数值
- 风险贡献

分页：

- 页大小：20。
- 显示 `上一页`、`第 x 页 / 共 y 页`、`下一页`。

空状态：

- `⚡ 暂无预警经验，执行风险评估后自动生成`

### 6.6 短期记忆

标题：`🧠 短期记忆库`

顶部元素：

- 总计标签。
- `⬆️ 全部迁移` 按钮。
- `📤 导出` 按钮。
- 搜索输入：`搜索...`
- 分类筛选：全部分类、推理过程、预警记录、预警经验、上下文。
- `🔄 刷新` 按钮。

接口：

- `GET /api/v1/memory/short-term`
- `POST /api/v1/memory/migrate`
- `DELETE /api/v1/memory/short-term/{item_id}`
- `GET /api/v1/memory/stats`
- `POST /api/v1/memory/export`

KPI：

- 短期记忆总数
- P0 紧急
- 分类数量
- 关联企业

图表：

| 标题 | 类型 |
|---|---|
| 📊 分类分布 | 饼图 |
| 📈 优先级分布 | 柱状图 |
| 📈 入库时间趋势 | 折线图 + dataZoom |
| 🏢 企业关联TOP8 | 横向柱状图 |
| ⏱️ 记忆重要度评分 | Gauge |
| 🎯 分类关联强度散点图 | 散点图 |
| 🔥 分类×优先级关联热力图 | 热力图 |

表格列：

- 优先级
- 分类
- 内容
- 企业ID
- 时间
- 标签
- 操作

每行操作：

- `📋 详情`
- `⬆️ 迁移`
- `🗑️` 删除

分页：

- 页大小：20。
- `上一页`、页码、`下一页`。

详情弹窗：

- 标题：`📋 记忆详情`
- 关闭按钮：`✕ 关闭`
- 字段：ID、优先级、分类、类型、企业ID、时间、数据源、已验证。
- 完整内容。
- 标签。
- 行数据。

### 6.7 长期记忆

标题：`💾 长期记忆库`

顶部元素：

- 总计标签。
- `📤 导出`
- 搜索输入：`搜索...`
- 分类筛选：全部分类、企业数据、预警经验、知识库、法规标准、事故案例。
- `🔄 刷新`

接口：

- `GET /api/v1/memory/long-term`
- `GET /api/v1/memory/stats`
- `POST /api/v1/memory/export`

KPI：

- 长期记忆总数
- P0 紧急
- 分类数量
- 关联企业

图表：

| 标题 | 类型 |
|---|---|
| 📊 分类分布 | 饼图 |
| 📈 优先级分布 | 柱状图 |
| 📈 入库时间趋势 | 折线图 + dataZoom |
| 📁 数据来源TOP10 | 横向柱状图 |
| 🏢 企业关联TOP8 | 横向柱状图 |
| ⏱️ 验证覆盖率 | Gauge |
| 📦 数据源分布 | 饼图 |
| 🔥 企业×分类关联热力图 | 热力图 |
| 🔥 分类×优先级关联热力图 | 热力图 |

表格列：

- 优先级
- 分类
- 内容
- 数据源
- 企业ID
- 时间
- 已验证
- 操作

每行操作：

- `📋 详情`

分页：

- 页大小：20。
- `上一页`、页码、`下一页`。

空状态：

- `💾 长期记忆库为空`

### 6.8 审批管理

标题：`📋 管理员审批工作流`

顶部元素：

- 待审批数量标签。
- 状态筛选：全部状态、待审批、已批准、已驳回。
- `🔄 刷新`

接口：

- `GET /api/v1/memory/approvals`
- `POST /api/v1/memory/approvals/{approval_id}/decide`

表格列：

- ID
- 目标
- 操作
- 发起人
- 状态
- 创建时间
- 决策

每行操作：

- 待审批状态显示：
  - `✅ 批准`
  - `❌ 驳回`
- 已处理状态显示审批人。

空状态：

- `📋 暂无审批记录`

### 6.9 审计日志

标题：`🔍 审计日志`

顶部元素：

- 总计标签。
- 搜索输入：`搜索日志...`
- 操作筛选：
  - 全部操作
  - 数据导入
  - 批量评估
  - 企业评估
  - 记忆迁移
  - 创建审批
  - 审批决策
- `🔍 搜索` 按钮。

接口：

- `GET /api/v1/memory/audit-logs`

表格列：

- 时间
- 操作
- 操作人
- 目标
- 详情

分页：

- 页大小：30。
- `上一页`、页码、`下一页`。

空状态：

- `🔍 暂无审计日志`

## 7. 页面四：模型迭代与 CI/CD

文件：`frontend/src/pages/IterationPage.tsx`

页面标题：

- `🔄 模型迭代全生命周期管理`

### 二级标签页

| Key | 标签 |
|---|---|
| `dashboard` | 📊 迭代仪表盘 |
| `tracking` | 📈 准确性追踪 |
| `lifecycle` | 🔧 生命周期管理 |
| `approval` | 📋 审批工作流 |
| `compare` | 📑 版本对比 |
| `changelog` | 📝 变更日志 |

### 7.1 迭代仪表盘

接口：

- `GET /api/v1/iteration/status`
- `POST /api/v1/iteration/trigger`

KPI 卡片：

- 当前状态
- 累计样本
- F1 分数
- 待审批

图表与面板：

| 标题 | 类型/元素 |
|---|---|
| 📈 F1分数趋势 | 折线图 |
| 🚀 灰度流量比例 | 进度条 |
| 审批状态 | 待审批版本标签 |
| 📜 版本历史 | 表格 |
| ▶️ 触发模拟迭代 | 按钮 + 流水线进度条 |

版本历史表格列：

- 版本
- 日期
- 状态
- F1
- 样本
- 审批人

按钮：

- `🚀 触发模拟迭代流水线`
- 运行中显示当前步骤和进度条。

模拟流水线阶段：

1. 监控触发检查
2. 数据清洗与特征工程
3. Stacking 模型训练（7基学习器+元学习器）
4. 5折时序交叉验证
5. 回归测试与 Drift 分析
6. 两级终审流程
7. 灰度发布 0.1 → 0.5 → 1.0
8. 迭代完成，模型已上线

### 7.2 准确性追踪

接口：

- `GET /api/v1/memory/iteration-tracking`

顶部控件：

- 时间筛选下拉：全部时间、近7天、近30天、近90天、近180天。
- `🔄 刷新` 按钮。

KPI：

- 准确率，带增减箭头。
- F1 分数，带增减箭头。
- 误报率 FPR，带增减箭头。
- 漏报率 FNR，带增减箭头。

统计卡：

- 95% 置信区间。
- 样本量。
- 统计显著性：显著改善 / 变化不显著。

图表：

| 标题 | 类型 |
|---|---|
| 📈 准确性趋势（多指标） | 多折线图：准确率、精确率、召回率、F1 |
| 📊 误报/漏报率对比 | 柱状图 |
| 🔥 迭代性能热力图 | 热力图 |
| 📊 迭代前后对比 | 分组柱状图 |

详细表格列：

- 版本
- 时间
- 准确率
- 精确率
- 召回率
- F1
- FPR
- FNR
- 样本
- 改进

### 7.3 生命周期管理

顶部：

- 标题：`🔧 版本全生命周期管理`
- 按钮：`➕ 创建新版本`，展开后变为 `取消创建`。

创建表单字段：

- 版本号
- 预期效果
- 版本描述
- 改进点（逗号或换行分隔）
- 技术实现方案

创建表单按钮：

- `✅ 创建版本`
- `取消`

版本卡片：

- 版本号。
- 状态标签。
- 日期。
- F1 标签。
- 样本标签。
- 展开/收起按钮 `▲ / ▼`。
- 工作流步骤图标：
  - 📝 版本创建
  - 🧪 自动测试
  - 📋 审批流程
  - ✅ 审批通过
  - 🔄 灰度发布
  - 🚀 正式上线
- 版本描述。
- 改进点标签。
- 展开详情：技术实现方案、预期效果、审批信息。

行内动作：

- 草稿状态：`🧪 开始测试`
- 测试中状态：`📋 提交审批`

### 7.4 审批工作流

标题：`📋 迭代审批工作流`

顶部：

- 待审批数量标签。

空状态：

- `✅ 暂无待审批的迭代版本`

待审批卡片：

- 标题：`审批请求: {version} - {description}`
- 当前生产版本对比块。
- 待审批版本对比块。
- 改进点标签。
- 技术方案。
- 审批意见文本域，必填。
- `✅ 批准发布`
- `❌ 驳回`

审批历史表格列：

- 版本
- 状态
- 审批人
- 审批意见
- 审批时间

### 7.5 版本对比

顶部：

- 标题：`📑 版本对比分析`
- 已选数量：`已选: x/3`
- 提示：选择 2-3 个版本进行对比分析。

选择表格列：

- 选择
- 版本
- 日期
- 状态
- F1
- 样本
- 描述

交互：

- 每行复选框。
- 最多选择 3 个版本。
- 选择至少 2 个后显示图表和详细表。

图表：

- `🎯 3D版本对比曲面`
- `📊 柱状图对比`

详细对比表指标：

- F1 分数
- 样本量
- 状态
- 描述
- 改进点
- 技术方案
- 审批人

### 7.6 变更日志

顶部：

- 标题：`📝 迭代变更日志`
- 状态筛选：全部状态、生产环境、灰度发布、待审批、已批准、已驳回。

展示：

- 竖向时间线。
- 每个版本一个可点击卡片。
- 卡片显示版本、状态、日期、F1、描述、改进点、展开箭头。
- 展开后显示技术实现方案、预期效果、审批信息。

## 8. 页面五：系统配置与 API 文档

文件：`frontend/src/pages/SystemConfigPage.tsx`

页面标题：

- `系统配置与 API 文档`

### 后端状态 Alert

状态：

- 在线：`FastAPI 后端已连通，当前版本 ...；模型与大模型调用由后端统一调度。`
- 离线：`后端未连通，前端将以本地 Mock 数据演示；请先启动 FastAPI 服务。`

接口：

- `GET /health`

### KPI 卡片

| 标题 | 内容 |
|---|---|
| API BASE | 同源代理或 `VITE_API_BASE` |
| 当前场景 | 当前选择的业务场景 |
| 决策链路 | `6 节点` |
| 治理阈值 | 当前场景蒙特卡洛置信度下限 |

### 方案映射的系统能力表

列：

- 模块
- 方案依据
- 页面配置含义

行：

- 多源数据治理
- 风险预测模型
- 长短期记忆
- 决策风控
- 迭代管控

### 智能体后端工作流

6 个流程节点卡：

| 序号 | 节点 | 标签 |
|---|---|---|
| 1 | 数据接入 | HTTP / CSV / Excel |
| 2 | 风险评估 | Stacking + SHAP |
| 3 | 记忆召回 | AgentFS + RAG |
| 4 | 决策生成 | LangGraph DAG |
| 5 | 合规校验 | MARCH + Monte Carlo |
| 6 | 结果推送 | Audit Trail |

### 当前场景配置参数

使用 `JsonView` 展示当前场景配置：

- 场景名称。
- 置信度阈值。
- 风险阈值。
- 校验严格度。
- 记忆召回 top_k。

### 核心知识库矩阵

静态展示 6 个知识库文件：

- `工矿风险预警智能体合规执行书.md`
- `部门分级审核SOP.md`
- `工业物理常识及传感器时间序列逻辑.md`
- `企业已具备的执行条件.md`
- `类似事故处理案例.md`
- `预警历史经验与短期记忆摘要.md`

### API 文档入口

链接/标签：

- `Swagger UI`，链接 `/docs`
- `Redoc`，链接 `/redoc`
- `GET /health` 静态标签

### 接口输入输出契约

使用 `JsonView` 展示示例：

- request：
  - `enterprise_id`
  - `scenario_id`
  - `data`
- response：
  - `enterprise_id`
  - `predicted_level`
  - `probability_distribution`
  - `shap_contributions`
  - `decision_payload`
  - `guardrails`

### 核心接口速查表

列：

- 分组
- 接口
- 说明

表内接口：

- `GET /health`
- `POST /api/v1/agent/decision`
- `POST /api/v1/agent/decision/stream`
- `POST /api/v1/agent/scenario/{id}`
- `POST /api/v1/prediction/predict`
- `POST /api/v1/data/upload`
- `POST /api/v1/data/upload/batch`
- `GET /api/v1/knowledge/list`
- `GET /api/v1/knowledge/read/{filename}`
- `POST /api/v1/knowledge/snapshot`
- `GET /api/v1/iteration/status`
- `POST /api/v1/iteration/trigger`
- `POST /api/v1/iteration/approve`
- `POST /api/v1/iteration/canary`
- `GET /api/v1/audit/query`

### 系统运行信息

使用 `JsonView` 展示：

- backend_status
- version
- api_base
- frontend：`React + Vite + ECharts (SCADA Theme)`
- backend：`Python + FastAPI + LangGraph`
- model_layer：`防泄露 Stacking 风险预警模型`
- memory_layer：`AgentFS + SQLite + Git + RAG`
- guardrails：`MARCH 三重校验 + Monte Carlo 高风险阻断`
- theme：`Industrial Control Room Dark`

## 9. 前端 API 封装清单

文件：`frontend/src/api/client.ts`

### 基础配置

- `VITE_API_BASE`：可覆盖 API 根地址，默认同源。
- `VITE_ADMIN_API_TOKEN`：如存在，则在需要管理员权限的请求中添加 `X-Admin-Token`。
- 统一错误处理：多数接口失败后返回 `null` 或空数组，不直接抛到页面。

### 当前封装的接口

| 函数 | 方法与路径 | 主要页面 |
|---|---|---|
| `fetchHealth` | `GET /health` | 全局、系统配置 |
| `switchScenario` | `POST /api/v1/agent/scenario/{scenarioId}` | 侧栏 |
| `fetchLLMConfig` | `GET /api/v1/agent/llm` | 当前主页面未直接展示 |
| `switchLLMProvider` | `POST /api/v1/agent/llm/{provider}` | 当前主页面未直接展示 |
| `updateLLMConfig` | `POST /api/v1/agent/llm` | 当前主页面未直接展示 |
| `postDecision` | `POST /api/v1/agent/decision` | 企业风险预测 |
| `streamDecision` | `POST /api/v1/agent/decision/stream` | 企业风险预测 |
| `uploadDataFile` | `POST /api/v1/data/upload` | 企业风险预测 |
| `listKnowledge` | `GET /api/v1/knowledge/list` | 当前主页面未直接展示 |
| `readKnowledge` | `GET /api/v1/knowledge/read/{filename}` | 当前主页面未直接展示 |
| `fetchIterationStatus` | `GET /api/v1/iteration/status` | 全局侧栏、迭代页 |
| `triggerIteration` | `POST /api/v1/iteration/trigger` | 迭代仪表盘 |
| `queryAudit` | `GET /api/v1/audit/query` | 当前主页面未直接展示 |
| `queryShortTermMemory` | `GET /api/v1/memory/short-term` | 旧封装 |
| `addShortTermMemory` | `POST /api/v1/memory/short-term` | 当前主页面未直接展示 |
| `deleteShortTermMemory` | `DELETE /api/v1/memory/short-term/{id}` | 短期记忆 |
| `queryLongTermMemory` | `GET /api/v1/memory/long-term` | 旧封装 |
| `addLongTermMemory` | `POST /api/v1/memory/long-term` | 当前主页面未直接展示 |
| `migrateToLongTerm` | `POST /api/v1/memory/migrate` | 短期记忆 |
| `queryWarningLogs` | `GET /api/v1/warning/logs` | 当前主页面未直接展示 |
| `resolveWarningLog` | `POST /api/v1/warning/logs/{id}/resolve` | 当前主页面未直接展示 |
| `importEnterpriseData` | `POST /api/v1/memory/import-new-data` | 数据管理 |
| `importExcelFile` | `POST /api/v1/memory/import-excel` | 导入预测 |
| `assessEnterpriseFile` | `POST /api/v1/memory/assess-enterprise` | 导入预测 |
| `batchRiskAssessment` | `POST /api/v1/memory/batch-assess` | 风险评估 |
| `fetchEnterpriseDataSummary` | `GET /api/v1/memory/enterprise-data-summary` | 数据管理 |
| `fetchMemoryStats` | `GET /api/v1/memory/stats` | 总览、记忆相关页 |
| `fetchWarningExperiences` | `GET /api/v1/memory/warning-experiences` | 预警经验 |
| `fetchEnterpriseRiskHistory` | `GET /api/v1/memory/enterprise-risk-history/{enterpriseId}` | 风险评估 |
| `fetchIterationTracking` | `GET /api/v1/memory/iteration-tracking` | 准确性追踪 |
| `fetchApprovals` | `GET /api/v1/memory/approvals` | 审批管理 |
| `createApproval` | `POST /api/v1/memory/approvals` | 当前主页面未直接展示 |
| `decideApproval` | `POST /api/v1/memory/approvals/{approvalId}/decide` | 审批管理 |
| `fetchAuditLogs` | `GET /api/v1/memory/audit-logs` | 审计日志 |
| `exportMemoryData` | `POST /api/v1/memory/export` | 导出面板、导入预测 |
| `queryShortTermMemoryPaginated` | `GET /api/v1/memory/short-term` | 短期记忆 |
| `queryLongTermMemoryPaginated` | `GET /api/v1/memory/long-term` | 长期记忆 |
| `generateModelEvaluation` | `POST /api/v1/model/evaluate` | 当前主页面未直接展示 |
| `listIterationRecords` | `GET /api/v1/iteration/records` | 当前主页面未直接展示 |
| `createIterationRecord` | `POST /api/v1/iteration/records` | 当前主页面未直接展示 |
| `approveIteration` | `POST /api/v1/iteration/records/{id}/approve` | 当前主页面未直接展示 |
| `promoteIteration` | `POST /api/v1/iteration/records/{id}/promote` | 当前主页面未直接展示 |
| `fetchEarlyWarningTrend` | `GET /api/v1/visualization/trend` | 数据可视化 |
| `fetchCorrelationScatter` | `GET /api/v1/visualization/scatter` | 数据可视化 |
| `fetchCorrelationHeatmap` | `GET /api/v1/visualization/heatmap` | 数据可视化 |
| `fetchEnterpriseStats` | `GET /api/v1/visualization/enterprise-stats` | 数据可视化 |
| `fetchModuleTrend` | `GET /api/v1/visualization/module-trend` | 数据可视化、记忆总览 |
| `fetchStorageTrend` | `GET /api/v1/visualization/storage-trend` | 数据可视化 |
| `fetchCategoryPriorityHeatmap` | `GET /api/v1/visualization/category-priority-heatmap` | 数据可视化 |
| `fetchEnterpriseCategoryHeatmap` | `GET /api/v1/visualization/enterprise-category-heatmap` | 数据可视化 |

## 10. 当前图表总清单

### ECharts 2D

- 环形饼图：风险概率、风险等级分布、分类分布、数据源分布、行业分布等。
- 横向/纵向柱状图：SHAP、优先级分布、企业关联 Top、数据来源 Top、风险等级趋势、误报/漏报对比。
- 堆叠柱状图：三模块分类对比、季度风险等级分布。
- 折线图：预警趋势、入库趋势、风险评分趋势、企业风险历史、准确率/F1/召回率趋势、月度综合趋势。
- 散点图：相关性散点、分类关联强度。
- 热力图：相关矩阵、分类×优先级、企业×分类、等级×场景、迭代性能。
- Gauge：综合风险评分、财务影响、记忆重要度、验证覆盖率、系统状态。
- Sunburst：记忆结构旭日图。

### ECharts GL 3D

- 三维风险曲面：严重性、相关性、不可逆性。
- 3D 多维度记忆曲面：短期记忆、长期记忆、预警经验。
- 3D 版本对比曲面：版本多个指标对比。

### 图表交互

- Tooltip。
- Legend。
- dataZoom 拖拽缩放。
- visualMap 颜色映射。
- markLine 阈值线。
- markPoint 峰值点。
- 3D 自动旋转。

## 11. 当前表格总清单

| 页面 | 表格 | 列 |
|---|---|---|
| 数据可视化 | TOP 8 高风险企业预警 | 排名、企业名称、行业类型、风险评分、风险等级、事故次数 |
| 知识库-风险评估 | 详细评估结果 | 企业ID、企业名称、场景、风险评分、风险等级、评估时间、预警经验、历史 |
| 知识库-导入预测 | 重点关注处置清单 | 企业名称、评分、等级、建议动作 |
| 知识库-导入预测 | 场景与等级汇总 | 维度、数量、占比 |
| 知识库-导入预测 | 详细预测结果 | 企业名称、风险评分、风险等级、场景、关键指标 |
| 知识库-预警经验 | 关键风险因素 | 指标、数值、风险贡献 |
| 知识库-短期记忆 | 短期记忆列表 | 优先级、分类、内容、企业ID、时间、标签、操作 |
| 知识库-长期记忆 | 长期记忆列表 | 优先级、分类、内容、数据源、企业ID、时间、已验证、操作 |
| 知识库-审批管理 | 审批列表 | ID、目标、操作、发起人、状态、创建时间、决策 |
| 知识库-审计日志 | 审计日志 | 时间、操作、操作人、目标、详情 |
| 迭代-仪表盘 | 版本历史 | 版本、日期、状态、F1、样本、审批人 |
| 迭代-准确性追踪 | 迭代追踪详细数据 | 版本、时间、准确率、精确率、召回率、F1、FPR、FNR、样本、改进 |
| 迭代-审批工作流 | 审批历史 | 版本、状态、审批人、审批意见、审批时间 |
| 迭代-版本对比 | 版本选择表 | 选择、版本、日期、状态、F1、样本、描述 |
| 迭代-版本对比 | 详细对比表 | 指标 + 所选版本列 |
| 系统配置 | 方案能力表 | 模块、方案依据、页面配置含义 |
| 系统配置 | 核心接口速查 | 分组、接口、说明 |

## 12. 分页与列表交互

当前显式分页：

| 页面 | 页大小 | 控件 |
|---|---|---|
| 预警经验 | 20 | 上一页、页码、下一页 |
| 短期记忆 | 20 | 上一页、页码、下一页 |
| 长期记忆 | 20 | 上一页、页码、下一页 |
| 审计日志 | 30 | 上一页、页码、下一页 |

其他列表交互：

- 预警经验卡片可展开/收起。
- 记忆详情通过模态弹窗查看。
- 迭代版本卡片可展开/收起。
- 变更日志时间线卡片可展开/收起。
- 版本对比最多选择 3 个版本。

## 13. 当前按钮与操作入口汇总

全局：

- 一级标签页按钮。
- 场景下拉切换。
- 演示模式复选框。

企业风险预测：

- 模拟数据填充。
- 上传 CSV/Excel。
- 使用 SSE 实时节点流。
- 执行预测。
- 折叠展开 SSE 日志和原始 JSON。

数据可视化：

- 该页没有手动刷新按钮，加载后自动请求接口。

知识库与记忆系统：

- 刷新统计。
- 从 `new_data/` 导入 Excel 数据。
- 执行批量风险评估。
- 选择文件进行预测分析。
- 导入到长期记忆库。
- 导出长期记忆。
- 导出短期记忆。
- 导出预警经验。
- 搜索预警经验。
- 预警等级筛选。
- 搜索短期/长期记忆。
- 分类筛选。
- 全部迁移。
- 单条迁移。
- 单条删除。
- 查看详情。
- 审批批准/驳回。
- 审计日志搜索。
- 上一页/下一页。

模型迭代：

- 触发模拟迭代流水线。
- 准确性追踪刷新。
- 时间周期筛选。
- 创建新版本。
- 取消创建。
- 开始测试。
- 提交审批。
- 批准发布。
- 驳回。
- 版本选择复选框。
- 变更日志状态筛选。

系统配置：

- Swagger UI 链接。
- Redoc 链接。

## 14. 重构时必须保留的功能清单

重构 UI 时建议保留以下行为和数据链路：

- 顶部后端健康状态、版本、场景、时间。
- 左侧场景切换和演示模式。
- 五个一级 Tab 的信息架构。
- 企业风险预测的 JSON 输入、CSV/Excel 上传、SSE 开关和 Mock 回退。
- 决策结果的风险等级、概率分布、SHAP、政府建议、企业建议、三类风控校验、SSE 日志和原始 JSON。
- 数据可视化页的 8 类接口数据和所有统计图表。
- 知识库与记忆系统的 9 个二级 Tab。
- 记忆导出筛选条件：格式、时间、分类、优先级、企业 ID。
- 短期记忆的迁移、删除和详情弹窗。
- 长期记忆的详情弹窗。
- 预警经验的搜索、等级筛选、展开详情和分页。
- 审批管理的状态筛选、批准、驳回。
- 审计日志搜索、操作筛选和分页。
- 迭代页 6 个二级 Tab 的生命周期功能。
- 版本对比最多 3 个版本。
- 系统配置页的能力映射、工作流、接口契约、API 速查和运行信息。

## 15. 当前前端可改进点

这些不是现有功能，而是给后续重构 AI 的提示：

- 当前 UI 信息量很高，适合大屏但普通桌面会显得拥挤。
- 大量 Emoji 图标风格不统一，重构可改成统一图标库。
- 大量内联样式分散在页面组件中，重构可沉淀为组件和设计 token。
- 部分页面同时承担“业务操作”和“图表大屏”职责，可拆成更清晰的信息层级。
- 许多卡片嵌套和面板样式重复，适合统一为 DashboardCard、Toolbar、DataTable、MetricCard、ChartPanel。
- 数据可视化页没有手动刷新按钮，重构可增加刷新和加载骨架屏。
- 系统配置页的接口清单是静态表，和 `client.ts` 内实际封装接口不完全一致，可在重构时统一。

## 16. 给 AI 重构时可复制的简短背景

当前项目是工矿企业风险预警智能体前端，React + Vite + TypeScript + ECharts，整体是深色 SCADA 工业控制室风格。应用包含顶部状态栏、左侧侧栏和 5 个一级页面：企业风险预测、数据可视化、知识库与记忆系统、模型迭代与 CI/CD、系统配置与 API 文档。请在保留所有接口、业务流程、图表、表格、分页、筛选、上传、导出、审批、SSE 日志和 Mock 回退能力的基础上，重构成更现代、更统一、更清晰、更适合桌面和大屏展示的前端界面。
