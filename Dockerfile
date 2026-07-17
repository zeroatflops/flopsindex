# Dockerfile — FLOPS Index MCP server (for Glama.ai server introspection).
#
# Glama builds this image, starts the stdio MCP server, and issues an
# initialize + tools/list handshake. tools/list is static, so introspection
# passes with no network or credentials. Actual tool calls hit the public,
# key-free API (app.flopsindex.com) at runtime.
FROM python:3.12-slim

WORKDIR /app

# Build the server straight from this repo's source (version-matched, no PyPI
# round-trip). The package exposes the `flopsindex-mcp` console entrypoint.
COPY mcp/ /app/mcp/
RUN pip install --no-cache-dir ./mcp

# Glama drives the server over stdio.
ENTRYPOINT ["flopsindex-mcp"]
