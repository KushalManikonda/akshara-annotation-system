import zipfile
from tempfile import SpooledTemporaryFile

class FileWrapper:
    def __init__(self, file, name):
        self._file = file
        self.name = name
    def seekable(self): return True
    def readable(self): return True
    def writable(self): return False
    def __getattr__(self, item):
        return getattr(self._file, item)

with open('test2.zip', 'wb') as f:
    f.write(b'PK\x05\x06' + b'\x00'*18) # empty zip

f = SpooledTemporaryFile()
with open('test2.zip', 'rb') as zf:
    f.write(zf.read())
f.seek(0)

wrapped = FileWrapper(f, 'test2.zip')
try:
    with zipfile.ZipFile(wrapped, 'r') as z:
        print('Success!')
except Exception as e:
    print('Error:', e)
