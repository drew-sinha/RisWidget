import cffi
import re

import pathlib
hist_src = pathlib.Path(__file__).parent / '_histogram_src.c'

with hist_src.open() as f:
    hist_source = f.read()
hist_def = re.compile(r'^void.+?\)', flags=re.MULTILINE|re.DOTALL)
hist_headers = '\n'.join(h + ';' for h in hist_def.findall(hist_source))

ffi = cffi.FFI()

ffi.set_source("_histogram", hist_source)
ffi.cdef(hist_headers)

if __name__ == "__main__":
    ffi.compile()