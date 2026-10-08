import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from PyPDF2 import PdfReader

reader = PdfReader('Hello Farmer.pdf')
with open('hello_farmer_clean.txt', 'w', encoding='utf-8') as f:
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        # Clean up the text - join fragmented words
        lines = text.split('\n')
        cleaned_lines = []
        current_line = ""
        for line in lines:
            stripped = line.strip()
            if stripped == '':
                if current_line:
                    cleaned_lines.append(current_line)
                    current_line = ""
                continue
            if current_line:
                current_line += " " + stripped
            else:
                current_line = stripped
            # If line ends with period, colon, or is a heading, flush it
            if stripped.endswith(('.', ':', '!', '?')) or stripped.startswith(('●', '○', '■', '◆', '-', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                cleaned_lines.append(current_line)
                current_line = ""
        if current_line:
            cleaned_lines.append(current_line)
        
        f.write(f'\n=== PAGE {i+1} ===\n')
        f.write('\n'.join(cleaned_lines))
        f.write('\n')

print(f"Extracted {len(reader.pages)} pages to hello_farmer_clean.txt")
