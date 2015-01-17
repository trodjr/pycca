# -'- coding: utf-8 -'-

from pytest import raises
from pycc.asm import *
from pycc.asm.pointer import Pointer, rex, pack_int

# Note: when running GNU-as in 32-bit mode, the rxx registers do not exist. 
# This would be fine except that instead of generating an error, the 
# compiler simply treats the unknown name as a null pointer [0x0]. To work 
# around this, we first probe AS to see which registers it doesn't know about,
# then raise an exception when attempting to compile using those registers.
invalid_regs = []
regs = {}
_nullptr = as_code('push [0x0]')
for name,obj in list(globals().items()):
    if isinstance(obj, Register):
        try:
            if as_code('push %s' % obj.name, quiet=True) == _nullptr:
                invalid_regs.append(obj.name)
        except:
            pass
        
        # While we're here, make register groups easier to access:
        regs.setdefault('all', []).append(obj)
        regs.setdefault(obj.bits, []).append(obj)
        if 'mm' not in obj.name:
            # general-purpose registers
            regs.setdefault('gp', []).append(obj)


def itest(instr):
    """Generic instruction test: ensure that output of our function matches
    output of GNU assembler.
    
    *args* must be instruction arguments + assembler code to compare 
    as the last argument.
    """
    asm = str(instr)
    
    def as_code_checkreg(asm):
        # make sure no invalid registers are used; GNU ignores these silently :(
        global invalid_regs
        for reg in invalid_regs:
            if reg in asm:
                exc = Exception("GNU AS unrecognized symbol '%s'" % reg)
                exc.output = ''
                raise exc
        return as_code(asm, quiet=True)
    
    try:
        code1 = instr.code
    except:
        try:
            code2 = as_code_checkreg(asm)
        except:
            return
        print("\n---------\n" + str(instr))
        sys.stdout.write("gnu: ")
        phexbin(code2)
        raise

    try:
        code2 = as_code_checkreg(asm)
    except Exception as err:
        print("\n---------\n" + str(instr))
        sys.stdout.write("py:  ")
        phexbin(code1)
        print(err.output)
        raise
    
    if code1 != code2:
        print("\n---------\n" + asm)
        sys.stdout.write("py:  ")
        phexbin(code1)
        sys.stdout.write("gnu: ")
        phexbin(code2)
        raise Exception("code mismatch.")
    
    
    
    #try:
        #code1 = instr.code
        #err1 = None
    #except TypeError as exc:
        #err1 = exc
        
    #asm = str(instr)
        
    #try:
        ## make sure no invalid registers are used; GNU ignores these silently :(
        #for reg in invalid_regs:
            #if reg in asm:
                #exc = Exception("GNU AS unrecognized symbol '%s'" % reg)
                #exc.output = ''
                #raise exc
        #code2 = as_code(asm, quiet=True)
        #err2 = None
    #except Exception as exc:
        #err2 = exc
        
    #if err1 is None and err2 is None:
        #if code1 == code2:
            #return
        #else:
            #print("\n---------\n" + asm)
            #sys.stdout.write("py:  ")
            #phexbin(code1)
            #sys.stdout.write("gnu: ")
            #phexbin(code2)
            #raise Exception("code mismatch.")
    #elif err1 is not None and err2 is not None:
        #return
    #elif err1 is None:
        #print("\n---------\n" + str(instr))
        #sys.stdout.write("py:  ")
        #phexbin(code1)
        #print("\n" + err2.output)
        #raise err2
    #elif err2 is None:
        #print("\n---------\n" + str(instr))
        #sys.stdout.write("gnu: ")
        #phexbin(code2)
        #raise err1


def addresses(base):
    """Generator yielding various effective address arrangements.
    """
    for offset in regs[base.bits]:
        if offset not in regs['gp']:
            continue
        for disp in [0, 0x1, 0x100, 0x10000]:
            yield [base + disp], '[%s + 0x%x]' % (base.name, disp)
            yield [base + offset + disp], '[%s + %s + 0x%x]' % (base.name, offset.name, disp)
            yield [base + offset*2 + disp], '[%s + %s*2 + 0x%x]' % (base.name, offset.name, disp)
            yield [offset*2 + disp], '[%s*2 + 0x%x]' % (offset.name, disp)
            yield [disp], '[0x%x]' % disp


def test_effective_address():
    # test that register/scale/offset arithmetic works
    assert str(Pointer([eax])) == '[eax]'
    assert str(eax + ebx) == '[eax + ebx]'
    assert str(8*eax + ebx) == '[8*eax + ebx]'
    assert str(ebx + 4*ecx + 0x1000) == '[0x1000 + 4*ecx + ebx]'
    assert str(Pointer([0x1000])) == '[0x1000]'
    assert str(0x1000 + ecx) == '[0x1000 + ecx]'
    assert str(0x1000 + 2*ecx) == '[0x1000 + 2*ecx]'

    # test that we can generate a variety of mod_r/m+sib+disp strings
    itest(mov(edx, dword([eax])))
    itest(mov(edx, dword([ebx + eax])))
    itest(mov(edx, dword([eax*8 + ebx])))
    itest(mov(edx, dword([ebx + 4*ecx + 0x1000])))
    itest(mov(edx, dword([0x1000])))
    itest(mov(edx, dword([0x1000 + ecx])))
    itest(mov(edx, dword([0x1000 + 2*ecx])))

    # test using rbp as the SIB base
    itest(mov(edx, dword([ebp + 4*ecx + 0x1000])))
    
    # test using esp as the SIB offset
    with raises(TypeError):
        (ebx + 4*esp + 0x1000).modrm_sib(edx)
    with raises(TypeError):
        (4*esp + 0x1000).modrm_sib(edx)
    
    # test rex prefix:
    assert Pointer([r8]).modrm_sib(eax)[0] == rex.b


def test_generate_asm():
    # Need to be sure that str(instr) generates accurate strings or else 
    # we may get false positive tests.
    assert str(mov(eax, ebx)) == 'mov eax, ebx'
    ptypes = [
        ('', lambda x: x),
        ('byte ptr ', byte),
        ('word ptr ', word),
        ('dword ptr ', dword),
        ('qword ptr ', qword),
    ]
    for name, fn in ptypes:
        assert str(mov(eax, fn([ebx]))) == 'mov eax, %s[ebx]' % name
        assert str(mov(eax, fn([ebx+eax]))) == 'mov eax, %s[ebx + eax]' % name
        assert str(mov(eax, fn([eax+ebx]))) == 'mov eax, %s[eax + ebx]' % name
        assert str(mov(eax, fn([eax+ebx*4]))) == 'mov eax, %s[4*ebx + eax]' % name
        assert str(mov(eax, fn([eax*4+ebx]))) == 'mov eax, %s[4*eax + ebx]' % name
        assert str(mov(eax, fn([eax*4]))) == 'mov eax, %s[4*eax]' % name
        assert str(mov(eax, fn([0x100+ebx]))) == 'mov eax, %s[0x100 + ebx]' % name
        assert str(mov(eax, fn([0x100+ebx+eax]))) == 'mov eax, %s[0x100 + ebx + eax]' % name
        assert str(mov(eax, fn([0x100+eax+ebx]))) == 'mov eax, %s[0x100 + eax + ebx]' % name
        assert str(mov(eax, fn([0x100+eax+ebx*4]))) == 'mov eax, %s[0x100 + 4*ebx + eax]' % name
        assert str(mov(eax, fn([0x100+eax*4+ebx]))) == 'mov eax, %s[0x100 + 4*eax + ebx]' % name
        assert str(mov(eax, fn([0x100+eax*4]))) == 'mov eax, %s[0x100 + 4*eax]' % name
        assert str(mov(eax, fn([0x100]))) == 'mov eax, %s[0x100]' % name
    assert str(mov(eax, 1)) == 'mov eax, 1'
    assert str(mov(eax, 100)) == 'mov eax, 100'
    assert str(mov(eax, 100000000)) == 'mov eax, 100000000'

    

def test_pack_int():
    assert pack_int(0x10) == b'\x10\x00'
    assert pack_int(0x10, int8=True) == b'\x10'
    assert pack_int(0x10, int16=False) == b'\x10\x00\x00\x00'
    assert pack_int(0x1000) == b'\x00\x10'
    assert pack_int(0x100000) == b'\x00\x00\x10\x00'
    assert pack_int(0x10000000) == b'\x00\x00\x00\x10'
    assert pack_int(0x1000000000) == b'\x00\x00\x00\x00\x10\x00\x00\x00'



# Move instructions

def test_mov():
    itest(mov(eax, 0x1234567))
    itest(mov(eax, ebx))
    itest(mov(rax, 0x1234567891))
    itest(mov(rax, rbx))
    itest(mov(qword([0x12345]), rax))
    # note: these tests fail on 32-bit because GNU prefers a shorthand encoding
    # A3/A1+disp32 but the mode used on 64-bit (89/8B) should work as well. 
    #     itest(mov(dword([0x12345]), ecx))
    #     itest(mov(eax, dword([0x12345])))
    itest(mov(dword([0x12345]), ecx))
    itest(mov(rax, qword([0x12345])))
    itest(mov(ecx, dword([0x12345])))
    itest(mov(rax, qword([rbx])))
    itest(mov(rax, qword([rcx+rbx])))
    itest(mov(rax, qword([8*rbx+rcx])))
    itest(mov(rax, qword([0x1000+8*rbx+rcx])))
    itest(mov(rax, '\xdd'*8))
    itest(mov(qword([0x12345]), '\0'*8))

def test_movsd():
    itest(movsd(xmm1, [rax+rbx*4+0x1000]))
    itest(movsd([rax+rbx*4+0x1000], xmm1))
    itest(movsd(xmm1, qword([eax+ebx*4+0x1000])))
    itest(movsd(qword([eax+ebx*4+0x1000]), xmm1))


# Procedure management instructions

def test_push():
    itest(push(rcx))
    itest(push(ecx))
    itest(push([ecx]))
    itest(push([rcx]))
    itest(push(0x10))
    itest(push(0x10000))
    itest(push(-129))
    itest(push(-128))
    itest(push(-127))
    itest(push(129))
    itest(push(128))
    itest(push(127))

def test_pop():
    itest(pop(ebp))
    itest(pop([ecx]))
    itest(pop(rbp))
    itest(pop([rcx]))

def test_ret():
    itest(ret())
    itest(ret(4))

def test_call():
    # relative calls
    assert call(0x0) == as_code('call .+0x0')
    assert call(-0x1000) == as_code('call .-0x1000')
    code = call('label').code
    assert code.compile({'label': 0x0, 'next_instr_addr': 5}) == as_code('label:\ncall label')
    
    # absolute calls
    itest(call(rax))
    itest(call(eax))


# Arithmetic instructions

def test_add():
    itest( add(rax, rbx) )
    itest( add(rbx, 0x1000) )
    itest( add(dword([0x1000]), eax) )
    itest( add(eax, dword([0x1000])) )
    itest( add(dword([0x1000]), 0x1000) )
    
def test_sub():
    itest( sub(rax, rbx) )
    itest( sub(rbx, 0x1000) )
    itest( sub(dword([0x1000]), eax) )
    itest( sub(eax, dword([0x1000])) )
    #itest( add([0x1000], rax) )
    #itest( add(rax, [0x1000]) )
    itest( sub(dword([0x1000]), 0x1000) )
    
def test_dec():
    itest( dec(dword([0x1000])) )
    itest( dec(eax) )
    itest( dec(rax) )

def test_inc():
    itest( inc(dword([0x1000])) )
    itest( inc(eax) )
    itest( inc(rax) )

def test_imul():
    itest( imul(eax, ebp) )
    
def test_idiv():
    itest( idiv(ebp) )

def test_lea():
    itest( lea(rax, [rbx+rcx*2+0x100]) )
    itest( lea(rax, [ebx+ecx*2+0x100]) )
    itest( lea(eax, [rbx+rcx*2+0x100]) )
    itest( lea(eax, [ebx+ecx*2+0x100]) )

def test_fld():
    itest( fld(dword([rax])) )
    itest( fld(qword([rax+rcx*8])) )
    itest( fld(st(4)) )

def test_fst():
    itest( fst(dword([rax])) )
    itest( fst(qword([rax+rcx*8])) )
    itest( fst(st(4)) )

def test_fstp():
    itest( fstp(dword([rax])) )
    itest( fstp(qword([rax+rcx*8])) )
    itest( fstp(st(4)) )

def test_fild():
    itest( fild(word([rax])) )
    itest( fild(dword([rax])) )
    itest( fild(qword([rax+rcx*8])) )

def test_fist():
    itest( fist(word([rax])) )
    itest( fist(dword([rax])) )

def test_fistp():
    itest( fistp(word([rax])) )
    itest( fistp(dword([rax])) )
    itest( fistp(qword([rax+rcx*8])) )

def test_fabs():
    itest( fabs() )

def test_fadd():
    itest( fadd() )
    itest( fadd(dword([rax])) )
    itest( fadd(qword([rax])) )
    itest( fadd(st(0), st(4)) )
    itest( fadd(st(4), st(0)) )
    
def test_faddp():
    itest( faddp() )
    itest( faddp(st(4), st(0)) )
    
def test_fiadd():
    itest( fiadd(dword([rax])) )
    itest( fiadd(word([rax])) )
    
    
    

# Testing instructions

def test_cmp():
    itest( cmp(dword(0x1000), 0x1000) )
    itest( cmp(rbx, 0x1000) )
    itest( cmp(qword(rbx+0x1000), 0x1000) )

def test_test():
    itest( test(eax, eax) )


# Branching instructions

def test_jmp():
    itest( jmp(rax) )
    assert jmp(0x1000) == as_code('jmp .+0x1000')    

def test_jcc():
    all_jcc = ('a,ae,b,be,c,e,z,g,ge,l,le,na,nae,nb,nbe,nc,ne,ng,nge,nl,nle,'
               'no,np,ns,nz,o,p,pe,po,s').split(',')
    for name in all_jcc:
        name = 'j' + name
        func = globals()[name]
        assert func(0x1000) == as_code('%s .+0x1000' % name)


# OS instructions

def test_syscall():
    itest( syscall() )

def test_int():
    itest( int_(0x80) )
    itest( int_(-129) )
    itest( int_(-128) )
    itest( int_(-127) )
    itest( int_(129) )
    itest( int_(128) )
    itest( int_(127) )



def test_push():
    # can we push immediate values?
    itest(push(0x5))
    
    # Extensive address encoding test
    for reg in regs['gp']:
        # can we push a register?
        itest(push(reg))
        
        # can we push from memory? 
        for py,asm in addresses(reg):
            itest(push(py))
