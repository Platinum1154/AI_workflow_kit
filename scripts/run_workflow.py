from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "article-to-platform-input.example.yaml"
PLATFORM_RULES_PATH = ROOT / "config" / "platform-rules.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        run_init(args.output, args.force)
        return

    if args.command == "run":
        run_pipeline(args.input, args.output_dir)
        return

    parser.print_help()


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_workflow.py",
        description="文章整理与多平台成稿模板合并脚本",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="复制输入模板")
    init_parser.add_argument(
        "--output",
        default=str(ROOT / "inputs" / "article-to-platform-input.yaml"),
        help="输出模板文件路径",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已存在的目标文件",
    )

    run_parser = subparsers.add_parser("run", help="渲染并输出所有阶段模板")
    run_parser.add_argument(
        "--input",
        required=True,
        help="输入 YAML 文件路径",
    )
    run_parser.add_argument(
        "--output-dir",
        help="输出目录，默认使用 YAML 中的 runtime.output_dir 或 outputs/",
    )

    return parser


def run_init(output: str, force: bool) -> None:
    output_path = Path(output)
    if output_path.exists() and not force:
        raise SystemExit(f"目标文件已存在：{output_path}。如需覆盖，请加 --force")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE_PATH, output_path)
    print(f"已创建输入模板：{output_path}")


def run_pipeline(input_path_str: str, output_dir_str: str | None) -> None:
    input_path = Path(input_path_str)
    if not input_path.exists():
        raise SystemExit(f"找不到输入文件：{input_path}")

    config = load_yaml(input_path)
    context = build_context(config)
    runtime = config.get("runtime", {})
    output_root = Path(output_dir_str or runtime.get("output_dir") or DEFAULT_OUTPUT_DIR)
    run_dir = make_run_dir(output_root, context["target_platform"], input_path.stem)

    print(f"运行目录：{run_dir}")

    stage1 = render_stage_prompt(ROOT / "prompts" / "article-structuring.md", context)
    write_text(run_dir / "01-article-structuring.merged.txt", stage1)

    stage2_context = dict(context)
    stage2_context["structured_article_notes"] = context["structured_article_notes"]
    stage2 = render_stage_prompt(ROOT / "prompts" / "platform-copywriting.md", stage2_context)
    write_text(run_dir / "02-platform-copywriting.merged.txt", stage2)

    stage3_context = dict(stage2_context)
    stage3_context["platform_draft"] = context["platform_draft"]
    stage3 = render_stage_prompt(ROOT / "prompts" / "platform-copy-review.md", stage3_context)
    write_text(run_dir / "03-platform-copy-review.merged.txt", stage3)

    summary = {
        "input_file": str(input_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "files": [
            "01-article-structuring.merged.txt",
            "02-platform-copywriting.merged.txt",
            "03-platform-copy-review.merged.txt",
        ],
    }
    write_text(
        run_dir / "run-summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2),
    )

    print(f"已完成。合并结果目录：{run_dir}")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("输入 YAML 格式不正确，顶层必须是对象。")
    return data


def build_context(config: dict[str, Any]) -> dict[str, str]:
    source = config.get("source", {})
    meaning = config.get("meaning_rules", {})
    platform = config.get("platform", {})
    output = config.get("output", {})
    guardrails = config.get("content_guardrails", {})
    intermediate = config.get("intermediate", {})
    target_platform = text_or_default(platform.get("target_platform"), "知乎")
    platform_profile = resolve_platform_profile(target_platform)

    context: dict[str, Any] = {
        "source_title": text_or_default(source.get("source_title"), ""),
        "source_language": text_or_default(source.get("source_language"), "中文"),
        "article_type": text_or_default(source.get("article_type"), "知识分享文章"),
        "source_article": text_or_default(source.get("source_article"), ""),
        "core_message_must_be_preserved": bool_or_default(
            meaning.get("core_message_must_be_preserved"), True
        ),
        "compression_allowed": bool_or_default(meaning.get("compression_allowed"), False),
        "structure_reorganization_allowed": bool_or_default(
            meaning.get("structure_reorganization_allowed"), False
        ),
        "rephrasing_allowed_without_changing_meaning": bool_or_default(
            meaning.get("rephrasing_allowed_without_changing_meaning"), True
        ),
        "new_information_allowed": bool_or_default(
            meaning.get("new_information_allowed"), False
        ),
        "target_platform": target_platform,
        "platform_rule_name": text_or_default(
            platform_profile.get("canonical_name"), target_platform
        ),
        "platform_rule_pack": format_platform_rule_pack(platform_profile),
        "target_audience": text_or_default(
            platform.get("target_audience"),
            "（如未填写，请根据原文判断最适合的核心读者群体）",
        ),
        "platform_style_requirements": text_or_default(
            platform.get("platform_style_requirements"),
            "（无额外补充要求；如有特殊要求再填写）",
        ),
        "length_requirement": text_or_default(
            platform.get("length_requirement"),
            text_or_default(platform_profile.get("recommended_length"), "1500-2500字"),
        ),
        "required_output_parts": list_or_default(
            output.get("required_output_parts"),
            list_or_default(
                platform_profile.get("default_output_parts"),
                ["标题", "正文", "结尾总结"],
            ),
        ),
        "headline_requirement": text_or_default(
            output.get("headline_requirement"),
            text_or_default(
                platform_profile.get("headline_requirement"),
                "避免标题党，突出问题、判断或适用人群。",
            ),
        ),
        "hook_requirement": text_or_default(
            output.get("hook_requirement"),
            text_or_default(
                platform_profile.get("hook_requirement"),
                "开头尽快给出明确结论，并说明适合谁、解决什么问题。",
            ),
        ),
        "ending_requirement": text_or_default(
            output.get("ending_requirement"),
            text_or_default(
                platform_profile.get("ending_requirement"),
                "结尾做总结收束，最好给出行动建议或判断框架。",
            ),
        ),
        "tag_requirement": text_or_default(
            output.get("tag_requirement"),
            text_or_default(
                platform_profile.get("tag_requirement"),
                "如平台需要，再补少量高相关标签；如果不需要可省略。",
            ),
        ),
        "facts_that_must_be_retained": list_or_default(
            guardrails.get("facts_that_must_be_retained"), []
        ),
        "terms_not_to_change": list_or_default(guardrails.get("terms_not_to_change"), []),
        "extra_constraints": text_or_default(
            guardrails.get("extra_constraints"),
            "严格保留原意，不要补充原文没有的新事实、新数据、新案例。",
        ),
        "review_focus": text_or_default(
            config.get("runtime", {}).get("review_focus"),
            "重点检查是否偏离原意、是否遗漏关键事实、是否新增原文没有的信息。",
        ),
        "structured_article_notes": text_or_default(
            intermediate.get("structured_article_notes"),
            "（这里会放整理后的文章材料；当前脚本只负责合并模板，不自动生成此内容）",
        ),
        "platform_draft": text_or_default(
            intermediate.get("platform_draft"),
            "（这里会放平台文稿；当前脚本只负责合并模板，不自动生成此内容）",
        ),
    }

    return {key: stringify(value) for key, value in context.items()}


def resolve_platform_profile(target_platform: str) -> dict[str, Any]:
    rules = load_yaml(PLATFORM_RULES_PATH)
    default_profile = rules.get("default", {})
    platform_profiles = rules.get("platforms", {})

    if not isinstance(default_profile, dict):
        raise SystemExit("platform-rules.yaml 中的 default 配置格式不正确。")
    if not isinstance(platform_profiles, dict):
        raise SystemExit("platform-rules.yaml 中的 platforms 配置格式不正确。")

    normalized_target = normalize_platform_name(target_platform)
    matched_profile: dict[str, Any] | None = None

    for platform_key, profile in platform_profiles.items():
        if not isinstance(profile, dict):
            continue
        aliases = [platform_key, profile.get("canonical_name", "")]
        aliases.extend(profile.get("aliases", []))
        if any(normalize_platform_name(alias) == normalized_target for alias in aliases if alias):
            matched_profile = profile
            break

    resolved_profile = dict(default_profile)
    if matched_profile is not None:
        resolved_profile.update(matched_profile)
        resolved_profile["match_status"] = (
            f"已命中平台预设规则：{resolved_profile.get('canonical_name', target_platform)}"
        )
    else:
        resolved_profile["canonical_name"] = target_platform or resolved_profile.get(
            "canonical_name", "通用图文平台"
        )
        resolved_profile["match_status"] = "未命中专用预设，已回退到通用图文规则。"

    return resolved_profile


def normalize_platform_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-_（）()]+", "", text)
    return text


def format_platform_rule_pack(profile: dict[str, Any]) -> str:
    sections = [
        ("规则命中结果", [text_or_default(profile.get("match_status"), "已应用通用规则。")]),
        ("建议篇幅", [text_or_default(profile.get("recommended_length"), "未设置")]),
        ("推荐输出组成", list_or_default(profile.get("default_output_parts"), ["标题", "正文"])),
        ("平台调性", list_or_default(profile.get("tone_rules"), ["保持信息清楚、表达自然。"])),
        ("结构偏好", list_or_default(profile.get("structure_rules"), ["结构清楚，重点前置。"])),
        ("标题规则", list_or_default(profile.get("title_rules"), ["标题与内容保持一致。"])),
        ("开头规则", list_or_default(profile.get("opening_rules"), ["开头尽快进入主题。"])),
        ("结尾规则", list_or_default(profile.get("ending_rules"), ["结尾做收束。"])),
        ("互动与标签", list_or_default(profile.get("interaction_rules"), ["互动表达保持自然。"])),
        ("风险规避", list_or_default(profile.get("avoid_rules"), ["不要偏离原意。"])),
    ]

    lines: list[str] = [f"平台规则来源：{profile.get('canonical_name', '通用图文平台')}"]
    for title, values in sections:
        lines.append(f"{title}：")
        lines.extend(f"- {value}" for value in values)
    return "\n".join(lines)


def text_or_default(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def bool_or_default(value: Any, default: bool) -> bool:
    if value is None:
        return default
    return bool(value)


def list_or_default(value: Any, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return default
    items = [str(item).strip() for item in value if str(item).strip()]
    return items if items else default


def stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        if not value:
            return "- 无"
        return "\n".join(f"- {item}" for item in value)
    if value is None:
        return ""
    return str(value)


def render_stage_prompt(prompt_path: Path, context: dict[str, str]) -> str:
    template = extract_prompt_block(prompt_path.read_text(encoding="utf-8"))
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    missing = sorted(set(re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", rendered)))
    if missing:
        missing_fields = ", ".join(missing)
        raise SystemExit(f"以下占位符没有被替换：{missing_fields}")

    return rendered.strip() + "\n"


def extract_prompt_block(content: str) -> str:
    match = re.search(r"```text\s*(.*?)```", content, re.DOTALL)
    if not match:
        raise SystemExit("Prompt 文件中没有找到 ```text ... ``` 代码块。")
    return match.group(1).strip()


def make_run_dir(output_root: Path, target_platform: str, input_stem: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(target_platform or input_stem or "run")
    run_dir = output_root / f"{timestamp}-{slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "run"


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
