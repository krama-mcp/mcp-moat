#!/usr/bin/env python3
"""
run03_generate_info_graphics.py

Reads summarized markdown files from an input directory, uses Azure OpenAI to generate
comprehensive Mermaid diagrams (mindmap, flowchart, comparison, journey, unified),
and renders them as high-resolution PNG and SVG using mmdc (mermaid-cli).

Usage:
    python run03_generate_info_graphics.py -i <summarize_dir>
    python run03_generate_info_graphics.py -i <summarize_dir> -o <output_dir>
    python run03_generate_info_graphics.py -i <summarize_dir> --scale 8
    python run03_generate_info_graphics.py -i <summarize_dir> --skip-render

Examples:
    # Auto-detect output dir (replaces -summarize with -mmd)
    python run03_generate_info_graphics.py -i MindIsLLM_CH_session-summarize

    # Custom output directory
    python run03_generate_info_graphics.py -i MindIsLLM_CH_session-summarize -o my-diagrams

    # Higher resolution PNGs
    python run03_generate_info_graphics.py -i MindIsLLM_CH_session-summarize --scale 8
"""

import os
import sys
import re
import argparse
import subprocess
import shutil
import requests
from time import sleep
from dotenv import load_dotenv
from progress_utils import ProgressTracker, setup_logging

load_dotenv()
logger = setup_logging(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Mermaid diagram prompts
# ──────────────────────────────────────────────────────────────────────────────

DIAGRAM_SPECS = [
    {
        "name": "mindmap",
        "filename": "01_mindmap.mmd",
        "description": "Comprehensive hierarchical mindmap",
        "prompt": (
            "Create a comprehensive Mermaid MINDMAP diagram that captures ALL major themes, "
            "concepts, sub-topics, and relationships from the content below.\n\n"
            "Requirements:\n"
            "- Use the `mindmap` diagram type\n"
            "- The root node should be the central thesis or topic title\n"
            "- Create 5-8 major branches covering all key areas\n"
            "- Each major branch should have 3-6 leaf nodes with concise descriptions\n"
            "- Capture key terms, definitions, analogies, practical lessons, and open questions\n"
            "- Use `(**bold**)` for major branches\n"
            "- Keep leaf node text concise (under 60 chars)\n"
            "- Do NOT include any title/frontmatter — start directly with `mindmap`\n"
            "- Output ONLY the mermaid code, no markdown fences, no explanation\n"
        ),
    },
    {
        "name": "flowchart_model",
        "filename": "02_flowchart_model.mmd",
        "description": "Conceptual model with relationships and data flow",
        "prompt": (
            "Create a Mermaid FLOWCHART (flowchart TB) diagram that shows the conceptual model "
            "described in the content below — showing entities, how they relate, and how data/information flows.\n\n"
            "Requirements:\n"
            "- Use `flowchart TB` (top-to-bottom)\n"
            "- Group related concepts into `subgraph` blocks with descriptive titles\n"
            "- Show directional relationships with labeled edges (e.g., -->|\"controls\"|)\n"
            "- Use dotted lines (-.->) for parallels/analogies between concepts\n"
            "- Use thick arrows (==>) for primary relationships\n"
            "- Add `classDef` styling with distinct fill colors for each subgraph category\n"
            "- Include 4-8 subgraphs covering the major conceptual areas\n"
            "- Each subgraph should have 3-6 nodes\n"
            "- Do NOT include any title/frontmatter — start directly with `flowchart TB`\n"
            "- Output ONLY the mermaid code, no markdown fences, no explanation\n"
        ),
    },
    {
        "name": "comparison",
        "filename": "03_comparison.mmd",
        "description": "Side-by-side comparison of two parallel concepts",
        "prompt": (
            "Create a Mermaid FLOWCHART (flowchart LR) diagram that shows a side-by-side "
            "comparison/mapping between the two main parallel concepts in the content below.\n\n"
            "Requirements:\n"
            "- Use `flowchart LR` (left-to-right)\n"
            "- Create two `subgraph` blocks side by side, one for each parallel concept\n"
            "- Within each subgraph, show the internal hierarchy (controller → engine → components)\n"
            "- Connect corresponding nodes across subgraphs with dotted equivalence lines: `<-..->|\"≡\"|`\n"
            "- Map at least 8-12 corresponding pairs\n"
            "- Use `classDef` with two distinct colors (one per side)\n"
            "- Each node should have a bold label and an italic description\n"
            "- Do NOT include any title/frontmatter — start directly with `flowchart LR`\n"
            "- Output ONLY the mermaid code, no markdown fences, no explanation\n"
        ),
    },
    {
        "name": "journey",
        "filename": "04_journey_progression.mmd",
        "description": "Progression/journey through levels or stages",
        "prompt": (
            "Create a Mermaid FLOWCHART (flowchart BT or LR) diagram that shows a progression "
            "or journey through levels/stages described in the content below.\n\n"
            "Requirements:\n"
            "- Use `flowchart BT` (bottom-to-top) to show ascension through levels\n"
            "- Create 4-6 level subgraphs, each representing a stage in the progression\n"
            "- Each level should have 3-4 descriptive nodes about what characterizes that stage\n"
            "- Connect levels with labeled edges describing the transition/practice\n"
            "- Optionally add a parallel track showing the corresponding technical/practical analogy\n"
            "- Use `classDef` with gradient colors from warm (bottom) to cool (top)\n"
            "- Do NOT include any title/frontmatter — start directly with `flowchart`\n"
            "- Output ONLY the mermaid code, no markdown fences, no explanation\n"
        ),
    },
    {
        "name": "unified",
        "filename": "05_FULL_unified.mmd",
        "description": "Complete unified diagram connecting all concepts",
        "prompt": (
            "Create a single comprehensive Mermaid FLOWCHART (flowchart TB) diagram that unifies ALL "
            "major concepts from the content below into one interconnected picture.\n\n"
            "Requirements:\n"
            "- Use `flowchart TB`\n"
            "- Start with a central thesis node at the top using stadium shape `([...])`\n"
            "- Create 5-7 `subgraph` sections covering: the two parallel systems being compared, "
            "the shared architecture/hierarchy, the progression journey, practical lessons, and open questions\n"
            "- The two parallel systems should be in a wrapper subgraph side by side\n"
            "- Connect sections with thick labeled arrows (==>) showing how they relate\n"
            "- Use equivalence links (~~~|\"≡\"|) between corresponding nodes in the parallel systems\n"
            "- Use `classDef` with distinct colors per section\n"
            "- Aim for 40-60 total nodes — comprehensive but not overwhelming\n"
            "- This diagram should tell the complete story when read top-to-bottom\n"
            "- Do NOT include any title/frontmatter — start directly with `flowchart TB`\n"
            "- Output ONLY the mermaid code, no markdown fences, no explanation\n"
        ),
    },
]


class InfographicGenerator:
    """Generates Mermaid infographic diagrams from summarized content using Azure OpenAI."""

    def __init__(self, input_dir, output_dir, scale=4, skip_render=False):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.scale = scale
        self.skip_render = skip_render

        # Azure OpenAI config
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not self.api_key or not self.api_endpoint:
            raise ValueError(
                "Azure OpenAI credentials not found in .env file.\n"
                "Required: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT"
            )

        self.api_url = (
            f"{self.api_endpoint}openai/deployments/{self.deployment_name}"
            f"/chat/completions?api-version={self.api_version}"
        )
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        self.request_delay = 3
        self.retry_delay = 30
        self.max_retries = 3

    def read_summarized_content(self):
        """Read and combine all markdown files from the input directory."""
        md_files = sorted(
            f for f in os.listdir(self.input_dir) if f.endswith(".md")
        )
        if not md_files:
            raise FileNotFoundError(f"No .md files found in {self.input_dir}")

        combined = []
        for fname in md_files:
            fpath = os.path.join(self.input_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            combined.append(f"--- {fname} ---\n{content}")
            logger.info(f"Read: {fname} ({len(content)} chars)")

        full_text = "\n\n".join(combined)
        logger.info(f"Combined content: {len(full_text)} chars from {len(md_files)} files")
        return full_text

    def call_azure_openai(self, system_prompt, user_prompt):
        """Call Azure OpenAI API with retry logic."""
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 8000,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 429:
                    logger.warning(f"Rate limited (attempt {attempt}), waiting {self.retry_delay}s...")
                    sleep(self.retry_delay)
                    continue

                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()

            except requests.exceptions.RequestException as e:
                logger.error(f"API error (attempt {attempt}): {e}")
                if attempt < self.max_retries:
                    sleep(self.retry_delay)
                else:
                    raise
        return None

    def clean_mermaid_output(self, raw_output):
        """Strip markdown fences and frontmatter from LLM output."""
        text = raw_output.strip()
        # Remove ```mermaid ... ``` fencing
        text = re.sub(r"^```(?:mermaid)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        # Remove YAML frontmatter
        text = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL)
        return text.strip()

    def generate_diagram(self, spec, content):
        """Generate a single Mermaid diagram using Azure OpenAI."""
        system_prompt = (
            "You are an expert at creating Mermaid.js diagrams. "
            "You output ONLY valid Mermaid diagram code — no markdown fences, "
            "no explanations, no titles. The output must be directly parseable by `mmdc`."
        )
        user_prompt = f"{spec['prompt']}\n\nCONTENT:\n\n{content}"

        raw = self.call_azure_openai(system_prompt, user_prompt)
        if not raw:
            return None
        return self.clean_mermaid_output(raw)

    def render_mermaid(self, mmd_path):
        """Render a .mmd file to PNG (high-res) and SVG using mmdc."""
        mmdc_path = shutil.which("mmdc")
        if not mmdc_path:
            logger.warning("mmdc not found — skipping render. Install with: npm i -g @mermaid-js/mermaid-cli")
            return False

        base = mmd_path.rsplit(".mmd", 1)[0]
        png_path = f"{base}.png"
        svg_path = f"{base}.svg"

        success = True
        # Render PNG at high scale
        try:
            result = subprocess.run(
                [mmdc_path, "-i", mmd_path, "-o", png_path, "-s", str(self.scale), "-b", "white"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"  PNG: {png_path}")
            else:
                logger.error(f"  PNG render failed: {result.stderr}")
                success = False
        except subprocess.TimeoutExpired:
            logger.error(f"  PNG render timed out for {mmd_path}")
            success = False

        # Render SVG
        try:
            result = subprocess.run(
                [mmdc_path, "-i", mmd_path, "-o", svg_path, "-b", "transparent"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"  SVG: {svg_path}")
            else:
                logger.error(f"  SVG render failed: {result.stderr}")
                success = False
        except subprocess.TimeoutExpired:
            logger.error(f"  SVG render timed out for {mmd_path}")
            success = False

        return success

    def run(self):
        """Main execution: read content, generate diagrams, render images."""
        os.makedirs(self.output_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print("  INFOGRAPHIC GENERATOR")
        print("=" * 60)
        print(f"  Input:  {self.input_dir}")
        print(f"  Output: {self.output_dir}")
        print(f"  Scale:  {self.scale}x")
        print(f"  Render: {'yes' if not self.skip_render else 'skip'}")
        print("=" * 60 + "\n")

        # Step 1: Read content
        print("Reading summarized content...")
        content = self.read_summarized_content()
        print(f"  Combined {len(content)} characters\n")

        # Step 2: Generate diagrams
        progress = ProgressTracker(
            total_items=len(DIAGRAM_SPECS),
            task_name="Mermaid Diagram Generation",
        )
        progress.start()

        generated_files = []

        for spec in DIAGRAM_SPECS:
            progress.start_item(f"{spec['name']} — {spec['description']}")

            mmd_path = os.path.join(self.output_dir, spec["filename"])

            # Generate
            diagram_code = self.generate_diagram(spec, content)
            if not diagram_code:
                logger.error(f"Failed to generate {spec['name']}")
                progress.complete_item(spec["name"], success=False)
                continue

            # Write .mmd file
            with open(mmd_path, "w", encoding="utf-8") as f:
                f.write(diagram_code + "\n")
            logger.info(f"Written: {mmd_path} ({len(diagram_code)} chars)")

            # Render
            if not self.skip_render:
                render_ok = self.render_mermaid(mmd_path)
                if not render_ok:
                    logger.warning(f"Render issues for {spec['name']} — .mmd file still saved")

            generated_files.append(mmd_path)
            progress.complete_item(spec["name"], success=True)

            # Delay between API calls
            sleep(self.request_delay)

        progress.finish()

        # Summary
        print("\n" + "=" * 60)
        print("  GENERATION COMPLETE")
        print("=" * 60)
        print(f"  Generated {len(generated_files)}/{len(DIAGRAM_SPECS)} diagrams")
        print(f"  Output directory: {self.output_dir}")
        print()
        for f in generated_files:
            base = os.path.basename(f)
            print(f"    {base}")
            if not self.skip_render:
                print(f"    {base.replace('.mmd', '.png')}  ({self.scale}x)")
                print(f"    {base.replace('.mmd', '.svg')}")
        print("=" * 60)

        return len(generated_files)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Mermaid infographic diagrams from summarized content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python run03_generate_info_graphics.py -i MindIsLLM_CH_session-summarize\n"
            "  python run03_generate_info_graphics.py -i session-summarize -o session-mmd --scale 8\n"
            "  python run03_generate_info_graphics.py -i session-summarize --skip-render\n"
        ),
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input directory containing summarized .md files (e.g., *-summarize folder)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory for .mmd, .png, .svg files (default: auto-detect from input name)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=4,
        help="PNG render scale factor (default: 4 for high-res)",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip PNG/SVG rendering (only generate .mmd files)",
    )
    return parser.parse_args()


def auto_output_dir(input_dir):
    """Derive output directory name from input: replace -summarize with -mmd."""
    base = os.path.basename(os.path.normpath(input_dir))
    if base.endswith("-summarize"):
        return base.replace("-summarize", "-mmd")
    return f"{base}-mmd"


def main():
    args = parse_args()

    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    output_dir = args.output or auto_output_dir(input_dir)

    generator = InfographicGenerator(
        input_dir=input_dir,
        output_dir=output_dir,
        scale=args.scale,
        skip_render=args.skip_render,
    )
    count = generator.run()

    if count == 0:
        print("ERROR: No diagrams were generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
