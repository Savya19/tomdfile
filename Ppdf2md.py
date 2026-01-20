import pymupdf4llm
import pathlib
import os

md_text = pymupdf4llm.to_markdown("Discharge_Summary_Text_and_Tables.pdf")

output_dir = "output_folder"
os.makedirs(output_dir, exist_ok=True)

pathlib.Path("output_folder/output.md").write_bytes(md_text.encode())
