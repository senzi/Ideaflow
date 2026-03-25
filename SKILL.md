# Agent 操作指南

## 角色定义
- **role: human** - 人类用户
- **role: agent** - AI 助手（你）

## 录入方式
- **method: manual** - 人类直接在 WebUI/CLI 输入
- **method: proxy** - 人类口述或授权，由 AI 整理代录
- **method: autonomous** - AI 基于逻辑触发的自主评估

## 核心约束

### 1. 权限边界
- **禁止**：修改人类的 `manual` 评论
- **允许**：新增评论进行补充
- **允许**：修改 `status`、`tags` 等元数据

### 2. 状态流转规则
```
unclassified → active → transformed/archived
```

### 3. 自动触发条件

#### Skill: Labeler（自动打标）
- 触发：`status == "unclassified"`
- 动作：分析内容，添加领域标签
- 命令：`iflow label <id> <tags...>`

#### Skill: Evaluator（可行性评估）
- 触发：`meta.updated_flag == true`
- 动作：追加评估评论，包含：
  - 实现难度评估
  - 风险点识别
  - 任务拆解建议
- 命令：自动执行，无需手动调用

#### Skill: Proxy Recorder（代录员）
- 触发：人类说"记一下这个想法"
- 动作：以 `method: proxy` 方式创建新条目
- 命令：`iflow add --proxy "想法内容"`

## 数据操作规范

### 读取数据
```bash
# 列出所有想法
iflow list

# 按标签过滤
iflow list --filter tag:架构

# 按状态过滤
iflow list --filter status:active

# 按更新标记过滤
iflow list --filter updated:true

# 获取单个想法详情
iflow get <id>
```

### 修改数据
```bash
# 更新状态
iflow update <id> --status active

# 添加标签
iflow tag <id> <tag1> <tag2>

# 添加评论（自动设置 updated_flag）
iflow comment <id> "评论内容"

# 标记为已处理（清除 updated_flag）
iflow ack <id>
```

## 评估模板

当执行 Evaluator 技能时，使用以下格式：

```
【可行性评估】
- 难度：[低/中/高]
- 原因：[简要说明]

【风险识别】
- 技术风险：[描述]
- 资源风险：[描述]
- 合规风险：[描述]

【任务拆解】
1. [步骤1]
2. [步骤2]
3. [步骤3]
```

## 重要提醒
- 所有修改操作都会自动设置 `meta.updated_flag = true`
- Agent 不得随意删除任何数据
- 优先使用 CLI 命令操作，避免直接读写 ndjson 文件
- 保持数据文件扁平结构，禁止创建子目录

## WebUI 使用须知

### 启动服务器
WebUI 需要服务器支持，**禁止直接双击打开 index.html**（会导致 CORS 错误）。

```bash
# 启动服务器（默认端口 8765）
python iflow_server.py

# 或指定端口
python iflow_server.py 8765
```

### 访问方式
- **本机访问**: http://localhost:8765
- **局域网访问**: http://<本机IP>:8765

### Agent 守护模式
Agent 应该以守护进程形式持续运行服务器
