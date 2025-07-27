bits 16

global sub_0002

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0x30432 0x30463 0x2

sub_0002:
        push    bp
        mov     bp, sp

        mov     ax, [bp+0x6]
        cmp     ax, 0xffff
        jz      loc_0031

        cmp     ax, 0x80
        jb      loc_0010

        cmp     ax, 0x100
        jae     loc_0010

        ; ax — 0x80..0xff
        cmp     ax, 0x90
        jb      or_20

        ; ax — 0x90..0xff
        cmp     ax, 0xa0
        jb      add_50

        ; ax — 0xa0..0xff
        cmp     ax, 0xf0
        jb      loc_0031 ; Ё

        cmp     ax, 0xf2
        jae     loc_0031

        inc     ax
        jmp     loc_0031

add_50:
        add     ax, 0x50
        jmp     loc_0031

or_20:
        or      ax, 0x20
        jmp     loc_0031

loc_0010:
        mov     bx, ax
        cmp     ax, 0x100
        jb      skip_fix_runes

        and     bx, 0xfeff
        or      bx, 0x80

skip_fix_runes:
        test    byte [bx+0x3117], 0x4 ; От этой таблицы регистров можно было бы избавиться.
        jz      loc_0031

        mov     al, [bp+0x6]
        mov     ah, 0x0
        add     ax, 0x20
        jmp     loc_0031

loc_0031:
        pop     bp
        retf
