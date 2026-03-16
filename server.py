"""
Galaxy Classification MCP Server

An MCP server that uses the Qwen VL (Vision Language) model to classify
galaxy images by morphological type (e.g. spiral, elliptical, irregular).
"""

import base64
import os
from pathlib import Path

# Load environment variables from .env file if it exists
from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("Galaxy Classification")

# ---------------------------------------------------------------------------
# Qwen VL client helpers
# ---------------------------------------------------------------------------

_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_DEFAULT_MODEL = "qwen-vl-max"

_SYSTEM_PROMPT = (
    "You are an expert astronomer specialising in galaxy morphology. "
    "When given an image of a galaxy, classify it according to the Hubble "
    "sequence (E0–E7 for ellipticals, S0 for lenticulars, Sa–Sd for normal "
    "spirals, SBa–SBd for barred spirals, Irr for irregulars) or other "
    "relevant morphological types. "
    "Always provide: (1) the morphological type, (2) key visual features "
    "that led to this classification, and (3) a confidence level "
    "(High / Medium / Low)."
)


def _get_client() -> OpenAI:
    """Return an OpenAI-compatible client pointed at the Qwen API."""
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "No Qwen API key found. "
            "Set the DASHSCOPE_API_KEY (or QWEN_API_KEY) environment variable."
        )
    return OpenAI(api_key=api_key, base_url=_QWEN_BASE_URL)


def _image_content(image_source: str) -> dict:
    """
    Build an image content block accepted by the Qwen VL chat API.

    Supports:
    - HTTP/HTTPS URLs  → passed directly as ``image_url``
    - Local file paths → base64-encoded and passed as a data-URI
    """
    if image_source.startswith(("http://", "https://")):
        return {"type": "image_url", "image_url": {"url": image_source}}

    # Treat as a local file path
    path = Path(image_source)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_source}")

    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".fits": "image/fits",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{encoded}"
    return {"type": "image_url", "image_url": {"url": data_uri}}


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
def classify_galaxy(image_source: str, model: str = _DEFAULT_MODEL) -> str:
    """Classify a galaxy image using the Qwen VL vision-language model.

    Args:
        image_source: Either a public HTTP/HTTPS URL pointing to the galaxy
                      image, or an absolute local file path.  Supported
                      formats include JPEG, PNG, GIF, WebP, BMP, TIFF, and
                      FITS (FITS files must be pre-rendered to a standard
                      raster format before being passed here).
        model: Qwen VL model to use.  Defaults to ``qwen-vl-max``.  Other
               options include ``qwen-vl-plus``.

    Returns:
        A plain-text classification report that includes the morphological
        type, key visual features, and a confidence level.
    """
    client = _get_client()

    image_block = _image_content(image_source)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    image_block,
                    {
                        "type": "text",
                        "text": (
                            "Please classify this galaxy image and describe "
                            "its morphological type, key visual features, "
                            "and your confidence level."
                        ),
                    },
                ],
            },
        ],
    )

    if not response.choices:
        raise RuntimeError("Qwen VL API returned an empty response (no choices).")

    return response.choices[0].message.content


@mcp.tool()
def describe_galaxy(image_source: str, question: str, model: str = _DEFAULT_MODEL) -> str:
    """Ask a custom astronomy question about a galaxy image.

    This is a more flexible companion to ``classify_galaxy`` that lets you
    pose any question about the galaxy shown in the image.

    Args:
        image_source: Either a public HTTP/HTTPS URL pointing to the galaxy
                      image, or an absolute local file path.
        question: The question you want to ask about the galaxy image.
        model: Qwen VL model to use.  Defaults to ``qwen-vl-max``.

    Returns:
        The model's answer to your question about the galaxy.
    """
    client = _get_client()

    image_block = _image_content(image_source)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    image_block,
                    {"type": "text", "text": question},
                ],
            },
        ],
    )

    if not response.choices:
        raise RuntimeError("Qwen VL API returned an empty response (no choices).")

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
