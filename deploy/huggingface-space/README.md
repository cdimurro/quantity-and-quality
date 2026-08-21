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
- API base URL: `https://api.exergyfactor.com/v1`
- Keyless MCP endpoint: `https://api.exergyfactor.com/mcp/`

The public-beta deployment does not require an API key. Results retain the
package's units, reference conditions, basis, boundary, Fidelity Tier,
assumptions, and warnings.

## Render deployment

The repository root contains a `render.yaml` Blueprint for a free Render web
service. Connect this repository in Render with **New → Blueprint**, review the
single `exergy-factor-api` web service, and deploy it on the selected plan.
Render will build the Docker image from this directory and expose the health
check at `/v1/health`. The service is intended for low-volume public use; the
calculator remains available without the hosted API.

The public custom domain is:

```text
https://api.exergyfactor.com/v1
```

The service is keyless. The same image also serves the streamable HTTP MCP
endpoint at `https://api.exergyfactor.com/mcp/` for agents.
