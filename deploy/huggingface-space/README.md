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

## Free Render deployment

The repository root contains a `render.yaml` Blueprint for a free Render web
service. Connect this repository in Render with **New → Blueprint**, review the
single `exergy-factor-api` web service, and deploy it on the Free plan. Render
will build the Docker image from this directory and expose the health check at
`/v1/health`. Free instances may sleep after inactivity and are intended for
hobby or preview use; the calculator remains available without the hosted API.

The resulting default URL is:

```text
https://exergy-factor-api.onrender.com/v1
```
