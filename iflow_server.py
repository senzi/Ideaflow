#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ideaflow Web Server - 轻量级 HTTP API 服务器
提供 REST API 供 WebUI 调用，操作 ideaflow.ndjson
"""

import json
import uuid
import sys
import io
from datetime import datetime, timezone
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 配置文件
DATA_FILE = Path(__file__).parent / "ideaflow.ndjson"
WWW_DIR = Path(__file__).parent
PORT = 8765


def generate_id(prefix: str = "idea") -> str:
    """生成唯一 ID"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}-{timestamp}-{unique}"


def generate_comment_id() -> str:
    """生成评论 ID"""
    return f"cmt-{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    """获取当前 ISO8601 时间戳"""
    return datetime.now(timezone.utc).isoformat()


def read_all_ideas() -> list:
    """读取所有想法数据"""
    if not DATA_FILE.exists():
        return []

    ideas = []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ideas.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"读取数据文件错误: {e}")
    return ideas


def write_all_ideas(ideas: list) -> bool:
    """写入所有想法数据"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            for idea in ideas:
                f.write(json.dumps(idea, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"写入数据文件错误: {e}")
        return False


def find_idea_by_id(ideas: list, idea_id: str):
    """根据 ID 查找想法"""
    for idea in ideas:
        if idea.get("id") == idea_id:
            return idea
    return None


class IdeaflowHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{self.date_time_string()}] {args[0]}")

    def send_json_response(self, data, status=200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_error_response(self, message, status=400):
        """发送错误响应"""
        self.send_json_response({"error": message}, status)

    def read_body(self):
        """读取请求体"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))
        return {}

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        # 静态文件服务
        if path == "/" or path == "/index.html":
            self.serve_file("index.html", "text/html")
            return
        elif path == "/favicon.ico":
            self.send_error_response("Not found", 404)
            return

        # API: 获取所有想法
        if path == "/api/ideas":
            ideas = read_all_ideas()

            # 过滤参数
            status_filter = query.get("status", [None])[0]
            tag_filter = query.get("tag", [None])[0]
            updated_filter = query.get("updated", [None])[0]
            search_query = query.get("search", [None])[0]

            filtered = ideas
            if status_filter:
                filtered = [i for i in filtered if i.get("status") == status_filter]
            if tag_filter:
                filtered = [i for i in filtered if tag_filter in i.get("tags", [])]
            if updated_filter is not None:
                flag = updated_filter.lower() == "true"
                filtered = [
                    i for i in filtered if i.get("meta", {}).get("updated_flag") == flag
                ]
            if search_query:
                query_lower = search_query.lower()
                filtered = [
                    i
                    for i in filtered
                    if query_lower in i.get("title", "").lower()
                    or query_lower in i.get("content", "").lower()
                ]

            self.send_json_response({"ideas": filtered})
            return

        # API: 获取单个想法
        if path.startswith("/api/ideas/"):
            idea_id = path.split("/")[-1]
            ideas = read_all_ideas()
            idea = find_idea_by_id(ideas, idea_id)

            if idea:
                self.send_json_response(idea)
            else:
                self.send_error_response("想法未找到", 404)
            return

        # API: 统计数据
        if path == "/api/stats":
            ideas = read_all_ideas()
            stats = {
                "total": len(ideas),
                "updated": sum(
                    1 for i in ideas if i.get("meta", {}).get("updated_flag")
                ),
                "active": sum(1 for i in ideas if i.get("status") == "active"),
                "unclassified": sum(
                    1 for i in ideas if i.get("status") == "unclassified"
                ),
                "archived": sum(1 for i in ideas if i.get("status") == "archived"),
                "transformed": sum(
                    1 for i in ideas if i.get("status") == "transformed"
                ),
                "total_comments": sum(len(i.get("comments", [])) for i in ideas),
                "tags": {},
            }

            # 统计标签
            for idea in ideas:
                for tag in idea.get("tags", []):
                    stats["tags"][tag] = stats["tags"].get(tag, 0) + 1

            self.send_json_response(stats)
            return

        # API: 获取所有标签
        if path == "/api/tags":
            ideas = read_all_ideas()
            tags = set()
            for idea in ideas:
                tags.update(idea.get("tags", []))
            self.send_json_response({"tags": sorted(list(tags))})
            return

        self.send_error_response("接口未找到", 404)

    def do_POST(self):
        """处理 POST 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # API: 创建想法
        if path == "/api/ideas":
            data = self.read_body()

            if not data.get("content"):
                self.send_error_response("内容不能为空")
                return

            idea = {
                "id": generate_id(),
                "title": data.get("title")
                or (
                    data["content"][:20] + "..."
                    if len(data["content"]) > 20
                    else data["content"]
                ),
                "content": data["content"],
                "status": data.get("status", "unclassified"),
                "tags": data.get("tags", []),
                "meta": {
                    "created_at": now_iso(),
                    "last_updated": now_iso(),
                    "updated_flag": False,
                },
                "comments": [],
            }

            ideas = read_all_ideas()
            ideas.append(idea)

            if write_all_ideas(ideas):
                self.send_json_response(idea, 201)
            else:
                self.send_error_response("保存失败", 500)
            return

        # API: 添加评论
        if path.startswith("/api/ideas/") and path.endswith("/comments"):
            parts = path.split("/")
            idea_id = parts[-2]

            data = self.read_body()
            content = data.get("content", "").strip()

            if not content:
                self.send_error_response("评论内容不能为空")
                return

            ideas = read_all_ideas()
            idea = find_idea_by_id(ideas, idea_id)

            if not idea:
                self.send_error_response("想法未找到", 404)
                return

            comment = {
                "comment_id": generate_comment_id(),
                "role": data.get("role", "human"),
                "method": data.get("method", "manual"),
                "content": content,
                "timestamp": now_iso(),
            }

            if "comments" not in idea:
                idea["comments"] = []

            idea["comments"].append(comment)
            idea["meta"]["updated_flag"] = True
            idea["meta"]["last_updated"] = now_iso()

            if write_all_ideas(ideas):
                self.send_json_response(comment, 201)
            else:
                self.send_error_response("保存失败", 500)
            return

        # API: 自动打标
        if path == "/api/label":
            ideas = read_all_ideas()
            labeled_count = 0

            keyword_map = {
                "技术": [
                    "代码",
                    "程序",
                    "api",
                    "数据库",
                    "算法",
                    "架构",
                    "系统",
                    "技术",
                    "后端",
                    "前端",
                ],
                "产品": [
                    "用户",
                    "功能",
                    "需求",
                    "体验",
                    "界面",
                    "产品",
                    "设计",
                    "交互",
                ],
                "商业": [
                    "盈利",
                    "收入",
                    "市场",
                    "客户",
                    "商业模式",
                    "营销",
                    "商业",
                    "变现",
                ],
                "研究": ["调研", "分析", "数据", "实验", "论文", "研究", "调查"],
                "写作": ["文章", "博客", "内容", "写作", "文案", "故事", "教程"],
                "生活": ["习惯", "健康", "旅行", "生活", "日常", "家庭", "学习"],
                "AI": ["ai", "人工智能", "机器学习", "深度学习", "模型", "gpt", "llm"],
            }

            for idea in ideas:
                if idea.get("status") != "unclassified":
                    continue

                content = idea.get("content", "").lower()
                title = idea.get("title", "").lower()
                text = title + " " + content

                auto_tags = set()
                for tag, keywords in keyword_map.items():
                    if any(kw in text for kw in keywords):
                        auto_tags.add(tag)

                if auto_tags:
                    current_tags = set(idea.get("tags", []))
                    idea["tags"] = list(current_tags | auto_tags)
                    idea["meta"]["updated_flag"] = True
                    idea["meta"]["last_updated"] = now_iso()
                    labeled_count += 1

            if write_all_ideas(ideas):
                self.send_json_response(
                    {
                        "success": True,
                        "labeled_count": labeled_count,
                        "message": f"已为 {labeled_count} 个想法添加标签",
                    }
                )
            else:
                self.send_error_response("保存失败", 500)
            return

        # API: 可行性评估
        if path.startswith("/api/ideas/") and path.endswith("/evaluate"):
            idea_id = path.split("/")[-2]

            ideas = read_all_ideas()
            idea = find_idea_by_id(ideas, idea_id)

            if not idea:
                self.send_error_response("想法未找到", 404)
                return

            tags = idea.get("tags", [])

            # 难度评估
            difficulty = "中"
            if any(t in tags for t in ["技术", "架构", "后端", "AI"]):
                difficulty = "高"
            elif any(t in tags for t in ["生活", "写作"]):
                difficulty = "低"

            evaluation = f"""【可行性评估】
- 难度：{difficulty}
- 原因：基于内容标签分析，该想法涉及{", ".join(tags) if tags else "一般性"}领域

【风险识别】
- 技术风险：{"需要技术调研" if "技术" in tags or "AI" in tags else "较低"}
- 资源风险：{"需要评估投入成本" if difficulty == "高" else "可控"}
- 时间风险：取决于执行优先级

【任务拆解】
1. 进一步细化需求和目标
2. 制定具体的执行计划
3. 分配资源并开始执行
4. 定期回顾和调整"""

            comment = {
                "comment_id": generate_comment_id(),
                "role": "agent",
                "method": "autonomous",
                "content": evaluation,
                "timestamp": now_iso(),
            }

            if "comments" not in idea:
                idea["comments"] = []

            idea["comments"].append(comment)
            idea["meta"]["last_updated"] = now_iso()
            # 不自动清除 updated_flag，等待人工确认

            if write_all_ideas(ideas):
                self.send_json_response(comment, 201)
            else:
                self.send_error_response("保存失败", 500)
            return

        self.send_error_response("接口未找到", 404)

    def do_PUT(self):
        """处理 PUT 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # API: 更新想法
        if path.startswith("/api/ideas/"):
            idea_id = path.split("/")[-1]
            data = self.read_body()

            ideas = read_all_ideas()
            idea = find_idea_by_id(ideas, idea_id)

            if not idea:
                self.send_error_response("想法未找到", 404)
                return

            # 更新字段
            if "title" in data:
                idea["title"] = data["title"]
            if "content" in data:
                idea["content"] = data["content"]
            if "status" in data:
                idea["status"] = data["status"]
            if "tags" in data:
                idea["tags"] = data["tags"]

            idea["meta"]["updated_flag"] = True
            idea["meta"]["last_updated"] = now_iso()

            if write_all_ideas(ideas):
                self.send_json_response(idea)
            else:
                self.send_error_response("保存失败", 500)
            return

        self.send_error_response("接口未找到", 404)

    def do_DELETE(self):
        """处理 DELETE 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # API: 删除想法（谨慎使用）
        if path.startswith("/api/ideas/"):
            idea_id = path.split("/")[-1]

            ideas = read_all_ideas()
            new_ideas = [i for i in ideas if i.get("id") != idea_id]

            if len(new_ideas) == len(ideas):
                self.send_error_response("想法未找到", 404)
                return

            if write_all_ideas(new_ideas):
                self.send_json_response({"success": True, "message": "已删除"})
            else:
                self.send_error_response("删除失败", 500)
            return

        self.send_error_response("接口未找到", 404)

    def serve_file(self, filename, content_type):
        """提供静态文件"""
        file_path = WWW_DIR / filename
        if file_path.exists():
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error_response("文件未找到", 404)


def run_server(port=PORT):
    """启动服务器"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, IdeaflowHandler)
    print(f"\n🚀 Ideaflow Server 启动成功！")
    print(f"📍 本地访问: http://localhost:{port}")
    print(f"📂 数据文件: {DATA_FILE}")
    print(f"\n可用端点:")
    print(f"  GET    /api/ideas          - 获取所有想法")
    print(f"  GET    /api/ideas/<id>     - 获取单个想法")
    print(f"  POST   /api/ideas          - 创建想法")
    print(f"  PUT    /api/ideas/<id>     - 更新想法")
    print(f"  DELETE /api/ideas/<id>     - 删除想法")
    print(f"  POST   /api/ideas/<id>/comments - 添加评论")
    print(f"  POST   /api/label          - 自动打标")
    print(f"  POST   /api/ideas/<id>/evaluate - 可行性评估")
    print(f"  GET    /api/stats          - 统计数据")
    print(f"  GET    /api/tags           - 所有标签")
    print(f"\n按 Ctrl+C 停止服务器\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
        httpd.shutdown()


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
