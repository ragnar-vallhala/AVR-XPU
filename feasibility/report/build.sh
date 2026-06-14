#!/usr/bin/env bash
# Build the findings report. Runs pdflatex twice so all \ref/\label
# cross-references resolve (a single pass leaves "??" / undefined-reference
# warnings). Requires a TeX Live with pgfplots.
set -e
cd "$(dirname "$0")"
DOC=avr-xpu-findings
pdflatex -interaction=nonstopmode -halt-on-error "$DOC.tex" >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error "$DOC.tex" >/dev/null
rm -f "$DOC".aux "$DOC".log "$DOC".out
echo "built $DOC.pdf"
