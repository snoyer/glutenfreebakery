import argparse
import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence, cast

from . import __name__ as module_name
from .gltf import Gltf2
from .schema_io import read_glb_chunks


def main(argv: Sequence[str] | None = None):
    parser = ArgumentParser(module_name)
    subparsers = parser.add_subparsers(dest="command")

    parser_convert = subparsers.add_parser(
        "convert", help="Convert a GlTF file between `.gltf` and `.glb` formats."
    )
    parser_convert.add_argument("input")
    parser_convert.add_argument("output")

    parser_unpack = subparsers.add_parser(
        "unpack",
        help="Unpack a `.glb` file into a `.json` file and maybe a `.bin` file.",
    )
    parser_unpack.add_argument("input", metavar="in.glb")
    parser_unpack.add_argument("output_json", metavar="out.json")

    fix_help_text(parser)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        parser.exit(1)

    logging.basicConfig(level=logging.DEBUG)

    if args.command == "convert":
        convert(Path(args.input), Path(args.output))
    elif args.command == "unpack":
        output_json = Path(args.output_json)
        unpack(Path(args.input), output_json)


def convert(input: Path, output: Path) -> None:
    gltf = Gltf2.Read(input)

    if output.suffix.lower() == ".glb":
        gltf.embed_resources()
    elif output.suffix.lower() == ".gltf":
        gltf.extract_resources(output.parent, f"{output.stem}.")

    gltf.write(output)


def unpack(input: Path, output_json: Path):
    suffixes = {
        b"JSON": ".json",
        b"BIN\0": ".bin",
    }
    for chunk_type, chunk_data in read_glb_chunks(open(input, "rb")):
        suffix = suffixes.get(chunk_type, f".{chunk_type.decode()}")
        output_json.with_suffix(suffix).write_bytes(chunk_data)


def fix_help_text(parser: ArgumentParser, usage_prefix: str = "usage: "):
    def subparsers():
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):  # type: ignore
                for subparser in action.choices.values():
                    yield cast(ArgumentParser, subparser)

    def usages():
        for subparser in subparsers():
            yield subparser.format_usage().removeprefix(usage_prefix).rstrip()

    parser.usage = f"\n{' ' * len(usage_prefix)}".join(usages())


if __name__ == "__main__":  # pragma: nocover
    exit(main())
