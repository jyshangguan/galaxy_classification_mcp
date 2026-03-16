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

# Load classification instructions from markdown file
_INSTRUCTION_FILE = Path(__file__).parent / "galaxy_classification_instruction.md"

if _INSTRUCTION_FILE.exists():
    _CLASSIFICATION_INSTRUCTIONS = _INSTRUCTION_FILE.read_text()
else:
    _CLASSIFICATION_INSTRUCTIONS = """
    You are an expert galaxy morphologist. Please analyze galaxy images with
    isophotal contours and provide morphological classification.
    """

_SYSTEM_PROMPT = f"""You are a galaxy morphology classification assistant.

{_CLASSIFICATION_INSTRUCTIONS}

When analyzing images, always:
- Use only unmasked regions for analysis
- Consider grayscale brightness distribution and isophotal contours together
- Follow the sequential decision process outlined above
- Output results in the specified format
- Be cautious and use "Uncertain" when evidence is insufficient
"""


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
    """Classify a galaxy image using isophotal contours following detailed morphological criteria.

    This tool analyzes galaxy images with mask overlays (red regions) and isophotal
    contours (cyan, lime, magenta) to determine:
    - Number of independent galaxies
    - Morphology (disk vs elliptical)
    - Presence of bars, spiral arms, and tidal tails

    The classification follows a rigorous decision process based on contour analysis
    as specified in galaxy_classification_instruction.md.

    Args:
        image_source: Either a public HTTP/HTTPS URL pointing to the galaxy
                      image, or an absolute local file path.  Supported
                      formats include JPEG, PNG, GIF, WebP, BMP, TIFF, and
                      FITS (FITS files must be pre-rendered to a standard
                      raster format before being passed here).
                      Images should include:
                      - Red mask regions indicating unreliable/contaminated areas
                      - Grayscale intensity (black=low, white=high signal)
                      - Cyan/lime/magenta isophotal contours for structure analysis
        model: Qwen VL model to use.  Defaults to ``qwen-vl-max``.  Other
               options include ``qwen-vl-plus``.

    Returns:
        A structured classification report including:
        1. Mask count
        2. Galaxy count
        3. Morphology judgment
        4. Bar presence
        5. Spiral arm presence
        6. Tidal tail presence
        7. Structural feature description with reasoning
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
                            "Please analyze this galaxy image following the classification "
                            "instructions. Provide your analysis in the specified output format:\n\n"
                            "Source ID: [Unknown]\n"
                            "1. Mask count:\n"
                            "2. Galaxy count:\n"
                            "3. Galaxy morphology judgment:\n"
                            "4. Bar:\n"
                            "5. Spiral arms:\n"
                            "6. Tidal tail:\n"
                            "7. Structural feature description:\n\n"
                            "Remember: Red regions are masked areas to ignore. Cyan/lime/magenta "
                            "contours show isophotal structure. Darker = lower signal, brighter = higher signal."
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
    pose any question about the galaxy shown in the image. The model uses
    the same morphological expertise from galaxy_classification_instruction.md.

    Args:
        image_source: Either a public HTTP/HTTPS URL pointing to the galaxy
                      image, or an absolute local file path. Images should
                      include mask overlays (red) and isophotal contours
                      (cyan, lime, magenta) for optimal analysis.
        question: The question you want to ask about the galaxy image.
                  The model will use its expertise in galaxy morphology
                  and contour analysis to answer.
        model: Qwen VL model to use.  Defaults to ``qwen-vl-max``.

    Returns:
        The model's answer to your question about the galaxy, based on
        morphological analysis of contours and brightness distribution.
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
