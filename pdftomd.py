import os
import pdfplumber
import re
import unicodedata


def _emphasize_line(line: str) -> str:
    """Add hash markers around label prefixes or all-caps labels."""
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
            return f"{leading}# {label.strip()}: {rest.strip()} #{trailing}"

    # Fallback: all-caps/label-like lines -> wrap whole line
    all_caps_or_label = bool(re.fullmatch(r"[A-Z0-9 .,:/()\-]{4,}", stripped))
    if all_caps_or_label:
        leading = line[: len(line) - len(line.lstrip())]
        trailing = line[len(line.rstrip()) :]
        return f"{leading}# {stripped} #{trailing}"

    return line


def normalize_text(text):
    """
    Normalize text to preserve special characters and symbols.
    Ensures proper Unicode handling and fixes common encoding issues.
    """
    if not text:
        return text
    
    # Normalize Unicode characters (NFC normalization)
    text = unicodedata.normalize('NFC', text)
    
    # Preserve all Unicode characters - don't strip or replace them
    # The text should already be in Unicode from pdfplumber
    return text


def convert_pdf_to_md(pdf_file_path, output_dir='.'):
    """
    Converts a PDF file to Markdown format using pdfplumber.

    Args:
        pdf_file_path (str): The path to the input .pdf file.
        output_dir (str): The directory to save the output .md file.
    """
    os.makedirs(output_dir, exist_ok=True)

    markdown_text = ""
    with pdfplumber.open(pdf_file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            markdown_text += f"## Page {page_num}\n\n"
            
            # Extract text with layout preservation
            # Try different extraction methods to preserve symbols
            # Using layout=True helps preserve formatting and symbols
            text = page.extract_text(layout=True, x_tolerance=1, y_tolerance=3)
            if not text or len(text.strip()) == 0:
                # Fallback to simple extraction without layout
                text = page.extract_text()
            if not text or len(text.strip()) == 0:
                # Last resort: try extracting with words
                words = page.extract_words()
                if words:
                    text = ' '.join(word.get('text', '') for word in words)
            
            if text:
                # Normalize the text to preserve special characters
                text = normalize_text(text)
                for line in text.splitlines():
                    # Normalize each line to preserve symbols
                    normalized_line = normalize_text(line)
                    markdown_text += _emphasize_line(normalized_line) + "\n"
                markdown_text += "\n"
            
            # Extract tables
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    # Normalize table cells to preserve symbols
                    header_row = [normalize_text(str(cell) if cell else "") for cell in table[0]]
                    markdown_text += "| " + " | ".join(header_row) + " |\n"
                    markdown_text += "|" + "|".join(["---"] * len(table[0])) + "|\n"
                    for row in table[1:]:
                        normalized_row = [normalize_text(str(cell) if cell else "") for cell in row]
                        markdown_text += "| " + " | ".join(normalized_row) + " |\n"
                    markdown_text += "\n"

    # Define the output file name
    base_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
    output_file_path = os.path.join(output_dir, f"{base_name}.md")

    # Write the Markdown content to a file with explicit UTF-8 encoding
    # Using errors='strict' to preserve all characters as-is
    with open(output_file_path, 'w', encoding='utf-8', errors='strict', newline='\n') as f:
        f.write(markdown_text)

    print(f"Successfully converted '{pdf_file_path}' to '{output_file_path}'")


if __name__ == "__main__":
    # Example: convert a PDF file named 'document.pdf' to markdown
    convert_pdf_to_md("New LL Acknowledgement (ARYAN).pdf", output_dir="output_folder")
