"""Main CLI entry point."""

import asyncio


class CLIApplication:
    """Main CLI application class."""

    def __init__(self):
        pass

    async def run(self, args: list[str] | None = None):
        """Run the CLI application."""
        _ = args
        raise NotImplementedError(
            "The legacy CLI is no longer supported. "
            "Use the OpenCode tool suite instead: run opencode in the project root."
        )


def main():
    """Main CLI entry point."""
    app = CLIApplication()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
