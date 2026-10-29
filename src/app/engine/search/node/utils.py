import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo


def format_search_results(results: list[dict]) -> str:
    if not results:
        return "Result not found."
    
    lines = []
    for index, result in enumerate(results, start=1):
        title = result.get("title", "-")
        url = result.get("url", "-")
        description = result.get("description", "-")
        tags = result.get("tags", [])
        score = result.get("score") or 0.0
        created_at = result.get("created_at")

        created_string = "null"
        if created_at is not None:
            try:
                created_string = datetime.fromtimestamp(created_at / 1000, tz=ZoneInfo("Asia/Seoul")).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except (TypeError, ValueError):
                pass
        
        tags_string = ", ".join(tags) if tags else "-"
        
        lines.append(
            textwrap.dedent(f"""
            **{index}. {title}** (Score: {score:.2f})
            {description}
            Tags: {tags_string}
            Created: {created_string}
            {url}
            """)
        )

    header = f"Found {len(results)} related results: \n\n"
    return header + "\n\n".join(lines)
