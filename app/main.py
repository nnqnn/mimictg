import asyncio

from app.bot.main import run_bot


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()

