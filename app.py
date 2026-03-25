#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ideaflow Flask App - 前后端一体化应用
整合 WebUI 和 API，单进程维护
"""

import json
import uuid
import sys
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, send_file, jsonify, request

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 创建 Flask 应用
app = Flask(__name__, template_folder=".", static_folder=".")

# 配置文件
DATA_FILE = Path(__file__).parent / "ideaflow.ndjson"
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


# ==================== 前端路由 ====================


@app.route("/")
def index():
    """主页面 - 渲染 WebUI"""
    return send_file("index.html")


# ==================== API 路由 ====================


@app.route("/api/ideas", methods=["GET"])
def get_ideas():
    """获取所有想法（支持过滤）"""
    ideas = read_all_ideas()

    # 过滤参数
    status_filter = request.args.get("status")
    tag_filter = request.args.get("tag")
    updated_filter = request.args.get("updated")
    search_query = request.args.get("search")

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

    return jsonify({"ideas": filtered})


@app.route("/api/ideas/<idea_id>", methods=["GET"])
def get_idea(idea_id):
    """获取单个想法"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, idea_id)

    if idea:
        return jsonify(idea)
    return jsonify({"error": "想法未找到"}), 404


@app.route("/api/ideas", methods=["POST"])
def create_idea():
    """创建新想法"""
    data = request.get_json()

    new_idea = {
        "id": generate_id(),
        "title": data.get("title", ""),
        "content": data.get("content", ""),
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
    ideas.append(new_idea)

    if write_all_ideas(ideas):
        return jsonify(new_idea), 201
    return jsonify({"error": "保存失败"}), 500


@app.route("/api/ideas/<idea_id>", methods=["PUT"])
def update_idea(idea_id):
    """更新想法"""
    data = request.get_json()
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, idea_id)

    if not idea:
        return jsonify({"error": "想法未找到"}), 404

    # 允许更新的字段
    if "title" in data:
        idea["title"] = data["title"]
    if "content" in data:
        idea["content"] = data["content"]
    if "status" in data:
        idea["status"] = data["status"]
    if "tags" in data:
        idea["tags"] = data["tags"]

    # 自动更新时间戳和标记
    idea["meta"]["last_updated"] = now_iso()
    idea["meta"]["updated_flag"] = True

    if write_all_ideas(ideas):
        return jsonify(idea)
    return jsonify({"error": "保存失败"}), 500


@app.route("/api/ideas/<idea_id>", methods=["DELETE"])
def delete_idea(idea_id):
    """删除想法"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, idea_id)

    if not idea:
        return jsonify({"error": "想法未找到"}), 404

    ideas = [i for i in ideas if i.get("id") != idea_id]

    if write_all_ideas(ideas):
        return jsonify({"message": "删除成功"})
    return jsonify({"error": "删除失败"}), 500


@app.route("/api/ideas/<idea_id>/comments", methods=["POST"])
def add_comment(idea_id):
    """添加评论"""
    data = request.get_json()
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, idea_id)

    if not idea:
        return jsonify({"error": "想法未找到"}), 404

    comment = {
        "comment_id": generate_comment_id(),
        "role": data.get("role", "human"),
        "method": data.get("method", "manual"),
        "content": data.get("content", ""),
        "timestamp": now_iso(),
    }

    idea["comments"].append(comment)
    idea["meta"]["last_updated"] = now_iso()
    idea["meta"]["updated_flag"] = True

    if write_all_ideas(ideas):
        return jsonify(comment), 201
    return jsonify({"error": "保存失败"}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取统计数据"""
    ideas = read_all_ideas()
    return jsonify(
        {
            "total": len(ideas),
            "updated": sum(1 for i in ideas if i.get("meta", {}).get("updated_flag")),
            "active": sum(1 for i in ideas if i.get("status") == "active"),
            "unclassified": sum(1 for i in ideas if i.get("status") == "unclassified"),
            "archived": sum(1 for i in ideas if i.get("status") == "archived"),
            "transformed": sum(1 for i in ideas if i.get("status") == "transformed"),
            "comments": sum(len(i.get("comments", [])) for i in ideas),
        }
    )


@app.route("/api/tags", methods=["GET"])
def get_tags():
    """获取所有标签"""
    ideas = read_all_ideas()
    tags = set()
    for idea in ideas:
        tags.update(idea.get("tags", []))
    return jsonify({"tags": sorted(list(tags))})


@app.route("/api/label", methods=["POST"])
def auto_label():
    """自动打标（示例实现）"""
    ideas = read_all_ideas()
    labeled_count = 0

    # 简单规则：根据内容关键词自动添加标签
    keywords = {
        "技术": ["代码", "编程", "开发", "系统", "架构", "API", "数据库"],
        "产品": ["用户", "需求", "功能", "界面", "体验", "设计"],
        "商业": ["收入", "成本", "市场", "客户", "盈利", "商业模式"],
        "写作": ["文章", "写作", "博客", "内容", "文档"],
    }

    for idea in ideas:
        content = idea.get("content", "") + " " + idea.get("title", "")
        new_tags = []
        for tag, words in keywords.items():
            if any(word in content for word in words):
                if tag not in idea.get("tags", []):
                    new_tags.append(tag)

        if new_tags:
            idea["tags"] = idea.get("tags", []) + new_tags
            idea["meta"]["last_updated"] = now_iso()
            labeled_count += 1

    if write_all_ideas(ideas):
        return jsonify(
            {
                "message": f"已为 {labeled_count} 个想法自动添加标签",
                "labeled_count": labeled_count,
            }
        )
    return jsonify({"error": "保存失败"}), 500


@app.route("/api/ideas/<idea_id>/evaluate", methods=["POST"])
def evaluate_idea(idea_id):
    """评估想法可行性（示例实现）"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, idea_id)

    if not idea:
        return jsonify({"error": "想法未找到"}), 404

    # 简单评估逻辑
    tags = idea.get("tags", [])
    difficulty = "高" if "技术" in tags else "中"

    comment = {
        "comment_id": generate_comment_id(),
        "role": "agent",
        "method": "autonomous",
        "content": f"""【可行性评估】
- 难度：{difficulty}
- 原因：基于内容标签分析，该想法涉及{", ".join(tags) if tags else "通用"}领域

【风险识别】
- 技术风险：需要技术调研
- 资源风险：需要评估投入成本
- 时间风险：取决于执行优先级

【任务拆解】
1. 进一步细化需求和目标
2. 制定具体的执行计划
3. 分配资源并开始执行
4. 定期回顾和调整""",
        "timestamp": now_iso(),
    }

    idea["comments"].append(comment)
    idea["meta"]["last_updated"] = now_iso()

    if write_all_ideas(ideas):
        return jsonify(comment), 201
    return jsonify({"error": "保存失败"}), 500


def get_local_ip():
    """获取本机 IP"""
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


if __name__ == "__main__":
    print("\n🚀 Ideaflow Flask App 启动！")
    print(f"📍 本机访问: http://localhost:{PORT}")
    print(f"📍 局域网访问: http://{get_local_ip()}:{PORT}")
    print(f"📂 数据文件: {DATA_FILE}")
    print("\n按 Ctrl+C 停止\n")

    app.run(host="0.0.0.0", port=PORT, debug=False)
