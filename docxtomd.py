import os
import re
import docx2md


def _wrap_hash_markers(markdown: str) -> str:
    """Wrap bold spans and label prefixes with hash markers."""

    # Convert bold markdown **text** to # text #
    markdown = re.sub(r"\*\*([^*]+)\*\*", r"# \1 #", markdown)

    def wrap_line(line: str) -> str:
        stripped = line.strip()
        if not stripped or "http" in stripped.lower():
            return line

        # If line has a colon, wrap whole line as label: value (avoid times like 9:57)
        if ":" in stripped:
            if re.fullmatch(r".*\b\d{1,2}:\d{2}\b.*", stripped):
                return line
            label, rest = stripped.split(":", 1)
            if label and len(label) <= 80:
                leading = line[: len(line) - len(line.lstrip())]
                trailing = line[len(line.rstrip()) :]
                wrapped = f"{leading}# {label.strip()}: {rest.strip()} #{trailing}"
                return wrapped

        # Fallback: all-caps/label-like lines -> wrap whole line
        all_caps_or_label = bool(re.fullmatch(r"[A-Z0-9 .,:/()\-]{4,}", stripped))
        if all_caps_or_label:
            leading = line[: len(line) - len(line.lstrip())]
            trailing = line[len(line.rstrip()) :]
            return f"{leading}# {stripped} #{trailing}"

        return line

    processed_lines = [wrap_line(line) for line in markdown.splitlines()]
    return "\n".join(processed_lines)


def convert_docx_to_md(docx_file_path, output_dir='.'):
    """
    Converts a DOCX file to Markdown format.

    Args:
        docx_file_path (str): The path to the input .docx file.
        output_dir (str): The directory to save the output .md file and images.
    """
    os.makedirs(output_dir, exist_ok=True)

    markdown_text = docx2md.do_convert(docx_file_path, target_dir=output_dir)

    # Post-process to add hash markers
    markdown_text = _wrap_hash_markers(markdown_text)

    base_name = os.path.splitext(os.path.basename(docx_file_path))[0]
    output_file_path = os.path.join(output_dir, f"{base_name}.md")

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)

    print(f"Successfully converted '{docx_file_path}' to '{output_file_path}'")


if __name__ == "__main__":
    convert_docx_to_md("Random_Patient_Discharge_Summary.docx", output_dir="output_folder")
