from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs"
WORKFLOW_DEFINITIONS_DIR = ROOT / "config" / "workflow-definitions"
PLATFORM_RULES_PATH = ROOT / "config" / "platform-rules.yaml"

OUTPUT_START_TAG = "<<<AI_WORKFLOW_OUTPUT_START>>>"
OUTPUT_END_TAG = "<<<AI_WORKFLOW_OUTPUT_END>>>"
PRIMARY_START_TAG = "<<<PRIMARY_CONTENT_START>>>"
PRIMARY_END_TAG = "<<<PRIMARY_CONTENT_END>>>"
JSON_START_TAG = "<<<STRUCTURED_JSON_START>>>"
JSON_END_TAG = "<<<STRUCTURED_JSON_END>>>"
NAMED_BLOCK_START_PREFIX = "<<<NAMED_BLOCK_START:"
NAMED_BLOCK_END_PREFIX = "<<<NAMED_BLOCK_END:"


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def load_yaml_file(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_yaml_dict(path: Path) -> dict[str, Any]:
    data = load_yaml_file(path)
    if not isinstance(data, dict):
        raise SystemExit(f"YAML 顶层格式不正确：{path}")
    return data


def write_yaml_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "run"


def make_run_dir(output_root: Path, target_platform: str, input_stem: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(target_platform or input_stem or "run")
    run_dir = output_root / f"{timestamp}-{slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


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


def normalize_platform_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-_（）()]+", "", text)
    return text


def resolve_platform_profile(target_platform: str) -> dict[str, Any]:
    rules = load_yaml_dict(PLATFORM_RULES_PATH)
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


def flatten_context(data: Any) -> dict[str, str]:
    leaves: list[tuple[list[str], Any]] = []

    def walk(value: Any, path: list[str]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, [*path, key])
            return
        leaves.append((path, value))

    if isinstance(data, dict):
        walk(data, [])

    counters = Counter(path[-1] for path, _ in leaves if path)
    context: dict[str, str] = {}
    for path, value in leaves:
        if not path:
            continue
        full_key = "_".join(path)
        context[full_key] = stringify(value)
        leaf_key = path[-1]
        if counters[leaf_key] == 1:
            context[leaf_key] = stringify(value)
    return context


def build_article_to_platform_context(config: dict[str, Any]) -> dict[str, str]:
    source = config.get("source", {})
    meaning = config.get("meaning_rules", {})
    platform = config.get("platform", {})
    output = config.get("output", {})
    guardrails = config.get("content_guardrails", {})
    intermediate = config.get("intermediate", {})
    review = config.get("review", {})
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
        "latest_review_report": text_or_default(
            review.get("latest_report"),
            "（这里会放最新一轮质检报告；当前脚本只负责保存与串联，不自动生成此内容）",
        ),
    }

    return {key: stringify(value) for key, value in context.items()}


def build_render_context(config: dict[str, Any]) -> dict[str, str]:
    context = flatten_context(config)
    context.update(build_article_to_platform_context(config))
    return context


def extract_prompt_block(content: str) -> str:
    match = re.search(r"```text\s*(.*?)```", content, re.DOTALL)
    if not match:
        raise SystemExit("Prompt 文件中没有找到 ```text ... ``` 代码块。")
    return match.group(1).strip()


def render_prompt_template(prompt_path: Path, context: dict[str, str]) -> str:
    template = extract_prompt_block(load_text(prompt_path))
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    missing = sorted(set(re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", rendered)))
    if missing:
        raise SystemExit(f"以下占位符没有被替换：{', '.join(missing)}")
    return rendered.strip() + "\n"


def list_workflow_definitions() -> list[dict[str, Any]]:
    workflows: list[dict[str, Any]] = []
    for path in sorted(WORKFLOW_DEFINITIONS_DIR.glob("*.yaml")):
        workflows.append(load_workflow_definition(path.stem))
    return workflows


def load_workflow_definition(workflow_id: str) -> dict[str, Any]:
    path = WORKFLOW_DEFINITIONS_DIR / f"{workflow_id}.yaml"
    if not path.exists():
        raise SystemExit(f"找不到工作流定义：{workflow_id}")

    data = load_yaml_dict(path)
    steps = data.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise SystemExit(f"工作流 steps 配置不正确：{path}")

    normalized_steps: list[dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or not step.get("id"):
            raise SystemExit(f"工作流步骤配置不正确：{path}")
        normalized = dict(step)
        normalized["index"] = index
        normalized["title"] = step.get("title", step["id"])
        normalized["prompt_template"] = str(step["prompt_template"])
        normalized["prompt_path"] = ROOT / str(step["prompt_template"])
        normalized["response_target_label"] = step.get("response_target_label", "")
        normalized["prompt_file"] = step.get(
            "prompt_file",
            f"{index:02d}-{step['id']}.prompt.txt",
        )
        normalized["response_file"] = step.get(
            "response_file",
            f"{index:02d}-{step['id']}.response.md",
        )
        normalized["primary_output_file"] = step.get(
            "primary_output_file",
            f"{index:02d}-{step['id']}.content.md",
        )
        normalized["extra_output_blocks"] = step.get("extra_output_blocks", [])
        normalized["required_before_generate"] = step.get("required_before_generate", [])
        normalized_steps.append(normalized)

    return {
        "id": data.get("id", workflow_id),
        "name": data.get("name", workflow_id),
        "description": data.get("description", ""),
        "input_template": data.get("input_template"),
        "field_labels": data.get("field_labels", {}),
        "field_placeholders": data.get("field_placeholders", {}),
        "field_help": data.get("field_help", {}),
        "state_defaults": data.get("state_defaults", {}),
        "steps": normalized_steps,
    }


def deep_merge_dict(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def nested_get(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for segment in dotted_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def nested_set(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    segments = dotted_path.split(".")
    current = data
    for segment in segments[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            child = {}
            current[segment] = child
        current = child
    current[segments[-1]] = value


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def get_missing_requirements(data: dict[str, Any], requirements: list[str]) -> list[str]:
    missing: list[str] = []
    for dotted_path in requirements:
        value = nested_get(data, dotted_path)
        if is_missing_value(value):
            missing.append(dotted_path)
    return missing


def parse_workflow_response(content: str) -> dict[str, Any]:
    text = content.strip()
    if OUTPUT_START_TAG not in text or OUTPUT_END_TAG not in text:
        raise ValueError("缺少外层输出标记。")

    envelope_pattern = (
        re.escape(OUTPUT_START_TAG) + r"\s*(.*?)\s*" + re.escape(OUTPUT_END_TAG)
    )
    envelope_match = re.search(envelope_pattern, text, re.DOTALL)
    if not envelope_match:
        raise ValueError("无法提取外层输出内容。")

    envelope = envelope_match.group(1).strip()
    primary_content = extract_tagged_block(envelope, PRIMARY_START_TAG, PRIMARY_END_TAG)
    json_text = extract_tagged_block(envelope, JSON_START_TAG, JSON_END_TAG, required=False)

    metadata_source = envelope.split(PRIMARY_START_TAG, 1)[0].strip()
    metadata: dict[str, str] = {}
    for line in metadata_source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            raise ValueError(f"元数据格式不正确：{stripped}")
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip()

    parsed_json: Any = None
    if json_text:
        try:
            parsed_json = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"STRUCTURED_JSON 不是合法 JSON：{exc}") from exc

    return {
        "metadata": metadata,
        "primary_content": primary_content.strip(),
        "structured_json": parsed_json,
        "named_blocks": extract_named_blocks(envelope),
    }


def extract_tagged_block(
    content: str,
    start_tag: str,
    end_tag: str,
    required: bool = True,
) -> str | None:
    pattern = re.escape(start_tag) + r"\s*(.*?)\s*" + re.escape(end_tag)
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        if required:
            raise ValueError(f"缺少标记：{start_tag} / {end_tag}")
        return None
    return match.group(1)


def extract_named_blocks(content: str) -> dict[str, str]:
    pattern = (
        re.escape(NAMED_BLOCK_START_PREFIX)
        + r"\s*([a-zA-Z0-9_-]+)\s*>>>\s*(.*?)\s*"
        + re.escape(NAMED_BLOCK_END_PREFIX)
        + r"\s*\1\s*>>>"
    )
    matches = re.findall(pattern, content, re.DOTALL)
    return {block_id: block_content.strip() for block_id, block_content in matches}
