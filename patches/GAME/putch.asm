bits 16

global sub_33d3

global fixmeup0
global fixmeup1
global fixmeup2

global fixmeup5
global fixmeup6
global fixmeup7
global fixmeup8
global fixmeup9
global fixmeupA
global fixmeupB
global fixmeupC
global fixmeupD

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0xb013 0xb261 0x33d3

sub_33d3:
        push    bp
        mov     bp, sp
        sub     sp, byte +0x8
        push    si
        cmp     word [0x4a5], byte +0x0
        jnz     loc_33e4
        jmp     loc_361a

loc_33e4:
        cmp     word [bp+0x6], byte +0x26
        jz      loc_33fb
        cmp     word [0x4a3], byte +0x0
        jz      loc_33fb
        cmp     word [0x2ca8], byte +0x0
        jnz     loc_33fb
        jmp     loc_361a

loc_33fb:
        mov     ax, [bp+0x6]
        mov     cx, 0x0c
        mov     bx, switch_table_1

switch_loop_1:
        cmp     ax, [cs:bx]
        jz      loc_3410
        inc     bx
        inc     bx
        loop    switch_loop_1
        jmp     loc_3494

loc_3410:
        jmp     [cs:bx+0x0c*2]

switch_table_1:
        dw      0x23
        dw      0x24
        dw      0x25
        dw      0x26
        dw      0x2a
        dw      0x2f
        dw      0x3c
        dw      0x3e
        dw      0x40
        dw      0x5c
        dw      0x5e
        dw      0x60

jpt_17A50:
        dw      loc_17A84
        dw      loc_17A84
        dw      loc_17A84
        dw      loc_17AA8
        dw      loc_17A8D
        dw      loc_17A84
        dw      loc_17AB6
        dw      loc_17AC1
        dw      loc_17A84
        dw      loc_17A84
        dw      loc_17A84
        dw      loc_17ACC

loc_17A84:
        mov     al, [bp+6]
        mov     [0x57d], al
        jmp     loc_361a

loc_17A8D:
        mov     ax, 0xffff
        push    ax

fixmeup5: ; far call by absolute direct address
        call    0x464:0x2efa ; putch_impl
        mov     word [0x4d4], 0x1

fixmeup6: ; far call by absolute direct address
        call    0x464:0x2a59 ; getch
        mov     word [0x4d4], 0x5
        jmp     loc_361a

loc_17AA8:
        mov     ax, [0x4a3]
        neg     ax
        sbb     ax, ax
        inc     ax
        mov     [0x4a3], ax
        jmp     loc_361a

loc_17AB6:
        mov     bx, [0x4df]
        or      byte [bx+0x8], 0x8
        jmp     loc_361a

loc_17AC1:
        mov     bx, [0x4df]
        and     byte [bx+0x8], 0xf7
        jmp     loc_361a

loc_17ACC:
        mov     byte [0x498], 0x1
        jmp     loc_361a

loc_3494:
        mov     al, [0x57d]
        mov     ah, 0x0
        mov     cx, 0x6
        mov     bx, switch_table_2

switch_loop_2:
        cmp     ax, [cs:bx]
        jz      loc_34ab
        inc     bx
        inc     bx
        loop    switch_loop_2
        jmp     loc_3613

loc_34ab:
        jmp     [cs:bx+6*2]

switch_table_2:
        dw      '#'
        dw      '$'
        dw      '/'
        dw      '@'
        dw      '\'
        dw      '^'

jpt_17AEB:
        dw      loc_17B07
        dw      loc_17B74
        dw      loc_17BB6
        dw      loc_17C1F
        dw      loc_17BCC
        dw      loc_17BF3

loc_17B07:
        push    word [bp+0x6]

fixmeup0: ; far call by absolute direct address
        call    0x2ce6:0x3 ; toupper
        pop     cx
        mov     [bp+0x6], ax
        cmp     ax, 0x30
        jl      loc_34e4
        cmp     ax, 0x39
        jg      loc_34e4
        mov     si, ax
        add     si, byte -0x30
        jmp     loc_34fa

loc_34e4:
        cmp     word [bp+0x6], byte +0x41
        jl      loc_34f8
        cmp     word [bp+0x6], byte +0x5a
        jg      loc_34f8
        mov     si, [bp+0x6]
        add     si, byte -0x37
        jmp     loc_34fa

loc_34f8:
        xor     si, si

loc_34fa:
        mov     bx, si
        shl     bx, 1
        cmp     word [bx-0x491f], byte +0x1
        jz      loc_350a
        mov     ax, 0x1
        jmp     loc_350c

loc_350a:
        xor     ax, ax

loc_350c:
        mov     [0x49d], ax
        mov     bx, si
        shl     bx, 1
        push    word [bx-0x491f]
        push    ss
        lea     ax, [bp-0x8]
        push    ax
        mov     ax, 0x6
        push    ax
        mov     ax, 0xfff6
        push    ax

fixmeup7: ; far call by absolute direct address
        call    0x464:0x331a ; atoi
        push    ss
        lea     ax, [bp-0x8]
        push    ax

fixmeup8: ; far call by absolute direct address
        call    0x464:0x32f8 ; puts
        jmp     loc_35d8

loc_17B74:
        push    word [bp+0x6]

fixmeup1: ; far call by absolute direct address
        call    0x2ce6:0x3 ; toupper
        pop     cx
        mov     [bp+0x6], ax
        cmp     ax, 0x30
        jl      loc_3551
        cmp     ax, 0x39
        jg      loc_3551
        mov     si, ax
        add     si, byte -0x30
        jmp     loc_3567

loc_3551:
        cmp     word [bp+0x6], byte +0x41
        jl      loc_3565
        cmp     word [bp+0x6], byte +0x5a
        jg      loc_3565
        mov     si, [bp+0x6]
        add     si, byte -0x37
        jmp     loc_3567

loc_3565:
        xor     si, si

loc_3567:
        push    ds
        mov     bx, si
        shl     bx, 1
        push    word [bx-0x48d3]

fixmeup9: ; far call by absolute direct address
        call    0x464:0x32f8 ; puts
        jmp     loc_35d8

loc_17BB6: ; '/'
        mov     bx, [bp+0x6]
        test    byte [bx+0x3117], 0xc
        jz      loc_35a0
        cmp     word [0x49d], byte +0x0
        jz      loc_358a
        jmp     loc_361a

loc_358a:
        jmp     loc_35a0

loc_17BCC: ; '\'
        mov     bx, [bp+0x6]
        test    byte [bx+0x3117], 0xc
        jz      loc_35a0
        cmp     word [0x49d], byte +0x0
        jnz     loc_35a0
        jmp     loc_361a

loc_35a0:
        push    word [bp+0x6]

fixmeupA: ; far call by absolute direct address
        call    0x464:0x2efa ; putch_impl
        mov     bx, [bp+0x6]
        test    byte [bx+0x3117], 0xc
        jnz     loc_361a
        jmp     loc_35d8

loc_17BF3: ; '^'
        mov     bx, [0x4df]
        test    byte [bx+0x8], 0x8
        jz      loc_35cd
        mov     ax, [bp+0x6]
        and     ax, 0x1f
        or      ax, 0x80
        push    ax

fixmeupB: ; far call by absolute direct address
        call    0x464:0x2efa ; putch_impl
        jmp     loc_35d8

loc_35cd:
        mov     ax, [bp+0x6]
        and     ax, 0x1f
        push    ax

fixmeupC: ; far call by absolute direct address
        call    0x464:0x2efa ; putch_impl

loc_35d8:
        mov     byte [0x57d], 0x0
        jmp     loc_361a

loc_17C1F:
        push    word [bp+0x6]
        mov     ax, 0x5be ; ' ,.:;!?\'-"\n'.
        push    ax

fixmeup2: ; far call by absolute direct address
        call    0x2c1b:0xa ; strchr
        pop     cx
        pop     cx
        or      ax, ax
        jz      loc_3602
        mov     byte [0x57d], 0x0
        mov     al, [0x2a56]
        mov     bx, [0x4df]
        mov     [bx+0x6], al
        jmp     loc_3613

loc_3602:
        cmp     word [0x4a1], byte +0x0
        jz      loc_3613
        mov     al, [0x2a4a]
        mov     bx, [0x4df]
        mov     [bx+0x6], al

loc_3613:
        push    word [bp+0x6]

fixmeupD: ; far call by absolute direct address
        call    0x464:0x2efa ; putch_impl

loc_361a:
        pop     si
        mov     sp, bp
        pop     bp
        retf    0x2
