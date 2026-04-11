#!/bin/bash
# Compile LaTeX paper for arXiv submission

cd "/home/dnalang/dnalang-quantum-corpus-v1.0/paper"
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex

echo "Generated: main.pdf"
