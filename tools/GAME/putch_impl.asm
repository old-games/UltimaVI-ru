bits 16

global sub_2efa
global fixmeup0
global fixmeup1

section CODE

; cat unpacked/GAME.EXE | head -c44830 | tail -c+43835

; TODO: clean up code, move character buffer to proper place

sub_2efa:
        push    bp
        mov     bp, sp
        sub     sp, byte +0x6
        push    si
        push    di
        cmp     word [0x4a5], byte +0x0
        jnz     loc_2f0c
        jmp     loc_32d6

loc_2f0c:
        cmp     word [0x4a9], byte +0x0
        jz      loc_2f32
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x20
        jz      loc_2f32
        cmp     word [bp+0x6], byte +0xa
        jnz     loc_2f26
        jmp     loc_32d6

loc_2f26:
        cmp     word [bp+0x6], byte +0x0
        jl      loc_2f32
        mov     word [0x4a9], 0x0

loc_2f32:
        mov     word [0x2ffe], 0x0
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x4
        jz      loc_2f55
        cmp     byte [0x498], 0x0
        jz      loc_2f55
        push    word [bp+0x6]

fixmeup0: ; far call by absolute direct address
        call    0x2ce6:0x3 ; toupper
        pop     cx
        mov     [bp+0x6], ax

loc_2f55:
        mov     byte [0x498], 0x0
        cmp     word [bp+0x6], byte +0x0
        jnz     loc_2f65
        mov     word [bp+0x6], 0xa

loc_2f65:
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x8
        jz      loc_2f7a
        cmp     word [bp+0x6], byte +0x20
        jng     loc_2f7a
        or      word [bp+0x6], 0x100

loc_2f7a:
        mov     bx, [0x4df]
        mov     al, [bx+0x2]
        cmp     al, [0x57a]
        jz      loc_2f96
        cmp     word [bp+0x6], byte +0xa
        jz      loc_2f96
        cmp     word [bp+0x6], byte +0x0
        jl      loc_2f96
        jmp     loc_3288

loc_2f96:
        cmp     word [0xb729], byte +0x0
        jz      loc_2fb1
        cmp     word [bp+0x6], byte +0x0
        jl      loc_2fb1
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x10
        jz      loc_2fb1
        dec     word [0xb729]

loc_2fb1:
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x10
        jnz     loc_2fbe
        jmp     loc_3058

loc_2fbe:
        cmp     word [0xb729], byte +0x0
        jz      loc_2fc8
        jmp     loc_3058

loc_2fc8:
        cmp     word [bp+0x6], byte +0x0
        jnl     loc_2fd1
        jmp     loc_3058

loc_2fd1:
        mov     al, [bx+0x2]
        shr     al, 1
        mov     ah, 0x0
        add     ax, 0xfffe
        mov     [bp-0x4], ax
        mov     al, [bx+0x3]
        mov     ah, 0x0
        mov     dl, [bx+0x1]
        mov     dh, 0x0
        add     ax, dx
        dec     ax
        mov     [bp-0x2], ax
        mov     word [0x4af], 0x0
        mov     word [0x4d4], 0x1

loc_2ffa:
fixmeup1: ; far call by absolute direct address
        call    0x464:0x2a59 ; getch
        mov     di, ax
        cmp     di, byte +0x20
        jz      loc_3015
        cmp     di, byte +0xd
        jz      loc_3015
        cmp     di, byte +0x1b
        jz      loc_3015
        cmp     di, 0x8f
        jnz     loc_2ffa

loc_3015:
        mov     word [0x4d4], 0x5
        mov     word [0x4af], 0x1
        mov     word [0x2ffe], 0x0
        xor     si, si
        jmp     short loc_3042

loc_302b:
        mov     ax, 0x20
        push    ax
        mov     bx, [0x4df]
        mov     al, [bx]
        mov     ah, 0x0
        add     ax, si
        push    ax
        push    word [bp-0x2]
        call    far [0x4cc]
        inc     si

loc_3042:
        mov     bx, [0x4df]
        mov     al, [bx+0x2]
        mov     ah, 0x0
        cmp     ax, si
        jg      loc_302b
        mov     al, [bx+0x3]
        mov     ah, 0x0
        dec     ax
        mov     [0xb729], ax

loc_3058:
        mov     al, [0x57a]
        mov     ah, 0x0
        mov     [bp-0x6], ax
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x1
        jnz     loc_306d
        jmp     loc_30d5

loc_306d:
        mov     al, [bx+0x2]
        cmp     al, [0x57a]
        jnz     loc_30d5
        cmp     word [bp+0x6], byte +0x0
        jl      loc_30d5
        cmp     word [bp+0x6], byte +0xa
        jnz     loc_3086
        mov     ax, 0x20
        jmp     short loc_3089

loc_3086:
        mov     ax, [bp+0x6]

loc_3089:
        mov     dl, [0x57a]
        mov     dh, 0x0
        mov     bx, dx

        shl     bx, 1
        push    ds
        push    cs
        pop     ds
        mov     [bx+char_buffer], ax ; character
        pop     ds

        shr     bx, 1
        mov     bx, [0x4df]
        mov     al, [bx+0x6]
        mov     dl, [0x57a]
        mov     dh, 0x0
        mov     bx, dx
        mov     [bx+0xb67a], al ; color
        jmp     short loc_30ad

loc_30aa:
        dec     word [bp-0x6]

loc_30ad:
        mov     bx, [bp-0x6]

        shl     bx, 1
        push    ds
        push    cs
        pop     ds
        cmp     word [bx+char_buffer], 0x20 ; character
        pop     ds

        jz      loc_30c7

        push    ds
        push    cs
        pop     ds
        cmp     word [bx+char_buffer-2], 0x2d ; character
        pop     ds

        jz      loc_30c7
        shr     bx, 1
        mov     al, [0x57b]
        mov     ah, 0x0
        cmp     ax, bx
        jl      loc_30aa

loc_30c7:
        cmp     word [bp-0x6], byte +0x0
        jnz     loc_30d5
        mov     al, [0x57a]
        mov     ah, 0x0
        mov     [bp-0x6], ax

loc_30d5:
        mov     bx, [0x4df]
        mov     al, [bx+0x1]
        mov     ah, 0x0
        mov     dl, [bx+0x5]
        mov     dh, 0x0
        add     ax, dx
        mov     [bp-0x2], ax
        test    byte [bx+0x8], 0x2
        jz      loc_3128
        mov     al, [0x57b]
        mov     ah, 0x0
        mov     si, ax
        jmp     short loc_310e

loc_30f7:
        mov     ax, 0x20
        push    ax
        mov     bx, [0x4df]
        mov     al, [bx]
        mov     ah, 0x0
        add     ax, si
        push    ax
        push    word [bp-0x2]
        call    far [0x4cc]
        inc     si

loc_310e:
        mov     bx, [0x4df]
        mov     al, [bx+0x2]
        mov     ah, 0x0
        sub     ax, [bp-0x6]
        sar     ax, 1
        mov     dl, [0x57b]
        mov     dh, 0x0
        add     ax, dx
        cmp     ax, si
        jg      loc_30f7

loc_3128:
        mov     al, [0x57b]
        mov     ah, 0x0
        mov     si, ax
        jmp     short loc_3152

loc_3131:
        mov     al, [si+0xb67a] ; color
        mov     bx, [0x4df]
        mov     [bx+0x6], al

        shl     si, 1
        push    ds
        push    cs
        pop     ds
        mov     ax, [si+char_buffer] ; character
        pop     ds

        shr     si, 1
        push    ax
        mov     al, [bx]
        mov     ah, 0x0
        add     ax, si
        push    ax
        push    word [bp-0x2]
        call    far [0x4cc]
        inc     si

loc_3152:
        cmp     si, [bp-0x6]
        jl      loc_3131
        mov     al, [0x2a56]
        mov     bx, [0x4df]
        mov     [bx+0x6], al
        mov     al, [0x57b]
        mov     ah, 0x0
        cmp     ax, [bp-0x6]
        jnl     loc_3171
        mov     al, [bp-0x6]
        mov     [bx+0x4], al

loc_3171:
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x1
        jz      loc_31da
        mov     al, [bx+0x2]
        cmp     al, [0x57a]
        jnz     loc_31da
        cmp     word [bp+0x6], byte +0x0
        jl      loc_31da
        mov     bx, [bp-0x6]

        shl     bx, 1
        push    ds
        push    cs
        pop     ds
        cmp     word [bx+char_buffer], 0x20 ; character
        pop     ds

        jnz     loc_3197
        inc     word [bp-0x6]

loc_3197:
        mov     si, [bp-0x6]
        jmp     short loc_31b7

loc_319c:
        shl     si, 1
        push    ds
        push    cs
        pop     ds
        mov     ax, [si+char_buffer] ; character
        pop     ds
        shr     si, 1

        mov     bx, si
        sub     bx, [bp-0x6]

        shl     bx, 1
        push    ds
        push    cs
        pop     ds
        mov     [bx+char_buffer], ax ; character
        pop     ds
        shr     bx, 1

        mov     al, [si+0xb67a] ; color
        mov     bx, si
        sub     bx, [bp-0x6]
        mov     [bx+0xb67a], al ; color
        inc     si

loc_31b7:
        mov     al, [0x57a]
        mov     ah, 0x0
        cmp     ax, si
        jnl     loc_319c
        mov     byte [0x57b], 0x0
        mov     ax, si
        sub     al, [bp-0x6]
        mov     [0x57a], al
        cmp     word [bp+0x6], byte +0x20
        jnz     loc_321a
        mov     byte [0x57c], 0x0
        jmp     short loc_321a

loc_31da:
        cmp     word [bp+0x6], byte +0x0
        jl      loc_321a
        mov     al, 0x0
        mov     [0x57b], al
        mov     [0x57a], al
        cmp     word [bp+0x6], byte +0x0
        jl      loc_321a
        cmp     word [bp+0x6], byte +0xa
        jz      loc_321a
        mov     bx, [0x4df]
        mov     al, [bx+0x6]
        mov     dl, [0x57a]
        mov     dh, 0x0
        mov     bx, dx
        mov     [bx+0xb67a], al ; color
        mov     ax, [bp+0x6]
        mov     dl, [0x57a]
        mov     dh, 0x0
        mov     bx, dx

        shl     bx, 1
        push    ds
        push    cs
        pop     ds
        mov     [bx+char_buffer], ax ; character
        pop     ds
        shr     bx, 1

        inc     byte [0x57a]

loc_321a:
        cmp     word [bp+0x6], byte +0x0
        jl      loc_3273
        mov     bx, [0x4df]
        mov     byte [bx+0x4], 0x0
        mov     al, [bx+0x5]
        mov     ah, 0x0
        mov     dl, [bx+0x3]
        mov     dh, 0x0
        dec     dx
        cmp     ax, dx
        jnl     loc_323d
        inc     byte [bx+0x5]
        jmp     loc_32c5

loc_323d:
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x20
        jnz     loc_324a
        jmp     loc_32c5

loc_324a:
        mov     word [0x2ffe], 0x1
        mov     al, [bx]
        mov     ah, 0x0
        push    ax
        mov     al, [bx+0x1]
        mov     ah, 0x0
        push    ax
        mov     al, [bx+0x2]
        mov     ah, 0x0
        push    ax
        mov     al, [bx+0x3]
        mov     ah, 0x0
        push    ax
        call    far [0x4d0]
        mov     word [0x2ffe], 0x0
        jmp     short loc_32c5

loc_3273:
        mov     bx, [0x4df]
        mov     al, [bx+0x4]
        mov     [0x57a], al
        mov     [0x57b], al
        mov     word [0x4a3], 0x0
        jmp     short loc_32c5

loc_3288:
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x1
        jz      loc_329f
        cmp     word [bp+0x6], byte +0x20
        jnz     loc_329f
        cmp     byte [0x57c], 0x0
        jz      loc_32c5

loc_329f:
        mov     bx, [0x4df]
        mov     al, [bx+0x6]
        mov     dl, [0x57a]
        mov     dh, 0x0
        mov     bx, dx
        mov     [bx+0xb67a], al ; color
        mov     ax, [bp+0x6]
        mov     dl, [0x57a]
        mov     dh, 0x0
        mov     bx, dx

        shl     bx, 1
        push    ds
        push    cs
        pop     ds
        mov     [bx+char_buffer], ax ; character
        pop     ds
        shr     bx, 1

        inc     byte [0x57a]

loc_32c5:
        cmp     word [bp+0x6], byte +0x20
        jz      loc_32d0
        mov     byte [0x57c], 0x1

loc_32d0:
        mov     word [0x2ffe], 0x1

loc_32d6:
        pop     di
        pop     si
        mov     sp, bp
        pop     bp
        retf    0x2

char_buffer: times 0x29 dw 0
