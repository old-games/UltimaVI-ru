bits 16

global sub_1c45

global fixmeup0
global fixmeup1
global fixmeup2
global fixmeup3

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0x13ef5 0x13fb1 0x1c45

sub_1c45:
        push    bp
        mov     bp, sp
        sub     sp, byte +0x2
        jmp     loc_1cbe

loc_1c4e:
        cmp     byte [bp-0x1], 0x80
        jnc     loc_1c7c
        cmp     byte [bp-0x1], 0x20
        jnc     loc_1c60
        cmp     byte [bp-0x1], 0xa
        jnz     loc_1c6d

loc_1c60:
        mov     al, [bp-0x1]
        mov     ah, 0x0
        push    ax

fixmeup0: ; far call by absolute direct address
        call    0x464:0x33d3
        jmp     loc_1cb7

loc_1c6d:
        push    ds
        mov     ax, 0x9ed
        push    ax

fixmeup1: ; far call by absolute direct address
        call    0x464:0x3643
        pop     cx
        pop     cx
        jmp     loc_1cf7

loc_1c7c:
        cmp     byte [bp-0x1], 0xef
        jnz     loc_1cad
        cmp     byte [0xe79c], 0x0
        jnz     loc_1ca5
        push    word [bp+0x6]

fixmeup2: ; far call by absolute direct address
        call    0xecb:0x1d01
        jmp     loc_1cb7

loc_1c93:
        les     bx, [0x4d50]
        add     bx, [0xe7ab]
        mov     al, [es:bx]
        mov     [bp-0x1], al
        inc     word [0xe7ab]

loc_1ca5:
        cmp     byte [bp-0x1], 0xee
        jnz     loc_1c93
        jmp     loc_1cb7

loc_1cad:
        push    word [bp-0x1]
        push    word [bp+0x6]

fixmeup3: ; far call by absolute direct address
        call    0xecb:0x153b

loc_1cb7:
        cmp     byte [0x98a], 0x0
        jnz     loc_1cf7

loc_1cbe:
        les     bx, [0x4d50]
        add     bx, [0xe7ab]
        mov     al, [es:bx]
        mov     [bp-0x1], al
        inc     word [0xe7ab]
        cmp     byte [bp-0x1], 0xf7
        jz      loc_1cf7
        cmp     byte [bp-0x1], 0xf0
        jnc     loc_1cf7
        cmp     byte [bp-0x1], 0x0
        jz      loc_1cf7
        cmp     byte [bp-0x1], 0xf9
        jz      loc_1cf7
        cmp     byte [bp-0x1], 0xf8
        jz      loc_1cf7
        cmp     byte [bp-0x1], 0xee
        jz      loc_1cf7
        jmp     loc_1c4e

loc_1cf7:
        dec     word [0xe7ab]
        mov     sp, bp
        pop     bp
        retf    0x2
