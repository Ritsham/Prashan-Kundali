import glob
import os

for ext in ('*.html', '*.css'):
    for f in glob.glob(ext):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace hardcoded whites with dark indigo except for bg-surface
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if '--bg-surface: #FFFFFF;' in line:
                new_lines.append(line)
            else:
                l = line.replace('color: #ffffff', 'color: var(--ink-deep-soft)')
                l = l.replace('color: #fff', 'color: var(--ink-deep-soft)')
                l = l.replace('color: #fdf9f2', 'color: var(--ink-deep-soft)')
                l = l.replace('color:#fff', 'color: var(--ink-deep-soft)')
                l = l.replace('color:#ffffff', 'color: var(--ink-deep-soft)')
                
                # Fix shadows for light mode
                l = l.replace('rgba(0, 0, 0, 0.2)', 'rgba(46, 43, 95, 0.08)')
                l = l.replace('rgba(0,0,0,0.2)', 'rgba(46, 43, 95, 0.08)')
                l = l.replace('rgba(0, 0, 0, 0.3)', 'rgba(46, 43, 95, 0.12)')
                l = l.replace('rgba(0, 0, 0, 0.5)', 'rgba(46, 43, 95, 0.15)')
                
                new_lines.append(l)
                
        new_content = '\n'.join(new_lines)
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
