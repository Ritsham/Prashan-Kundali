import os

directory = r'c:\Users\gyanr\Desktop\Kundli\Prashan-Kundali\frontend'
replacements = {
    "'Outfit', sans-serif": "'Inter', sans-serif",
    "'Cinzel', serif": "'Space Grotesk', sans-serif",
    "ui-sans-serif, system-ui, -apple-system, sans-serif": "sans-serif"
}

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('.css') or file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Updated {file}')
