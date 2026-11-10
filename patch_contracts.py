path = r'c:\Users\saroj\OneDrive\Documents\GitHub\Interactive-ELN\backend\eln_common\contracts.py'
with open(path, 'rb') as f:
    data = f.read()

target = b'status: Literal["active", "archived"]'
replacement = b'status: Literal["active", "archived", "operational"]'

if target in data:
    data = data.replace(target, replacement)
    with open(path, 'wb') as f:
        f.write(data)
    print("SUCCESS: Patched contracts.py")
else:
    print("WARNING: target not found")
