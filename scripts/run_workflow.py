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

    context: dict[str, Any] = {
        "source_title": source.get("source_title", ""),
        "source_language": source.get("source_language", ""),
        "article_type": source.get("article_type", ""),
        "source_article": source.get("source_article", ""),
        "core_message_must_be_preserved": meaning.get("core_message_must_be_preserved", True),
        "compression_allowed": meaning.get("compression_allowed", False),
        "structure_reorganization_allowed": meaning.get("structure_reorganization_allowed", False),
        "rephrasing_allowed_without_changing_meaning": meaning.get(
            "rephrasing_allowed_without_changing_meaning", True
        ),
        "new_information_allowed": meaning.get("new_information_allowed", False),
        "target_platform": platform.get("target_platform", ""),
        "target_audience": platform.get("target_audience", ""),
        "platform_style_requirements": platform.get("platform_style_requirements", ""),
        "length_requirement": platform.get("length_requirement", ""),
        "required_output_parts": output.get("required_output_parts", []),
        "headline_requirement": output.get("headline_requirement", ""),
        "hook_requirement": output.get("hook_requirement", ""),
        "ending_requirement": output.get("ending_requirement", ""),
        "tag_requirement": output.get("tag_requirement", ""),
        "facts_that_must_be_retained": guardrails.get("facts_that_must_be_retained", []),
        "terms_not_to_change": guardrails.get("terms_not_to_change", []),
        "extra_constraints": guardrails.get("extra_constraints", ""),
        "review_focus": config.get("runtime", {}).get(
            "review_focus",
            "重点检查是否偏离原意、是否遗漏关键事实、是否新增原文没有的信息。",
        ),
        "structured_article_notes": intermediate.get(
            "structured_article_notes",
            "（这里会放整理后的文章材料；当前脚本只负责合并模板，不自动生成此内容）",
        ),
        "platform_draft": intermediate.get(
            "platform_draft",
            "（这里会放平台文稿；当前脚本只负责合并模板，不自动生成此内容）",
        ),
    }

    return {key: stringify(value) for key, value in context.items()}


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

