"""CLI tool for loading and rendering prompt templates."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain.exceptions import ConfigurationError  # noqa: E402
from infrastructure.prompts.prompt_loader import PromptLoader  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a prompt template by ID.")
    parser.add_argument(
        "--prompt-id",
        required=True,
        help="Prompt template ID (e.g., 'chapters/create_content')",
    )
    parser.add_argument(
        "--variables",
        default=None,
        help="JSON object string of variables to substitute",
    )
    args = parser.parse_args()

    variables = None
    if args.variables:
        try:
            variables = json.loads(args.variables)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in --variables: {e}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(variables, dict):
            print("Error: --variables must be a JSON object", file=sys.stderr)
            sys.exit(1)

    prompts_dir = PROJECT_ROOT / "prompts"

    # Validate prompt_id does not escape the prompts directory
    resolved_path = (prompts_dir / f"{args.prompt_id}.md").resolve()
    if not resolved_path.is_relative_to(prompts_dir.resolve()):
        print(
            f"Error: prompt ID escapes prompts directory: {args.prompt_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    loader = PromptLoader(prompts_dir=str(prompts_dir))

    try:
        result = loader.load_prompt(args.prompt_id, variables)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
