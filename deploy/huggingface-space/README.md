---
title: Exergy Factor API
emoji: ⚡
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
license: mit
---

# Exergy Factor API

Public, deterministic HTTP access to the
[`quantity-and-quality`](https://pypi.org/project/quantity-and-quality/) calculation
kernel used by [exergyfactor.com](https://www.exergyfactor.com/).

- Interactive OpenAPI documentation: `/docs`
- Health check: `/v1/health`
- API base path: `/v1`

The public-beta deployment does not require an API key. Results retain the
package's units, reference conditions, basis, boundary, Fidelity Tier,
assumptions, and warnings.

