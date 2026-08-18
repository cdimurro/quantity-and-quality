TEXENGINE ?= tectonic
SOURCE_DATE_EPOCH ?= 1779148800
export SOURCE_DATE_EPOCH
SOURCE ?= Quantity_and_Quality_Third_Draft.tex
JOURNAL_SOURCE ?= Quantity_and_Quality_Journal_Submission_Draft.tex
PUBLIC_PDF ?= quantity-and-quality-standard-reporting-framework.pdf
JOURNAL_PDF ?= Quantity and Quality A Proposed Exergy Factor Reporting Framework for Energy Systems Journal Submission Draft.pdf

.PHONY: pdf preprint journal figures xai4heat clean

pdf: preprint

preprint:
	$(TEXENGINE) --keep-logs --keep-intermediates $(SOURCE)
	cp "$(SOURCE:.tex=.pdf)" "$(PUBLIC_PDF)"

journal:
	$(TEXENGINE) --keep-logs --keep-intermediates $(JOURNAL_SOURCE)
	cp "$(JOURNAL_SOURCE:.tex=.pdf)" "$(JOURNAL_PDF)"

figures:
	cd .. && python scripts/generate_paper_figures.py

xai4heat:
	cd .. && python scripts/analyze_xai4heat.py

clean:
	rm -f *.aux *.log *.out *.toc *.xdv
