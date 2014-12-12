from pytest import raises
from pycc.asm import *
    
regs = {}
for name,obj in globals().items():
    if isinstance(obj, Register):
        regs.setdefault('all', []).append(obj)
        regs.setdefault(obj.bits, []).append(obj)
        if 'mm' not in obj.name:
            # general-purpose registers
            regs.setdefault('gp', []).append(obj)

def test(instr, *args):
    """Generic instruction test: ensure that output of our function matches
    output of GNU assembler.
    
    *args* must be instruction arguments + assembler code to compare 
    as the last argument.
    """
    asm = args[-1]
    args = args[:-1]
    
    try:
        code1 = instr(*args)
    except TypeError as exc:
        # Only pass if assembler also generates error
        try:
            code2 = as_code(asm)
            raise exc
        except Exception:
            return

    code2 = as_code(asm)
    assert code1 == code2

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
            yield [disp], '[0x%x]' % disp


#def test_effective_address():
    ## test that register/scale/offset arithmetic works
    #assert repr(interpret([rax])) == '[rax]'
    #assert repr(rax + rbx) == '[rbx + rax]'
    #assert repr(8*rax + rbx) == '[8*rax + rbx]'
    #assert repr(rbx + 4*rcx + 0x1000) == '[0x1000 + 4*rcx + rbx]'
    #assert repr(interpret([0x1000])) == '[0x1000]'
    #assert repr(0x1000 + rcx) == '[0x1000 + rcx]'
    #assert repr(0x1000 + 2*rcx) == '[0x1000 + 2*rcx]'

    ## test that we can generate a variety of mod_r/m+sib+disp strings
    #assert (interpret([rax])).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [rax]')[2:]
    #assert (rbx + rax).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [rax + rbx]')[2:]
    #assert (8*rax + rbx).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [rax*8 + rbx]')[2:]
    #assert (rbx + 4*rcx + 0x1000).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [rbx + 4*rcx + 0x1000]')[2:]
    #assert (interpret([0x1000])).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [0x1000]')[2:]
    #assert (0x1000 + rcx).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [0x1000 + rcx]')[2:]
    #assert (0x1000 + 2*rcx).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [0x1000 + 2*rcx]')[2:]

    ## test using rbp as the SIB base
    #assert (rbp + 4*rcx + 0x1000).modrm_sib(rdx)[1] == as_code('mov rdx, qword ptr [rbp + 4*rcx + 0x1000]')[2:]
    
    ## test using esp as the SIB offset
    #with raises(TypeError):
        #(rbx + 4*esp + 0x1000).modrm_sib(rdx)
    #with raises(TypeError):
        #(4*esp + 0x1000).modrm_sib(rdx)
    
    ## test rex prefix:
    #assert interpret([r8]).modrm_sib(rax)[0] == rex.b
    

def test_pack_int():
    assert pack_int(0x10) == '\x10\x00'
    assert pack_int(0x10, int8=True) == '\x10'
    assert pack_int(0x10, int16=False) == '\x10\x00\x00\x00'
    assert pack_int(0x1000) == '\x00\x10'
    assert pack_int(0x100000) == '\x00\x00\x10\x00'
    assert pack_int(0x10000000) == '\x00\x00\x00\x10'
    assert pack_int(0x1000000000) == '\x00\x00\x00\x00\x10\x00\x00\x00'



# Move instructions

#def test_mov():
    #assert mov(eax, 0x1234567) == as_code('mov eax,0x1234567')
    #assert mov(eax, ebx) == as_code('mov eax,ebx')
    #assert mov(rax, 0x1234567891) == as_code('mov rax,0x1234567891')
    #assert mov(rax, rbx) == as_code('mov rax,rbx')
    #assert mov([0x12345], rax) == as_code('mov qword ptr [0x12345], rax')
    #assert mov([0x12345], eax) == as_code('mov dword ptr [0x12345], eax')
    #assert mov(rax, [0x12345]) == as_code('mov rax, qword ptr [0x12345]')
    #assert mov(eax, [0x12345]) == as_code('mov eax, dword ptr [0x12345]')
    #assert mov(rax, [rbx]) == as_code('mov rax, qword ptr [rbx]')
    #assert mov(rax, [rcx+rbx]) == as_code('mov rax, qword ptr [rbx+rcx]')
    #assert mov(rax, [8*rbx+rcx]) == as_code('mov rax, qword ptr [8*rbx+rcx]')
    #assert mov(rax, [0x1000+8*rbx+rcx]) == as_code('mov rax, qword ptr 0x1000[8*rbx+rcx]')
    
#def test_movsd():
    #assert movsd(xmm1, [rax+rbx*4+0x1000]) == as_code('movsd xmm1, qword ptr [rax+rbx*4+0x1000]')
    #assert movsd([rax+rbx*4+0x1000], xmm1) == as_code('movsd qword ptr [rax+rbx*4+0x1000], xmm1')


# Procedure management instructions

def test_push():
    for reg in regs['gp']:
        # can we push a register?
        test(push, reg, 'push %s' % reg.name)
        
        # can we push immediate values?
        test(push, reg, 'push %s' % reg.name)        
        
        # can we push from memory? 
        for py,asm in addresses(reg):
            test(push, py, 'push '+asm)
        #test(push, [reg], 'push [%s]' % reg.name)
        #test(push, [reg+0x1], 'push [%s+0x1]' % reg.name)
        #test(push, [reg+0x100], 'push [%s+0x100]' % reg.name)
        #test(push, [reg+0x10000], 'push [%s+0x10000]' % reg.name)
        #test(push, [reg+rax*2+0x1], 'push [%s+rax*2+0x1]' % reg.name)
        #test(push, [reg+rax*2+0x100], 'push [%s+rax*2+0x100]' % reg.name)
        #test(push, [reg+rax*2+0x10000], 'push [%s+rax*2+0x10000]' % reg.name)
        #test(push, [reg+rax*2], 'push [%s+rax*2]' % reg.name)
        #test(push, [0x1], 'push [0x1]' % reg.name)
        #test(push, [0x100], 'push [0x100]' % reg.name)
        #test(push, [0x10000], 'push [0x10000]' % reg.name)
        
        #assert push(reg) == as_code('push %s' % reg.name)
        #assert push(reg+0x1000) == as_code('push %s+0x1000' % reg.name)
        
    assert push(rbp) == as_code('pushq rbp')
    #assert push(rax) == as_code('push rax')

def test_pop():
    assert pop(rbp) == as_code('popq rbp')
    #assert pop(rax) == as_code('pop rax')

def test_ret():
    assert ret() == as_code('ret')
    #assert ret(4) == as_code('ret 4')

def test_call():
    # relative calls
    assert call(0x0) == as_code('call .+0x0') #'\xe8\x00\x10\x00\x00'  # how to specify these in
    assert call(-0x1000) == as_code('call .-0x1000') #'\xe8\x00\xf0\xff\xff' # assembler??
    # absolute calls
    assert call(rax) == as_code('call rax')


# Arithmetic instructions

def test_add():
    assert add(rax, rbx) == as_code('add rax, rbx')
    assert add(rbx, 0x1000) == as_code('add rbx, 0x1000')
    assert add([0x1000], eax) == as_code('add dword ptr [0x1000], eax')
    assert add(eax, [0x1000]) == as_code('add eax, dword ptr [0x1000]')
    #assert add([0x1000], rax) == as_code('add qword ptr [0x1000], rax')
    #assert add(rax, [0x1000]) == as_code('add rax, qword ptr [0x1000]')
    assert add([0x1000], 0x1000) == as_code('add dword ptr [0x1000], 0x1000')
    
def test_dec():
    assert dec([0x1000]) == as_code('dec dword ptr [0x1000]')
    assert dec(eax) == as_code('dec eax')
    assert dec(rax) == as_code('dec rax')

def test_inc():
    assert inc([0x1000]) == as_code('inc dword ptr [0x1000]')
    assert inc(eax) == as_code('inc eax')
    assert inc(rax) == as_code('inc rax')

def test_imul():
    assert imul(eax, ebp) == as_code('imul eax, ebp')
    
def test_idiv():
    assert idiv(ebp) == as_code('idiv ebp')

def test_lea():
    assert lea(rax, [rbx+rcx*2+0x100]) == as_code('lea rax, [rbx+rcx*2+0x100]')
    assert lea(rax, [ebx+ecx*2+0x100]) == as_code('lea rax, [ebx+ecx*2+0x100]')
    assert lea(eax, [rbx+rcx*2+0x100]) == as_code('lea eax, [rbx+rcx*2+0x100]')
    assert lea(eax, [ebx+ecx*2+0x100]) == as_code('lea eax, [ebx+ecx*2+0x100]')


# Testing instructions

def test_cmp():
    assert cmp(dword(0x1000), 0x1000) == as_code('cmp dword ptr [0x1000], 0x1000')
    assert cmp(rbx, 0x1000) == as_code('cmp rbx, 0x1000')
    assert cmp(qword(rbx+0x1000), 0x1000) == as_code('cmp qword ptr [rbx+0x1000], 0x1000')

def test_test():
    assert test(eax, eax) == as_code('test eax,eax')


# Branching instructions

def test_jmp():
    assert jmp(rax) == as_code('jmp rax')
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
    assert syscall() == as_code('syscall')

def test_int():
    assert int_(0x80) == as_code('int 0x80')

