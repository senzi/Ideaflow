# Ideaflow

A high-pressure cognitive flux engine that transforms raw ideas into actionable growth levers through continuous human-AI collaboration.

基于流体力学模型的灵感管理系统，通过 NDJSON 维护一个具备"高压强"与"稳定通量"的需求池。

## 项目结构

```
Ideaflow/
├── ideaflow.ndjson    # 核心数据库（NDJSON 格式）
├── iflow.py          # CLI 工具
├── iflow_server.py   # Web 服务器（提供 REST API）
├── index.html        # Web UI 管理后台
├── SKILL.md          # Agent 操作指南
├── prd.md           # 产品需求文档
└── TEST_REPORT.md   # 测试报告
```

## 快速开始

### 方式1：CLI 工具

```bash
# 添加想法
python iflow.py add "实现用户认证系统" --title "用户认证功能" --tags 技术 后端

# 列出所有想法
python iflow.py list

# 按状态过滤
python iflow.py list --filter status:active

# 按标签过滤
python iflow.py list --filter tag:技术

# 查看详情
python iflow.py get <idea-id>

# 更新状态
python iflow.py update <idea-id> --status active

# 添加评论
python iflow.py comment <idea-id> "评论内容"

# Agent 技能：自动打标
python iflow.py label

# Agent 技能：可行性评估
python iflow.py evaluate <idea-id>

# 查看统计
python iflow.py stats
```

### 方式2：Web UI（推荐）

**Step 1**: 启动 Web 服务器

```bash
python iflow_server.py
# 或指定端口
python iflow_server.py 8080
```

**Step 2**: 浏览器访问 http://localhost:8080

**Web UI 功能**：
- 📊 实时统计仪表盘
- 🔥 认知压强热力图（实时计算）
- 💬 对话流视图（Thread View）
- 🔍 搜索和过滤（支持实时搜索）
- 🏷️ Agent 自动打标
- 🤖 Agent 可行性评估
- ✨ 完整的数据增删改查

**注意**：直接打开 `index.html` 而不启动服务器将无法保存数据（会回退到演示模式）。

### 方式3：Agent 使用

Agent 可以直接调用 CLI 命令：

```python
# 读取想法列表
python iflow.py list --filter updated:true

# 对未分类的想法进行自动打标
python iflow.py label

# 对更新的想法进行评估
python iflow.py evaluate <idea-id>

# 以代录模式添加想法
python iflow.py add "用户口述的想法" --proxy
```

更多操作请参考 `SKILL.md`。

## API 端点

启动 `iflow_server.py` 后，可以使用以下 REST API：

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/ideas` | 获取所有想法（支持过滤参数） |
| GET | `/api/ideas/<id>` | 获取单个想法 |
| POST | `/api/ideas` | 创建想法 |
| PUT | `/api/ideas/<id>` | 更新想法 |
| DELETE | `/api/ideas/<id>` | 删除想法 |
| POST | `/api/ideas/<id>/comments` | 添加评论 |
| POST | `/api/label` | 自动打标（Agent技能） |
| POST | `/api/ideas/<id>/evaluate` | 可行性评估（Agent技能） |
| GET | `/api/stats` | 统计数据 |
| GET | `/api/tags` | 所有标签 |

**过滤参数示例**：
```
GET /api/ideas?status=active&tag=技术&search=关键词
```

## 核心概念

### 状态流转
```
unclassified → active → transformed/archived
```

### 数据 Schema
每个想法包含：
- `id`: 唯一标识
- `title`: 标题
- `content`: 内容（支持 Markdown）
- `status`: 状态
- `tags`: 标签数组
- `meta`: 元数据（创建时间、更新时间、更新标记）
- `comments`: 评论数组

### 压强计算
```
压强 = 评论密度 × 10 + 更新标记 × 20 + 停留时长 × 2
```

## 特性

- ✅ 完整的 CRUD 操作（CLI + Web + API）
- ✅ Agent 技能集成（Labeler, Evaluator, Proxy）
- ✅ RESTful API
- ✅ 对话流视图
- ✅ 认知压强热力图
- ✅ 状态自动标记机制
- ✅ 中文界面
- ✅ 扁平项目结构
- ✅ 自动降级（API不可用时使用本地数据）

## 技术栈

- **后端**: Python 3.x + http.server + NDJSON
- **前端**: React 18 + Tailwind CSS (CDN)
- **数据格式**: NDJSON (Newline Delimited JSON)
- **API**: RESTful API with CORS 支持

## 开发状态

- [x] CLI 工具
- [x] Web UI
- [x] REST API 服务器
- [x] Agent 技能
- [x] 数据一致性
- [x] 测试报告
- [ ] 多用户支持
- [ ] 远程同步
- [ ] 数据备份

## License

MIT
