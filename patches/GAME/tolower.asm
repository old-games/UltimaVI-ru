bits 16

global sub_0002

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0x30432 0x30463 0x2

sub_0002:
        push    bp
        mov     bp, sp
        cmp     word [bp+0x6], byte -0x1
        jnz     loc_0010
        mov     ax, 0xffff
        jmp     loc_0031

loc_0010:
        mov     al, [bp+0x6]
        mov     ah, 0x0
        mov     bx, ax
        test    byte [bx+0x3117], 0x4
        jz      loc_002a
        mov     al, [bp+0x6]
        mov     ah, 0x0
        add     ax, 0x20
        jmp     loc_0031
        jmp     loc_0031

loc_002a:
        mov     al, [bp+0x6]
        mov     ah, 0x0
        jmp     loc_0031

loc_0031:
        pop     bp
        retf
