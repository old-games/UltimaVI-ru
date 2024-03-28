bits 16

global sub_2d3a

global fixmeup0
global fixmeup1
global fixmeup2
global fixmeup3
global fixmeup4

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0xa97a 0xaa49 0x2d3a

sub_2d3a:
        push    bp
        mov     bp, sp
        sub     sp, byte +0x2
        push    si
        push    di
        mov     byte [0x49b], 0x1
        mov     word [0x4b1], 0x0
        mov     ax, 0xffff
        push    ax

fixmeup0: ; far call by absolute direct address
        call    0x464:0x2efa
        xor     di, di
        mov     si, di
        mov     [0x4ab], si
        jmp     loc_2ddb

loc_2d61:
fixmeup1: ; far call by absolute direct address
        call    0x464:0x0e6e
        mov     [bp-0x2], ax
        or      ax, ax
        jz      loc_2d61
        cmp     ax, 0xd
        jz      loc_2d7d
        cmp     ax, 0x1b
        jz      loc_2d8b
        cmp     ax, 0x10e
        jz      loc_2dab
        jmp     loc_2dba

loc_2d7d:
        mov     bx, [bp+0x8]
        mov     byte [bx+si], 0x0
        mov     word [0x4ad], 0x0
        jmp     loc_2da8

loc_2d8b:
        mov     bx, [bp+0x8]
        mov     byte [bx], 0x0
        jmp     loc_2d9b

loc_2d93:
        mov     ax, 0x8
        push    ax

fixmeup2: ; far call by absolute direct address
        call    0x464:0x0f52

loc_2d9b:
        mov     ax, si
        dec     si
        or      ax, ax
        jnz     loc_2d93
        mov     word [0x4ad], 0x1

loc_2da8:
        inc     di
        jmp     loc_2ddb

loc_2dab:
        or      si, si
        jz      loc_2ddb
        dec     si
        mov     ax, 0x8
        push    ax

fixmeup3: ; far call by absolute direct address
        call    0x464:0x0f52
        jmp     loc_2ddb

loc_2dba:
        cmp     si, [bp+0x6]
        jnl     loc_2ddb
        cmp     word [bp-0x2], byte +0x20
        jl      loc_2ddb
        cmp     word [bp-0x2], byte +0x7e
        jg      loc_2ddb
        mov     al, [bp-0x2]
        mov     bx, [bp+0x8]
        mov     [bx+si], al
        inc     si
        push    word [bp-0x2]

fixmeup4: ; far call by absolute direct address
        call    0x464:0x0f52

loc_2ddb:
        or      di, di
        jnz     loc_2de2
        jmp     loc_2d61

loc_2de2:
        mov     word [0x4ab], 0x1
        mov     bx, [0x4df]
        mov     al, [bx+0x3]
        mov     ah, 0x0
        mov     [0xb729], ax
        mov     word [0x4b1], 0x1
        mov     byte [0x49b], 0x0
        mov     ax, si
        pop     di
        pop     si
        mov     sp, bp
        pop     bp
        retf    0x4
