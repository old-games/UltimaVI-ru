bits 16

global sub_0003

section CODE

; cat ../unpacked/GAME.EXE | head -c197780 | tail -c+197732

sub_0003:
        push    bp
        mov     bp, sp
        cmp     word [bp+0x6], byte -0x1
        jnz     loc_11
        mov     ax, 0xffff
        jmp     short loc_32

loc_11:
        mov     al, [bp+0x6]
        mov     ah, 0x0
        mov     bx, ax
        test    byte [bx+0x3117], 0x8
        jz      loc_2b
        mov     al, [bp+0x6]
        mov     ah, 0x0
        add     ax, 0xffe0
        jmp     short loc_32
        jmp     short loc_32

loc_2b:
        mov     al, [bp+0x6]
        mov     ah, 0x0
        jmp     short loc_32

loc_32:
        pop bp
        retf
