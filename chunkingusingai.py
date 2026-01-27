"""
Semantic Chunking of Markdown Files using Ollama (Mistral 7B)

This script chunks medical markdown documents into 5 predefined sections:
1. Demographics
2. Condition at the start of treatment/vital parameters
3. Diagnosis
4. Condition at the end of the treatment/vital parameters
5. Physician outcomes/Outcome scales

Key points:
- The markdown is preprocessed so that ONLY headings and bold lines are sent to the AI model.
- The AI model (Mistral 7B via Ollama) decides which headings belong to which section.
- The final chunks contain the ORIGINAL content (no summarising, no rewriting).
- Output is a .txt file containing each section and its full content.

Usage:
    python chunkingusingai.py [path_to_markdown_file]

Requirements:
    1. Install Ollama from https://ollama.ai
    2. Pull the model: ollama pull mistral
    3. Install Python package: pip install ollama
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import ollama


class SemanticChunker:
    """
    Semantic chunking of markdown files into 5 predefined sections using Ollama (Mistral 7B).
    The model sees only headings and bold lines; the output chunks use original content.
    """

    SECTIONS = [
        "Demographics",
        "Condition at the start of treatment/vital parameters",
        "Diagnosis",
        "Condition at the end of the treatment/vital parameters",
        "Physician outcomes/Outcome scales",
    ]

    def __init__(self, model_name: str = "mistral"):
        """
        Initialize the chunker with an Ollama model.

        Args:
            model_name: Name of the Ollama model to use (default: mistral)
        """
        self.model_name = model_name

    # ------------------------------------------------------------------
    # Markdown preprocessing
    # ------------------------------------------------------------------
    def _extract_headings(self, lines: List[str]) -> List[Dict]:
        """
        Extract markdown headings and their line indices.

        Returns list of dicts with:
            - index: line index in the original file
            - text: heading line text (full line)
        """
        headings = []
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

        for i, line in enumerate(lines):
            if heading_pattern.match(line):
                headings.append({"index": i, "text": line.strip()})

        return headings

    def _build_skeleton(
        self, markdown_content: str
    ) -> Tuple[str, List[Dict], List[str]]:
        """
        Build a skeleton text containing only headings and bold lines.

        Returns:
            skeleton_text: text sent to the model
            headings: list of heading dicts (index, text)
            lines: original lines list
        """
        lines = markdown_content.splitlines()
        headings = self._extract_headings(lines)

        skeleton_lines: List[str] = []

        # Add headings with IDs so model can reference them precisely
        for idx, h in enumerate(headings):
            skeleton_lines.append(f'HEADING_{idx}: "{h["text"]}"')

        # Add bold lines (lines that contain **...**)
        bold_pattern = re.compile(r"\*\*(.+?)\*\*")
        for i, line in enumerate(lines):
            if bold_pattern.search(line) and not line.strip().startswith("#"):
                skeleton_lines.append(f'BOLD_LINE (line {i}): "{line.strip()}"')

        skeleton_text = "\n".join(skeleton_lines)
        return skeleton_text, headings, lines

    # ------------------------------------------------------------------
    # Model interaction
    # ------------------------------------------------------------------
    def _ask_model_for_section_headings(
        self, skeleton_text: str
    ) -> Dict[str, List[str]]:
        """
        Ask the model to assign headings to each of the 5 sections.

        Returns:
            Dict mapping section name -> list of HEADING_* IDs
        """
        sections_str = "\n".join(f"- {name}" for name in self.SECTIONS)

        prompt = f"""You are given a skeleton of a medical discharge summary in markdown form.
The skeleton contains ONLY headings (as HEADING_N entries) and some bold lines.

You must decide which HEADING_N entries belong to each of the following 5 sections:
{sections_str}

IMPORTANT RULES:
- Use ONLY the HEADING_N identifiers, not the bold lines, to build your answer.
- A heading can belong to at most ONE section.
- If a section has no relevant headings, return an empty list for that section.
- Demographics will usually be early headings like patient details, admission/discharge info, etc.
- The other sections are based on clinical meaning (start condition/vitals, diagnosis, end condition/vitals, outcomes).

SKELETON:
{skeleton_text}

Respond with VALID JSON ONLY, with this exact structure (no extra text):
{{
  "Demographics": ["HEADING_0", "HEADING_3"],
  "Condition at the start of treatment/vital parameters": ["HEADING_1"],
  "Diagnosis": ["HEADING_2"],
  "Condition at the end of the treatment/vital parameters": [],
  "Physician outcomes/Outcome scales": []
}}

Now fill in the correct HEADING_* lists for each section, based on the skeleton above.
"""
        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={"temperature": 0.2},
        )

        raw = response.get("response", "").strip()

        # Try to parse JSON strictly
        try:
            data = json.loads(raw)
            # Ensure all sections exist
            result: Dict[str, List[str]] = {}
            for name in self.SECTIONS:
                result[name] = list(data.get(name, []))
            return result
        except Exception as exc:
            print("Failed to parse model JSON response, returning empty mapping.")
            print("Raw response was:\n", raw)
            print("Error:", exc)
            return {name: [] for name in self.SECTIONS}

    # ------------------------------------------------------------------
    # Chunk reconstruction using original content
    # ------------------------------------------------------------------
    def _build_chunks_from_headings(
        self,
        section_to_heading_ids: Dict[str, List[str]],
        headings: List[Dict],
        lines: List[str],
        source_file: str,
    ) -> List[Dict]:
        """
        Build chunk contents from original markdown based on heading assignments.

        Each chunk is a dict:
            - content: full original markdown content for that section
            - metadata: {source_file, length, description}
        """
        # Map HEADING_N -> heading index in headings list
        id_to_heading_idx: Dict[str, int] = {
            f"HEADING_{i}": i for i in range(len(headings))
        }

        chunks: List[Dict] = []

        for section_name in self.SECTIONS:
            heading_ids = section_to_heading_ids.get(section_name, [])

            # Collect line ranges for all headings in this section
            ranges: List[Tuple[int, int]] = []
            for hid in heading_ids:
                if hid not in id_to_heading_idx:
                    continue
                h_idx = id_to_heading_idx[hid]
                start_line = headings[h_idx]["index"]
                if h_idx + 1 < len(headings):
                    end_line = headings[h_idx + 1]["index"]
                else:
                    end_line = len(lines)
                ranges.append((start_line, end_line))

            # Merge ranges and extract content
            merged_ranges: List[Tuple[int, int]] = []
            for start, end in sorted(ranges):
                if not merged_ranges or start > merged_ranges[-1][1]:
                    merged_ranges.append((start, end))
                else:
                    prev_start, prev_end = merged_ranges[-1]
                    merged_ranges[-1] = (prev_start, max(prev_end, end))

            section_lines: List[str] = []
            for start, end in merged_ranges:
                section_lines.extend(lines[start:end])

            content = "\n".join(section_lines).strip()

            chunk = {
                "content": content,
                "metadata": {
                    "source_file": source_file,
                    "length": len(content),
                    "description": section_name,
                },
            }
            chunks.append(chunk)

        return chunks

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chunk_markdown(self, markdown_path: str) -> List[Dict]:
        """
        Chunk a markdown file into the 5 predefined sections.

        Steps:
            1. Read markdown.
            2. Build skeleton with headings + bold lines.
            3. Ask Mistral (via Ollama) to assign headings to sections.
            4. Rebuild chunks from ORIGINAL markdown (no summarising).
        """
        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        source_file = Path(markdown_path).name

        skeleton_text, headings, lines = self._build_skeleton(markdown_content)

        print("Sending skeleton (headings + bold lines) to Mistral for section mapping...")
        section_to_heading_ids = self._ask_model_for_section_headings(skeleton_text)

        chunks = self._build_chunks_from_headings(
            section_to_heading_ids, headings, lines, source_file
        )
        return chunks

    def save_chunks_txt(self, chunks: List[Dict], output_path: str) -> None:
        """
        Save chunks to a .txt file, with sections and original content.

        Format:
            ===== Section Name =====
            <original markdown content>
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks, 1):
                meta = chunk["metadata"]
                content = chunk["content"]

                f.write("=" * 80 + "\n")
                f.write(f"Section {i}: {meta['description']}\n")
                f.write(f"Source file: {meta['source_file']}\n")
                f.write("=" * 80 + "\n\n")

                if content:
                    f.write(content)
                else:
                    f.write("[EMPTY - No content found for this section]")

                f.write("\n\n\n")

        print(f"Chunks saved (txt) to {output_path}")

    def print_chunks(self, chunks: List[Dict]) -> None:
        """Print chunks to the console (for quick inspection)."""
        for i, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            content = chunk["content"]

            print(f"\n{'='*80}")
            print(f"Section {i}: {meta['description']}")
            print(f"Source: {meta['source_file']}")
            print(f"Length: {meta['length']} characters")
            print(f"{'='*80}")
            if content:
                print(content)
            else:
                print("[EMPTY - No content found for this section]")
            print()


def main() -> None:
    """Main entry point for running semantic chunking."""
    import sys

    # Check if Ollama is available
    try:
        models = ollama.list()
        print("Ollama is available!")
        if "models" in models:
            model_names = [m.get("name", "unknown") for m in models["models"]]
            print(f"Available models: {model_names}")
    except Exception as e:  # noqa: BLE001
        print(f"Error connecting to Ollama: {e}")
        print("Please make sure Ollama is installed and running.")
        print("Install from: https://ollama.ai")
        print("Then run: ollama pull mistral")
        return

    # Get input file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "output_folder/Discharge_Summary_Text_and_Tables.md"

    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found.")
        return

    chunker = SemanticChunker(model_name="mistral")

    print(f"\nProcessing: {input_file}")
    print(
        "Preprocessing markdown (headings + bold lines only) and chunking into 5 sections...\n"
    )

    chunks = chunker.chunk_markdown(input_file)

    chunker.print_chunks(chunks)

    output_txt = Path(input_file).stem + "_chunks.txt"
    chunker.save_chunks_txt(chunks, output_txt)

    print(f"\nDone! Results saved to {output_txt}")
    print(f"Total sections: {len(chunks)}")


if __name__ == "__main__":
    main()
