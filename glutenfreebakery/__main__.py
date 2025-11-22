import argparse
import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence, cast

from . import __name__ as module_name
from .gltf import Gltf2


def main(argv: Sequence[str] | None = None):
    parser = ArgumentParser(module_name)
    subparsers = parser.add_subparsers(dest="command")

    parser_convert = subparsers.add_parser(
        "convert", help="Convert a GlTF file between `.gltf` and `.glb` formats"
    )
    parser_convert.add_argument("input")
    parser_convert.add_argument("output")

    fix_help_text(parser)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        parser.exit(1)

    logging.basicConfig(level=logging.DEBUG)

    if args.command == "convert":
        convert(Path(args.input), Path(args.output))


def convert(input: Path, output: Path) -> None:
    gltf = Gltf2.Read(input)

    if output.suffix.lower() == ".glb":
        gltf.embed_resources()
    elif output.suffix.lower() == ".gltf":
        gltf.extract_resources(output.parent, f"{output.stem}.")

    gltf.write(output)


def fix_help_text(parser: ArgumentParser, usage_prefix: str = "usage: "):
    def subparsers():
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):  # type: ignore
                for subparser in action.choices.values():
                    yield cast(ArgumentParser, subparser)

    def usages():
        for subparser in subparsers():
            yield subparser.format_usage().removeprefix(usage_prefix).rstrip()

    parser.usage = f"\n{' '*len(usage_prefix)}".join(usages())


if __name__ == "__main__":  # pragma: nocover
    exit(main())
