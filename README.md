# galaxy_classification_mcp

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server
that lets Claude (or any other MCP-compatible client) classify galaxy images
using the **Qwen VL** (Vision–Language) model hosted on Alibaba Cloud's
DashScope platform.

---

## Features

| Tool | Description |
|------|-------------|
| `classify_galaxy` | Classifies a galaxy image by Hubble-sequence morphological type (spiral, elliptical, irregular …) and returns key visual features plus a confidence level. |
| `describe_galaxy` | Lets you ask any custom astronomy question about a galaxy image. |

Both tools accept either a **public HTTPS URL** or an **absolute local file path** as the image source.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python ≥ 3.10 | Tested with 3.10 – 3.12 |
| DashScope API key | Free tier available at [dashscope.aliyun.com](https://dashscope.aliyun.com/) |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/jyshangguan/galaxy_classification_mcp.git
cd galaxy_classification_mcp

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy .env.example to .env and add your API key
cp .env.example .env
# Then edit .env and replace sk-your-api-key-here with your actual API key
```

---

## Configuration

The server reads your Qwen API key from the environment.  Choose **one** of the
following methods:

### Method 1: Using a `.env` file (recommended)

Create a `.env` file in the project root:

```bash
DASHSCOPE_API_KEY=sk-your-actual-api-key-here
```

The `.env` file is already in `.gitignore` to prevent accidentally committing
your API key.

### Method 2: Environment variable

```bash
# Preferred variable name
export DASHSCOPE_API_KEY="sk-..."

# Alternative (both are checked)
export QWEN_API_KEY="sk-..."
```

You can obtain a free API key from
[https://dashscope.aliyun.com/](https://dashscope.aliyun.com/) after
registering for an Alibaba Cloud account.

---

## Running the server

### Stdio transport (default — for Claude Desktop / Claude Code)

```bash
python server.py
```

The server speaks the MCP stdio protocol and is ready to be connected to by
Claude Desktop or Claude Code via the configuration below.

### SSE transport (for testing with `mcp dev`)

```bash
mcp dev server.py
```

---

## Connecting to Claude Desktop

Add the following block to your Claude Desktop configuration file
(`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "galaxy-classification": {
      "command": "python",
      "args": ["/absolute/path/to/galaxy_classification_mcp/server.py"]
    }
  }
}
```

Replace `/absolute/path/to/galaxy_classification_mcp/server.py` with the
actual path on your machine.

**Note:** The API key should be stored in a `.env` file in the project directory
(see [Configuration](#configuration) above). Alternatively, you can pass it
directly in the config by adding an `"env"` block with `"DASHSCOPE_API_KEY"`.

---

## Connecting to Claude Code (CLI)

If you have a `.env` file with your API key (recommended):

```bash
claude mcp add galaxy-classification \
  -- python /absolute/path/to/galaxy_classification_mcp/server.py
```

Alternatively, pass the API key directly:

```bash
claude mcp add galaxy-classification \
  -e DASHSCOPE_API_KEY=sk-... \
  -- python /absolute/path/to/galaxy_classification_mcp/server.py
```

---

## Example usage in Claude

Once the MCP server is connected you can ask Claude questions like:

```
Classify the galaxy in this image:
https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/NGC_4414_%28NASA-med%29.jpg/1024px-NGC_4414_%28NASA-med%29.jpg
```

Claude will call the `classify_galaxy` tool and return a structured report
such as:

```
Morphological type : Sc (late-type spiral)
Key visual features: Two loosely wound, patchy spiral arms; bright,
                     compact nucleus; clumpy star-forming regions along
                     the arms; no bar visible.
Confidence         : High
```

---

## Available models

| Model | Notes |
|-------|-------|
| `qwen-vl-max` | Highest capability (default) |
| `qwen-vl-plus` | Faster, lower cost |

Pass the `model` argument to either tool to switch models:

```
Use qwen-vl-plus to classify: https://example.com/galaxy.jpg
```

---

## Project structure

```
galaxy_classification_mcp/
├── server.py          # MCP server (FastMCP, Qwen VL tools)
├── requirements.txt   # Python dependencies
├── .env.example       # Example environment variables template
├── .env               # Your actual API key (not in git)
├── pyproject.toml     # Project metadata
└── README.md          # This file
```

---

## License

See [LICENSE](LICENSE).
