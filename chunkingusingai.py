"""
Semantic Chunking of Markdown Files using Ollama AI

This script chunks medical markdown documents into 5 predefined sections using AI:
1. Demographics
2. Condition at the start of treatment/vital parameters
3. Diagnosis
4. Condition at the end of the treatment/vital parameters
5. Physician outcomes/Outcome scales

Usage:
    python chunkingusingai.py [path_to_markdown_file]

Requirements:
    1. Install Ollama from https://ollama.ai
    2. Pull a model: ollama pull llama3.2 (or llama2, mistral, etc.)
    3. Install Python package: pip install ollama

The script will:
    - Use AI to directly extract the 5 sections from the markdown
    - Output chunks as a list of dictionaries with content and metadata
    - Leave sections empty if no matching content is found
"""

import json
import ollama
from typing import List, Dict
from pathlib import Path


class SemanticChunker:
    """
    Semantic chunking of markdown files into 5 predefined sections using Ollama AI.
    Uses AI directly without section matching - pure semantic extraction.
    """
    
    # Define the target sections
    SECTIONS = [
        "Demographics",
        "Condition at the start of treatment/vital parameters",
        "Diagnosis",
        "Condition at the end of the treatment/vital parameters",
        "Physician outcomes/Outcome scales"
    ]
    
    def __init__(self, model_name: str = "llama3.2"):
        """
        Initialize the chunker with an Ollama model.
        
        Args:
            model_name: Name of the Ollama model to use (default: llama3.2)
        """
        self.model_name = model_name
    
    def extract_section_with_ai(self, markdown_content: str, section_name: str) -> str:
        """
        Use AI to extract a specific section from the markdown content.
        
        Args:
            markdown_content: The full markdown content
            section_name: The name of the section to extract
            
        Returns:
            Extracted content for the section, or empty string if not found
        """
        # Special handling for Demographics - it's everything from start until condition at start
        if section_name == "Demographics":
            prompt = f"""You are analyzing a medical document in markdown format. Extract the Demographics section.

IMPORTANT: The Demographics section is NOT explicitly labeled. It consists of ALL content from the very beginning of the document until the "Condition at the start of treatment" or "vital parameters" section begins.

The Demographics section typically contains:
- Patient details like age, gender, hospital ID
- Admission date, discharge date
- Ward, bed number
- Any personal information or identification details
- Any content that appears at the start of the document before treatment/condition information

Medical Document:
{markdown_content}

Instructions:
1. Extract ALL content from the beginning of the document
2. Stop when you encounter content related to "condition at start", "initial condition", "presenting symptoms", "chief complaint", "vital parameters", or "vital signs"
3. Include all headings and content from the start until that point
4. Preserve the markdown formatting
5. If the document starts directly with condition/treatment information (no demographics), respond with exactly: "NO_CONTENT"
6. Be thorough - include everything from the document start

Extracted Demographics content:"""
        else:
            prompt = f"""You are analyzing a medical document in markdown format. Extract ONLY the content that belongs to the following section:

Section: "{section_name}"

This section should contain:
- For "Condition at the start of treatment/vital parameters": Initial condition, presenting symptoms, chief complaint, vital signs at admission, baseline parameters, condition on admission
- For "Diagnosis": Primary diagnosis, secondary diagnosis, differential diagnosis, any diagnostic information
- For "Condition at the end of the treatment/vital parameters": Final condition, discharge condition, vital signs at discharge, post-treatment parameters, condition at discharge
- For "Physician outcomes/Outcome scales": Clinical outcomes, physician notes, outcome scales, prognosis, follow-up information, treatment results, discharging doctor's note

Medical Document:
{markdown_content}

Instructions:
1. Find and extract ALL content related to "{section_name}"
2. Include relevant headings and their content
3. Preserve the markdown formatting
4. If no content exists for this section, respond with exactly: "NO_CONTENT"
5. Do not include content from other sections
6. Be thorough - look for similar terms and related information

Extracted content for "{section_name}":"""

        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.2,  # Low temperature for more deterministic results
                }
            )
            
            extracted = response.get('response', '').strip()
            
            # Check if AI returned no content
            if extracted.upper() == "NO_CONTENT" or not extracted or len(extracted) < 10:
                return ""
            
            return extracted
            
        except Exception as e:
            print(f"Error extracting section '{section_name}': {e}")
            return ""
    
    def chunk_markdown(self, markdown_path: str) -> List[Dict]:
        """
        Chunk a markdown file into the 5 predefined sections using AI.
        
        Args:
            markdown_path: Path to the markdown file
            
        Returns:
            List of dictionaries, each with 'content' and 'metadata' keys
        """
        # Read markdown file
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Get source file name
        source_file = Path(markdown_path).name
        
        # Initialize result list
        chunks = []
        
        # Extract each section using AI
        for section_name in self.SECTIONS:
            print(f"Extracting: {section_name}...")
            content = self.extract_section_with_ai(markdown_content, section_name)
            
            # Create chunk dictionary
            chunk = {
                "content": content,
                "metadata": {
                    "source_file": source_file,
                    "length": len(content),
                    "description": section_name
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def save_chunks(self, chunks: List[Dict], output_path: str):
        """
        Save chunks to a JSON file.
        
        Args:
            chunks: List of chunk dictionaries
            output_path: Path to save the output JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        print(f"\nChunks saved to {output_path}")
    
    def print_chunks(self, chunks: List[Dict]):
        """
        Print chunks in a readable format.
        
        Args:
            chunks: List of chunk dictionaries
        """
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk['metadata']
            content = chunk['content']
            
            print(f"\n{'='*80}")
            print(f"Chunk {i}: {metadata['description']}")
            print(f"Source: {metadata['source_file']}")
            print(f"Length: {metadata['length']} characters")
            print(f"{'='*80}")
            if content:
                print(content)
            else:
                print("[EMPTY - No content found for this section]")
            print()


def main():
    """
    Main function to run the semantic chunking.
    """
    import sys
    
    # Check if Ollama is available
    try:
        # Test Ollama connection by trying to list models
        models = ollama.list()
        print("Ollama is available!")
        if 'models' in models:
            model_names = [m.get('name', 'unknown') for m in models['models']]
            print(f"Available models: {model_names}")
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        print("Please make sure Ollama is installed and running.")
        print("Install from: https://ollama.ai")
        print("Then run: ollama pull llama3.2")
        return
    
    # Get input file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Default to the markdown file in output_folder
        input_file = "output_folder/Discharge_Summary_Text_and_Tables.md"
    
    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found.")
        return
    
    # Initialize chunker
    chunker = SemanticChunker(model_name="llama3.2")
    
    print(f"\nProcessing: {input_file}")
    print("Chunking markdown into 5 sections using AI semantic extraction...\n")
    
    # Chunk the markdown
    chunks = chunker.chunk_markdown(input_file)
    
    # Print results
    chunker.print_chunks(chunks)
    
    # Save to JSON
    output_file = Path(input_file).stem + "_chunks.json"
    chunker.save_chunks(chunks, output_file)
    
    print(f"\nDone! Results saved to {output_file}")
    print(f"Total chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
