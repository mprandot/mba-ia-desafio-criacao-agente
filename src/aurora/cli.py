import argparse
import sys

from aurora.infra.repository import restore


def main() -> None:
    parser = argparse.ArgumentParser(prog="aurora")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("restore", help="Restaura reservas e visitantes aos dados iniciais")
    args = parser.parse_args()
    if args.comando == "restore":
        restore()
        print("Dados iniciais restaurados.")


if __name__ == "__main__":
    main()
    sys.exit(0)
