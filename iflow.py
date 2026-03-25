#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ideaflow CLI - 灵感管理系统的核心控制器
"""

import sys
import io

# 设置 stdout 编码为 utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import json
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# 配置文件
DATA_FILE = Path(__file__).parent / "ideaflow.ndjson"
SKILL_FILE = Path(__file__).parent / "SKILL.md"


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


def read_all_ideas() -> List[Dict[str, Any]]:
    """读取所有想法数据"""
    if not DATA_FILE.exists():
        return []

    ideas = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ideas.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return ideas


def write_all_ideas(ideas: List[Dict[str, Any]]) -> None:
    """写入所有想法数据（原子化重写）"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        for idea in ideas:
            f.write(json.dumps(idea, ensure_ascii=False) + "\n")


def find_idea_by_id(
    ideas: List[Dict[str, Any]], idea_id: str
) -> Optional[Dict[str, Any]]:
    """根据 ID 查找想法"""
    for idea in ideas:
        if idea.get("id") == idea_id:
            return idea
    return None


def update_idea_flag(idea: Dict[str, Any]) -> None:
    """更新想法的更新标记"""
    idea["meta"]["updated_flag"] = True
    idea["meta"]["last_updated"] = now_iso()


def cmd_add(args):
    """添加新想法"""
    content = args.content
    method = "proxy" if args.proxy else "manual"
    role = "agent" if args.proxy else "human"

    # 如果提供了标题，使用标题；否则从内容提取前20字符
    title = (
        args.title
        if args.title
        else (content[:20] + "..." if len(content) > 20 else content)
    )

    idea = {
        "id": generate_id(),
        "title": title,
        "content": content,
        "status": "unclassified",
        "tags": args.tags if args.tags else [],
        "meta": {
            "created_at": now_iso(),
            "last_updated": now_iso(),
            "updated_flag": False,
        },
        "comments": [],
    }

    # 如果有初始评论
    if args.comment:
        idea["comments"].append(
            {
                "comment_id": generate_comment_id(),
                "role": role,
                "method": method,
                "content": args.comment,
                "timestamp": now_iso(),
            }
        )
        idea["meta"]["updated_flag"] = True

    # 追加到文件
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(idea, ensure_ascii=False) + "\n")

    print(f"[OK] 已创建想法: {idea['id']}")
    print(f"   标题: {idea['title']}")
    print(f"   状态: {idea['status']}")


def cmd_list(args):
    """列出想法"""
    ideas = read_all_ideas()

    if not ideas:
        print("[提示] 暂无想法，使用 `iflow add` 创建第一个想法")
        return

    # 过滤逻辑
    filtered = ideas

    if args.filter:
        for filter_str in args.filter:
            if ":" in filter_str:
                key, value = filter_str.split(":", 1)
                if key == "tag":
                    filtered = [i for i in filtered if value in i.get("tags", [])]
                elif key == "status":
                    filtered = [i for i in filtered if i.get("status") == value]
                elif key == "updated":
                    flag = value.lower() == "true"
                    filtered = [
                        i
                        for i in filtered
                        if i.get("meta", {}).get("updated_flag") == flag
                    ]

    # 排序
    if args.sort == "pressure":
        # 按评论密度排序（评论数越多，压强越高）
        filtered.sort(key=lambda x: len(x.get("comments", [])), reverse=True)
    elif args.sort == "updated":
        filtered.sort(
            key=lambda x: x.get("meta", {}).get("last_updated", ""), reverse=True
        )

    # 显示
    if not filtered:
        print("[搜索] 没有找到匹配的想法")
        return

    print(f"\n[列表] 共 {len(filtered)} 个想法\n")
    print(f"{'ID':<20} {'状态':<12} {'标签':<20} {'标题':<30} {'更新':<6}")
    print("-" * 90)

    for idea in filtered:
        idea_id = idea["id"][:18]
        status = idea.get("status", "unknown")
        tags = ",".join(idea.get("tags", []))[:18]
        title = idea.get("title", "无标题")[:28]
        updated = "[*]" if idea.get("meta", {}).get("updated_flag") else "[ ]"

        print(f"{idea_id:<20} {status:<12} {tags:<20} {title:<30} {updated:<6}")

    print()


def cmd_get(args):
    """获取单个想法详情"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, args.id)

    if not idea:
        print(f"[X] 未找到想法: {args.id}")
        return

    print(f"\n[文档] {idea['title']}")
    print(f"ID: {idea['id']}")
    print(f"状态: {idea['status']}")
    print(f"标签: {', '.join(idea.get('tags', []))}")
    print(f"创建: {idea['meta']['created_at']}")
    print(f"更新: {idea['meta']['last_updated']}")
    print(f"标记: {'[*] 待处理' if idea['meta']['updated_flag'] else '[ ] 已同步'}")
    print(f"\n内容:\n{idea['content']}\n")

    comments = idea.get("comments", [])
    if comments:
        print(f"[评论] 评论 ({len(comments)}条):")
        for cmt in comments:
            role_emoji = "[人]" if cmt["role"] == "human" else "[机]"
            method_indicator = {
                "manual": "[手动]",
                "proxy": "[代录]",
                "autonomous": "[自动]",
            }.get(cmt["method"], "")
            print(f"  {role_emoji} {method_indicator} {cmt['timestamp']}")
            print(f"     {cmt['content']}\n")


def cmd_update(args):
    """更新想法状态或内容"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, args.id)

    if not idea:
        print(f"[X] 未找到想法: {args.id}")
        return

    modified = False

    if args.status:
        idea["status"] = args.status
        modified = True
        print(f"[OK] 状态已更新: {args.status}")

    if args.title:
        idea["title"] = args.title
        modified = True
        print(f"[OK] 标题已更新")

    if args.content:
        idea["content"] = args.content
        modified = True
        print(f"[OK] 内容已更新")

    if modified:
        update_idea_flag(idea)
        write_all_ideas(ideas)


def cmd_tag(args):
    """添加标签"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, args.id)

    if not idea:
        print(f"[X] 未找到想法: {args.id}")
        return

    current_tags = set(idea.get("tags", []))
    new_tags = set(args.tags)

    # 合并标签
    idea["tags"] = list(current_tags | new_tags)
    update_idea_flag(idea)
    write_all_ideas(ideas)

    print(f"[OK] 标签已更新: {', '.join(idea['tags'])}")


def cmd_comment(args):
    """添加评论"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, args.id)

    if not idea:
        print(f"[X] 未找到想法: {args.id}")
        return

    method = "proxy" if args.proxy else "manual"
    role = "agent" if args.proxy else "human"

    comment = {
        "comment_id": generate_comment_id(),
        "role": role,
        "method": method,
        "content": args.content,
        "timestamp": now_iso(),
    }

    if "comments" not in idea:
        idea["comments"] = []

    idea["comments"].append(comment)
    update_idea_flag(idea)
    write_all_ideas(ideas)

    print(f"[OK] 评论已添加")


def cmd_ack(args):
    """确认处理（清除更新标记）"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, args.id)

    if not idea:
        print(f"[X] 未找到想法: {args.id}")
        return

    idea["meta"]["updated_flag"] = False
    idea["meta"]["last_updated"] = now_iso()
    write_all_ideas(ideas)

    print(f"[OK] 已确认处理: {args.id}")


def cmd_label(args):
    """自动打标（Agent 技能）"""
    ideas = read_all_ideas()

    if args.id:
        # 指定 ID
        idea = find_idea_by_id(ideas, args.id)
        if not idea:
            print(f"[X] 未找到想法: {args.id}")
            return
        ideas_to_label = [idea]
    else:
        # 所有未分类的
        ideas_to_label = [i for i in ideas if i.get("status") == "unclassified"]

    if not ideas_to_label:
        print("[提示] 没有需要打标的想法")
        return

    labeled_count = 0
    for idea in ideas_to_label:
        # 基于内容自动推断标签
        content = idea.get("content", "").lower()
        title = idea.get("title", "").lower()
        text = title + " " + content

        auto_tags = set()

        # 简单的关键词匹配规则
        keyword_map = {
            "技术": ["代码", "程序", "api", "数据库", "算法", "架构", "系统", "技术"],
            "产品": ["用户", "功能", "需求", "体验", "界面", "产品", "设计"],
            "商业": ["盈利", "收入", "市场", "客户", "商业模式", "营销", "商业"],
            "研究": ["调研", "分析", "数据", "实验", "论文", "研究"],
            "写作": ["文章", "博客", "内容", "写作", "文案", "故事"],
            "生活": ["习惯", "健康", "旅行", "生活", "日常", "家庭"],
        }

        for tag, keywords in keyword_map.items():
            if any(kw in text for kw in keywords):
                auto_tags.add(tag)

        if auto_tags:
            current_tags = set(idea.get("tags", []))
            idea["tags"] = list(current_tags | auto_tags)
            update_idea_flag(idea)
            labeled_count += 1
            print(f"[标签]  {idea['id'][:20]}... → {', '.join(auto_tags)}")

    if labeled_count > 0:
        write_all_ideas(ideas)
        print(f"\n[OK] 已为 {labeled_count} 个想法添加标签")
    else:
        print("[提示] 没有匹配到合适的标签")


def cmd_evaluate(args):
    """执行可行性评估（Agent 技能）"""
    ideas = read_all_ideas()
    idea = find_idea_by_id(ideas, args.id)

    if not idea:
        print(f"[X] 未找到想法: {args.id}")
        return

    if not idea.get("meta", {}).get("updated_flag"):
        print("[提示] 该想法没有待处理的更新")
        return

    # 生成评估内容
    title = idea.get("title", "")
    content = idea.get("content", "")
    tags = idea.get("tags", [])

    # 基于标签和内容进行简单评估
    difficulty = "中"
    if "技术" in tags or "架构" in tags:
        difficulty = "高"
    elif "生活" in tags or "写作" in tags:
        difficulty = "低"

    evaluation = f"""【可行性评估】
- 难度：{difficulty}
- 原因：基于内容标签分析，该想法涉及{", ".join(tags) if tags else "一般性"}领域

【风险识别】
- 技术风险：{"需要技术调研" if "技术" in tags else "较低"}
- 资源风险：{"需要评估投入成本" if difficulty == "高" else "可控"}
- 时间风险：取决于执行优先级

【任务拆解】
1. 进一步细化需求和目标
2. 制定具体的执行计划
3. 分配资源并开始执行
4. 定期回顾和调整"""

    # 添加评估评论
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
    # 评估后不自动清除标记，等待人工确认
    idea["meta"]["last_updated"] = now_iso()
    write_all_ideas(ideas)

    print(f"[OK] 已完成可行性评估")
    print(f"\n{evaluation}")


def cmd_stats(args):
    """显示统计信息"""
    ideas = read_all_ideas()

    if not ideas:
        print("[提示] 暂无数据")
        return

    total = len(ideas)
    status_counts = {}
    tag_counts = {}
    updated_count = 0
    total_comments = 0

    for idea in ideas:
        status = idea.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        for tag in idea.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if idea.get("meta", {}).get("updated_flag"):
            updated_count += 1

        total_comments += len(idea.get("comments", []))

    print("\n[统计] Ideaflow 统计")
    print("=" * 40)
    print(f"总想法数: {total}")
    print(f"待处理: {updated_count} [*]")
    print(f"总评论数: {total_comments}")
    print(f"\n状态分布:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    print(f"\n热门标签:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {tag}: {count}")
    print()


def cmd_help_agent(args):
    """显示 Agent 操作指南"""
    if SKILL_FILE.exists():
        with open(SKILL_FILE, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("[X] 未找到 SKILL.md 文件")


def main():
    parser = argparse.ArgumentParser(
        description="Ideaflow - 灵感管理系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  iflow add "新想法"                    # 添加想法
  iflow list                           # 列出所有想法
  iflow list --filter status:active    # 按状态过滤
  iflow get <id>                       # 查看详情
  iflow update <id> --status active    # 更新状态
  iflow comment <id> "评论内容"        # 添加评论
  iflow label                          # 自动打标（所有未分类）
  iflow evaluate <id>                  # 可行性评估
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加新想法")
    add_parser.add_argument("content", help="想法内容")
    add_parser.add_argument("--title", "-t", help="想法标题")
    add_parser.add_argument("--tags", nargs="+", help="标签列表")
    add_parser.add_argument("--comment", "-c", help="初始评论")
    add_parser.add_argument(
        "--proxy", action="store_true", help="代录模式（Agent使用）"
    )
    add_parser.set_defaults(func=cmd_add)

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出想法")
    list_parser.add_argument(
        "--filter",
        "-f",
        action="append",
        help="过滤条件 (如: status:active, tag:技术, updated:true)",
    )
    list_parser.add_argument(
        "--sort",
        "-s",
        choices=["updated", "pressure", "created"],
        default="updated",
        help="排序方式",
    )
    list_parser.set_defaults(func=cmd_list)

    # get 命令
    get_parser = subparsers.add_parser("get", help="获取想法详情")
    get_parser.add_argument("id", help="想法ID")
    get_parser.set_defaults(func=cmd_get)

    # update 命令
    update_parser = subparsers.add_parser("update", help="更新想法")
    update_parser.add_argument("id", help="想法ID")
    update_parser.add_argument(
        "--status",
        choices=["unclassified", "active", "archived", "transformed"],
        help="更新状态",
    )
    update_parser.add_argument("--title", help="更新标题")
    update_parser.add_argument("--content", help="更新内容")
    update_parser.set_defaults(func=cmd_update)

    # tag 命令
    tag_parser = subparsers.add_parser("tag", help="添加标签")
    tag_parser.add_argument("id", help="想法ID")
    tag_parser.add_argument("tags", nargs="+", help="要添加的标签")
    tag_parser.set_defaults(func=cmd_tag)

    # comment 命令
    comment_parser = subparsers.add_parser("comment", help="添加评论")
    comment_parser.add_argument("id", help="想法ID")
    comment_parser.add_argument("content", help="评论内容")
    comment_parser.add_argument("--proxy", action="store_true", help="代录模式")
    comment_parser.set_defaults(func=cmd_comment)

    # ack 命令
    ack_parser = subparsers.add_parser("ack", help="确认处理（清除更新标记）")
    ack_parser.add_argument("id", help="想法ID")
    ack_parser.set_defaults(func=cmd_ack)

    # label 命令
    label_parser = subparsers.add_parser("label", help="自动打标（Agent技能）")
    label_parser.add_argument(
        "id", nargs="?", help="指定想法ID（不指定则处理所有未分类）"
    )
    label_parser.set_defaults(func=cmd_label)

    # evaluate 命令
    evaluate_parser = subparsers.add_parser("evaluate", help="可行性评估（Agent技能）")
    evaluate_parser.add_argument("id", help="想法ID")
    evaluate_parser.set_defaults(func=cmd_evaluate)

    # stats 命令
    stats_parser = subparsers.add_parser("stats", help="统计信息")
    stats_parser.set_defaults(func=cmd_stats)

    # skill 命令
    skill_parser = subparsers.add_parser("skill", help="显示 Agent 操作指南")
    skill_parser.set_defaults(func=cmd_help_agent)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
