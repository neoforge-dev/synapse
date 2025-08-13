from typing import Any, List


def _rich_text_to_plain(rt: List[dict]) -> str:
    out = []
    for part in rt or []:
        text = part.get("plain_text")
        if text:
            out.append(text)
    return "".join(out)


def render_blocks_to_markdown(blocks: List[dict], include_assets: bool = True) -> str:
    """Very simple Notion block renderer to Markdown/plain text.

    Supports: paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item, quote, code, image, file.
    """
    lines: List[str] = []
    for b in blocks or []:
        t = b.get("type")
        data = b.get(t, {}) if t else {}
        if t == "paragraph":
            lines.append(_rich_text_to_plain(data.get("rich_text", [])))
        elif t == "heading_1":
            lines.append("# " + _rich_text_to_plain(data.get("rich_text", [])))
        elif t == "heading_2":
            lines.append("## " + _rich_text_to_plain(data.get("rich_text", [])))
        elif t == "heading_3":
            lines.append("### " + _rich_text_to_plain(data.get("rich_text", [])))
        elif t == "bulleted_list_item":
            lines.append("- " + _rich_text_to_plain(data.get("rich_text", [])))
        elif t == "numbered_list_item":
            lines.append("1. " + _rich_text_to_plain(data.get("rich_text", [])))
        elif t == "quote":
            lines.append("> " + _rich_text_to_plain(data.get("rich_text", [])))
        elif t == "code":
            code = _rich_text_to_plain(data.get("rich_text", []))
            lang = data.get("language") or ""
            fence = f"```{lang}" if lang else "```"
            lines.append(fence)
            lines.append(code)
            lines.append("```")
        elif t == "image":
            if not include_assets:
                continue
            src = None
            if data.get("type") == "external":
                src = data.get("external", {}).get("url")
            elif data.get("type") == "file":
                src = data.get("file", {}).get("url")
            cap = _rich_text_to_plain(data.get("caption", []))
            if src:
                lines.append(f"![{cap}]({src})")
        elif t == "file":
            if not include_assets:
                continue
            src = None
            if data.get("type") == "external":
                src = data.get("external", {}).get("url")
            elif data.get("type") == "file":
                src = data.get("file", {}).get("url")
            name = data.get("name") or "file"
            if src:
                lines.append(f"[{name}]({src})")
        # ignore other unsupported blocks for now
    return "\n\n".join([ln for ln in lines if ln is not None])
