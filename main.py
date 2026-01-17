#!/usr/bin/env python3
"""CLI entry point for FunnelCanary."""

import sys

from src.funnel_canary import ProblemSolvingAgent


def main():
    """Main entry point for the CLI."""
    if len(sys.argv) < 2:
        print("用法: uv run python main.py <问题>")
        print("示例: uv run python main.py \"今天北京天气怎么样\"")
        print("示例: uv run python main.py \"123 * 456 等于多少\"")
        sys.exit(1)

    problem = sys.argv[1]

    try:
        agent = ProblemSolvingAgent()
        agent.solve(problem)
    except ValueError as e:
        print(f"配置错误: {e}")
        print("请确保已创建 .env 文件并填入 OPENAI_API_KEY")
        sys.exit(1)
    except Exception as e:
        print(f"运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
