bits 16

global sub_0003

section CODE

; cat unpacked/GAME.EXE | head -c197780 | tail -c+197732

sub_0003:
        push    bp
        mov     bp, sp

        ; FIXME Первоначально `toupper` работала только с младшим байтом.
        ; Это позволяло также использовать её на расширенных символах,
        ; приходящих от прерываний BIOS, для нормализации горячих клавиш.

        mov     ax, [bp+0x6]
        cmp     ax, 0xffff
        jz      loc_32

        cmp     ax, 0x80
        jb      loc_11

        cmp     ax, 0x100
        jae     loc_11

        ; ax — 0x80..0xff
        cmp     ax, 0xa0
        jb      loc_32

        cmp     ax, 0xf0
        jz      loc_32 ; Ё

        cmp     ax, 0xb0
        jb      and_df

        cmp     ax, 0xe0
        jb      loc_32

        cmp     ax, 0xf0
        jb      sub_50

        cmp     ax, 0xf2
        jae     loc_32

        dec     ax
        jmp     loc_32

sub_50:
        sub     ax, 0x50
        jmp     loc_32

and_df:
        and     ax, 0xdf
        jmp     loc_32

loc_11:
        mov     bx, ax
        cmp     ax, 0x100
        jb      skip_fix_runes

        and     bx, 0xfeff
        or      bx, 0x80

skip_fix_runes:
        test    byte [bx+0x3117], 0x8 ; От этой таблицы регистров можно было бы избавиться.
        jz      loc_32

        mov     al, [bp+0x6]
        mov     ah, 0x0
        add     ax, 0xffe0
        jmp     short loc_32

loc_32:
        pop     bp
        retf
