import glob
import os

for ext in ('*.html', '*.css'):
    for f in glob.glob(ext):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        new_content = content.replace("'Cinzel', sans-serif", "'Cinzel', serif")
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
