from pycc.asm import *



def test_func_return():
    fn = mkfunction(mov(eax,0xdeadbeef) + ret())
    fn.restype = ctypes.c_uint64
    assert fn() == 0xdeadbeef

def test_func_args():
    fn = mkfunction(mov(rbx,rsp) + add(rbx,8) + mov(rax,ptr(rax)) + ret(8))
    fn.restype = ctypes.c_uint64
    fn.argtypes = [ctypes.c_uint64]
    assert fn(0xdeadbeef) == 0xdeadbeef
    assert fn(0x123) == 0x123
    
    
    