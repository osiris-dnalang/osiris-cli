"""Generate paper: python -m nclm.production.paper [--title ...] [--output paper.tex]"""
import argparse
from .paper import generate_paper

def main():
    parser = argparse.ArgumentParser(description="OSIRIS NCLM Paper Generator")
    parser.add_argument("--title", default="OSIRIS NCLM: A Self-Improving Neural Cognitive Language Model")
    parser.add_argument("--output", default="artifacts/paper.tex", help="Output .tex path")
    parser.add_argument("--authors", nargs="*", default=None, help="Author names")
    parser.add_argument("--root", default=None, help="Project root directory")
    args = parser.parse_args()
    path = generate_paper(title=args.title, output=args.output, authors=args.authors, root=args.root)
    print(f"Paper generated: {path}")

if __name__ == "__main__":
    main()
