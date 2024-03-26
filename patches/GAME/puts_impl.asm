bits 16

global sub_32f8
global fixmeup0

section CODE

; cat unpacked/GAME.EXE | head -c44890 | tail -c+44857

sub_32f8:
        push    bp
        mov     bp, sp
        jmp     loc_330d

loc_32fd:
        les     bx, [bp+0x6]
        inc     word [bp+0x6]
        mov     al, [es:bx]
        mov     ah, 0x0
        push    ax

fixmeup0: ; far call by absolute direct address
        call    0x464:0x2efa ; putch_impl

loc_330d:
        les     bx, [bp+0x6]
        cmp     byte [es:bx], 0x0
        jnz     loc_32fd
        pop     bp
        retf    0x4
