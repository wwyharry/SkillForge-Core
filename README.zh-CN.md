# SkillForge

[English](README.md) | 简体中文

SkillForge 是一个面向仓库知识蒸馏的工作台，用来把杂乱的项目材料整理成可复用的 AI 技能包。

它可以扫描本地目录、解析多种文档格式、提取流程证据、聚类能力模块，并通过内置 Web 界面把结果编译成可预览、可导出的技能产物。

## 为什么是 SkillForge？

团队真正有价值的知识，往往已经存在于仓库和文件夹里：产品文档、设计说明、研究报告、SOP、会议纪要、API 文档、Markdown 笔记。

问题不在于“有没有知识”，而在于如何把这些零散、隐性的知识，转化成 AI 可以复用的结构化技能。

手工完成这件事通常非常痛苦：

- 一次性脚本容易写，但很难维护和复用
- 通用 Agent 框架擅长编排，却不会自动把仓库知识提炼成技能包
- 手工复制文档到 prompt 中，成本高且难以规模化

SkillForge 专注解决这个中间环节：

> 证据提取 → 能力聚类 → 技能编译

也就是说，它不是单纯“运行一个 Agent”，而是帮助你把真实项目资料系统化地转成可执行的 AI 技能资产。

## 与其他方案相比有什么价值？

### 对比自建脚本

自建脚本适合一次性处理，但通常只停留在文件解析、关键词查找或规则抽取层面。

SkillForge 提供的是：

- 可重复执行的端到端流程
- 有状态的任务记录
- 可视化的工作流界面
- 生成结果的预览与导出机制

### 对比 LangChain / DSPy / 自定义 Agent 栈

这些工具非常适合做 prompt 编排、模型调用、Agent workflow。
而 SkillForge 更专注一个具体但常见的问题：

**如何把真实仓库里的知识蒸馏成可复用的 skill 包。**

简单来说：

- **LangChain / DSPy** 更偏向“搭建 Agent 系统”
- **SkillForge** 更偏向“把仓库知识变成 Agent 可用技能”

两者是互补关系。

## 典型使用场景

- 将内部文档沉淀为团队可复用技能
- 将研究资料文件夹提炼成结构化分析流程
- 从运营仓库中抽取 SOP 和执行步骤
- 把 API 文档与实现说明转成集成类技能
- 在“原始资料”和“AI 可执行技能”之间建立可审阅的桥梁

## 可视化体验

SkillForge 不是只有 API，它是一个可视化、可审阅的本地优先工作流。

### 可视化工作流

1. **Create a job**：选择仓库或文档目录
2. **Scan and parse**：发现候选文件并解析文档
3. **Extract evidence**：提取流程相关证据
4. **Cluster capabilities**：聚类为可复用能力模块
5. **Compile skills**：生成技能产物
6. **Export to folder**：导出到本地文件夹

### 内置可视化界面包括

- **Dashboard**：查看最近任务与流程覆盖情况
- **新建任务页**：配置根目录与目标描述
- **任务详情页**：展示
  - 阶段时间线
  - 任务进度
  - 文档解析结果
  - Evidence Workbench
  - Capability Clusters
  - Skill Plans
  - Generated Skills 预览
  - 导出与覆盖确认流程
- **SSE 实时状态更新**

### 1. 新建任务页面

<img width="2549" height="1403" alt="d563512473a2539a1ae612f04205a6c9" src="https://github.com/user-attachments/assets/cd6fdd08-67e7-42df-9ff7-45ab2904d0b1" />

### 2. 任务详情与可视化流程页

<img width="2549" height="1403" alt="84b0e0ca60d3ed6d20cbdbedf9383290" src="https://github.com/user-attachments/assets/9fc140c4-a0f0-49c0-8a46-baaa2a74a4e0" />

### 3. 导出后的技能文件夹结果

<img width="654" height="1044" alt="52c22df2242be4fd1c0be8f9dc964533" src="https://github.com/user-attachments/assets/23254618-0abd-4d06-a66e-c6b78adc3ae1" />

## 快速开始

### 环境要求

- Python 3.11+
- Windows / macOS / Linux

### 安装依赖

在仓库根目录运行：

```bash
pip install -r requirements.txt
```

或者直接安装后端包：

```bash
cd backend
pip install -e .
```

### 启动应用

在仓库根目录运行：

```bash
python start_skillforge.py
```

然后访问：

```text
http://127.0.0.1:8000
```

启动脚本会自动：

- 检查 `backend/` 是否存在
- 如果缺少 `backend/.env`，则从 `backend/.env.example` 自动生成
- 启动 FastAPI + Uvicorn 本地服务

### 第一次使用

1. 打开 `http://127.0.0.1:8000/jobs/new`
2. 输入任务名称
3. 选择本地仓库或文档目录
4. 输入你希望提取的目标描述
5. 运行流程
6. 查看 evidence、capability、skill 预览
7. 导出生成结果到本地文件夹

## 示例输出

一个典型的输出目录大致如下：

```text
exports/
└── customer-onboarding-skill/
    ├── SKILL.md
    ├── references/
    │   ├── decision-table.md
    │   ├── examples.md
    │   └── source-map.md
    ├── scripts/
    │   └── analyze_inputs.py
    └── assets/
        └── template.txt
```
**由于文件比较多，技能（skills）生成时间比较长是正常现象。**

## 模型依赖说明

SkillForge **默认不要求配置外部模型 API**。

当前默认体验是本地优先：

- 仓库扫描不依赖外部模型
- 文档解析不依赖外部模型
- 证据提取、能力聚类、技能规划与编译目前有本地/启发式实现
- Web UI 和导出流程都不需要 OpenAI Key

同时，系统也提供了可选的模型 API 配置界面，可用于：

- OpenAI 兼容接口
- Azure OpenAI 风格接口
- Anthropic 兼容接口
- 自定义兼容接口

因此：

- **不配置模型也可以运行 SkillForge**
- 如果后续要接入更强的模型能力，可以在设置页中进行配置和连通性测试

## 完整技术栈

### 应用层

- **Python 3.11+**
- **FastAPI**：API 与服务端应用框架
- **Jinja2**：服务端模板渲染
- **Uvicorn**：ASGI 服务
- **Vanilla JavaScript**：前端交互逻辑
- **Server-Sent Events (SSE)**：实时任务状态更新
- **CSS**：位于 `backend/app/static/style.css`

### 数据与配置

- **Pydantic v2**：Schema 与校验
- **pydantic-settings**：环境变量配置
- **orjson**：JSON 处理
- **python-multipart**：表单处理

### 持久化

- **本地优先默认模式**
- **SQLite**：本地数据文件位于 `backend/data/skillforge.db`
- **SQLAlchemy 2**：ORM / Repository 集成
- **Alembic**：数据库迁移
- **PostgreSQL + psycopg**：可选关系型持久化后端

### 异步执行

- **Celery**：可选后台任务执行
- **Redis**：可选 broker/result backend

### 文档处理

- **python-docx**：解析 `.docx`
- **pypdf**：解析 `.pdf`
- **openpyxl**：解析 `.xlsx`
- 原生 Python 处理 `.md` 与 `.txt`

### 可选 AI 后端集成

- 可配置 provider / base URL / API key / model
- 支持设置页中的连接测试
- 支持 SSL、超时、采样、streaming 等配置

## 架构概览

核心代码位于 `backend/app/`：

- `main.py` — 应用启动与路由注册
- `web.py` — 服务端渲染页面与表单路由
- `api/routes/` — JSON API
- `services/jobs.py` — 作业编排
- `services/inventory.py` — 仓库扫描与候选文件发现
- `services/parsing.py` — 文档解析
- `services/extraction.py` — 证据提取
- `services/distillation.py` — 能力聚类与 skill planning
- `services/compiler.py` — skill 编译与验证
- `services/exporter.py` — 导出与覆盖确认流程
- `services/model_client.py` — 可选模型连接
- `tasks/` — Celery 集成
- `templates/` — dashboard / job / settings 页面

## API 概览

### 健康检查

- `GET /health`

### Jobs API

- `GET /api/jobs`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/status`
- `GET /api/jobs/{job_id}/events`
- `POST /api/jobs/{job_id}/run`
- `POST /api/jobs/{job_id}/dispatch`
- `POST /api/jobs/{job_id}/retry`

### Settings API

- `GET /api/settings/model-api`
- `POST /api/settings/model-api`
- `POST /api/settings/model-api/test`

## 配置说明

环境变量从 `backend/.env` 读取，统一使用 `SKILLFORGE_` 前缀。

示例：

```env
SKILLFORGE_CORS_ORIGINS=["http://localhost:3000"]
SKILLFORGE_DATABASE_URL=postgresql+psycopg://skillforge:skillforge@localhost:5432/skillforge
SKILLFORGE_REDIS_URL=redis://localhost:6379/0
SKILLFORGE_USE_ASYNC_PIPELINE=false
SKILLFORGE_USE_DATABASE_PERSISTENCE=false
```

## 测试说明

当前仓库中 **没有正式提交的一方自动化测试套件**。

目前主要依赖手工验证：

- 本地启动应用
- 从 Web UI 创建任务
- 跑通流程
- 验证进度、预览、导出行为

如果后续补测试，`pytest` 会是比较自然的选择，但目前仓库里还没有完整接入。

## 贡献指南

欢迎贡献。

当前建议流程：

1. fork 仓库
2. 新建功能分支
3. 做聚焦的小改动
4. 本地验证 UI/API 流程
5. 提交 PR，并在需要时附上截图或复现说明

## 已知限制

- 当前提取与聚类仍偏启发式/本地优先，不是完全模型驱动
- 不包含 OCR，因此扫描版 PDF / 图片文字支持有限
- 超大仓库可能需要人工缩小扫描范围
- 目前没有提交自动化测试套件
- 输出质量仍受源文档质量与结构影响

## Roadmap

- 更强的模型增强提取与聚类
- 更好的可视化预览与可追溯性体验
- 更好的大仓库筛选与扩展性
- 自动化测试覆盖
- 更完整的导出与打包体验

## 许可证

本项目使用 [Apache License 2.0](LICENSE)。
