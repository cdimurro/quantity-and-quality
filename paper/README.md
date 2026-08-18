# Paper and reproducibility

The canonical publication is
[`quantity-and-quality-standard-reporting-framework.pdf`](quantity-and-quality-standard-reporting-framework.pdf),
built from [`Quantity_and_Quality_Third_Draft.tex`](Quantity_and_Quality_Third_Draft.tex).

The empirical demonstration uses the public XAI4HEAT repository at commit
`fc7ee9a`. From the repository root:

```bash
git clone https://github.com/xai4heat/xai4heat runtime/external/xai4heat
git -C runtime/external/xai4heat checkout fc7ee9a
python -m pip install ".[paper]"
python scripts/analyze_xai4heat.py
python scripts/generate_paper_figures.py
make -C paper pdf
```

`make` uses `tectonic` by default. Override it with `TEXENGINE=/path/to/tectonic`
when needed. The XAI4HEAT checkout remains under the ignored `runtime/` directory;
its pinned commit and the analysis code make the input independently recoverable.

Generated CSV tables are in `paper/generated/`. The four PDF figures used by the
paper are tracked alongside the source so readers can inspect the exact published
artifacts without rebuilding them.
