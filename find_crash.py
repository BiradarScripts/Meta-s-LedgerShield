import os

for root, _, files in os.walk('.'):
    p = str(root)
    if '\\.git' in p or '/.git' in p or '\\venv' in p or '/venv' in p or '__pycache__' in p:
        continue
    for f in files:
        if f == 'find_crash.py': continue
        path = os.path.join(root, f)
        try:
            with open(path, 'r', encoding='cp1252') as file:
                file.read()
        except UnicodeDecodeError as e:
            print(f'Cannot decode: {path} with cp1252')
