import os

for root, _, files in os.walk('.'):
    # skip venv, __pycache__, .git
    if '.git' in root or '__pycache__' in root or 'venv' in root:
        continue
    for f in files:
        if f == 'find_codec.py':
            continue
        path = os.path.join(root, f)
        try:
            with open(path, 'r', encoding='charmap') as file:
                file.read()
        except UnicodeDecodeError as e:
            print(f'Cannot decode: {path} with charmap')
        try:
            with open(path, 'r') as file:
                file.read()
        except UnicodeDecodeError as e:
            print(f'Cannot decode: {path} with default encoding ({e})')
