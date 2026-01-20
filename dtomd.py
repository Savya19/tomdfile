import os
import re
import docx2md

def convert_docx_to_md(docx_file_path, output_dir='.'):
   
    os.makedirs(output_dir, exist_ok=True)

    markdown_text = docx2md.do_convert(docx_file_path, target_dir=output_dir)

    base_name = os.path.splitext(os.path.basename(docx_file_path))[0]
    output_file_path = os.path.join(output_dir, f"{base_name}.md")

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)


if __name__ == "__main__":
    convert_docx_to_md("Random_Patient_Discharge_Summary.docx", output_dir="output_folder")
