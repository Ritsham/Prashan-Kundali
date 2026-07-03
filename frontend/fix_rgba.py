import glob
import os

for ext in ('*.html', '*.css'):
    for f in glob.glob(ext):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        new_content = content.replace("rgba(255, 255, 255,", "rgba(46, 43, 95,")
        new_content = new_content.replace("rgba(255,255,255,", "rgba(46,43,95,")
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
