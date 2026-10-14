import hashlib

def iter_blocks(file_obj, block_size=4*1024*1024):
    if type(block_size) is not int or block_size<1:raise ValueError("positive block size required")
    position=0
    while True:
        data=file_obj.read(block_size)
        if not data:break
        yield position,hashlib.sha256(data).hexdigest(),data
        position+=1
