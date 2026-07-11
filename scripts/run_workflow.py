import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from workflow_core import (
    DEFAULT_OUTPUT_DIR,
    ROOT,
    build_render_context,
    configure_stdio as core_configure_stdio,
    load_workflow_definition,
    load_yaml_dict,
    make_run_dir,
    render_prompt_template,
    write_text,
)


TEMPLATE_PATH = ROOT / "templates" / "article-to-platform-input.example.yaml"


def main() -> None:
    core_configure_stdio()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        run_init(args.output, args.force)
        return

    if args.command == "run":
        run_pipeline(args.input, args.output_dir)
        return

    parser.print_help()

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

    config = load_yaml_dict(input_path)
    workflow = load_workflow_definition("article-to-platform")
    context = build_render_context(config)
    runtime = config.get("runtime", {})
    output_root = Path(output_dir_str or runtime.get("output_dir") or DEFAULT_OUTPUT_DIR)
    run_dir = make_run_dir(output_root, context["target_platform"], input_path.stem)

    print(f"运行目录：{run_dir}")

    generated_files: list[str] = []
    for step in workflow["steps"]:
        rendered = render_prompt_template(Path(step["prompt_path"]), context)
        output_name = f"{step['index']:02d}-{step['id']}.merged.txt"
        write_text(run_dir / output_name, rendered)
        generated_files.append(output_name)

    summary = {
        "input_file": str(input_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "workflow_id": workflow["id"],
        "files": generated_files,
    }
    write_text(
        run_dir / "run-summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2),
    )

    print(f"已完成。合并结果目录：{run_dir}")

if __name__ == "__main__":
    main()
