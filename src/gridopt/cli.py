"""Command line entry point: gridopt validate | run | report."""

from __future__ import annotations

import argparse
from pathlib import Path

from .data import SystemData, repository_root


def main() -> None:
    parser = argparse.ArgumentParser(description="GridOpt Lab: reproducible power-system optimization")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Verify bundled dataset checksums and schema")
    run = sub.add_parser("run", help="Solve all experiments and export CSV/JSON results")
    run.add_argument("--output", type=Path, default=repository_root() / "results/runs/latest")
    run.add_argument("--quick", action="store_true", help="One operating day and one carbon case")
    report = sub.add_parser("report", help="Render figures and an accessible, standalone HTML report")
    report.add_argument("--input", type=Path, default=repository_root() / "results/reference")
    args = parser.parse_args()
    if args.command == "validate":
        data = SystemData.load()
        print(
            f"Checksums OK: {len(data.buses)} buses, {len(data.branches)} branches, "
            f"{len(data.generators)} thermal units, {len(data.profiles)} hourly profiles"
        )
    elif args.command == "run":
        from .experiments import run as experiment

        experiment(args.output, quick=args.quick)
        print(f"Artifacts written to {args.output.resolve()}")
    elif args.command == "report":
        from .reporting import create_report

        create_report(args.input)


if __name__ == "__main__":
    main()
