bits 16

global sub_0003

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0x30463 0x30494 0x3

sub_0003:
        push    bp
        mov     bp, sp

        ; FIXME Первоначально `toupper` работала только с младшим байтом.
        ; Это позволяло также использовать её на расширенных символах,
        ; приходящих от прерываний BIOS, для нормализации горячих клавиш.

        mov     ax, [bp+0x6]
        cmp     ax, 0xffff
        jz      loc_0032

        cmp     ax, 0x80
        jb      loc_0011

        cmp     ax, 0x100
        jae     loc_0011

        ; ax — 0x80..0xff
        cmp     ax, 0xa0
        jb      loc_0032

        cmp     ax, 0xf0
        jz      loc_0032 ; Ё

        cmp     ax, 0xb0
        jb      and_df

        cmp     ax, 0xe0
        jb      loc_0032

        cmp     ax, 0xf0
        jb      sub_50

        cmp     ax, 0xf2
        jae     loc_0032

        dec     ax
        jmp     loc_0032

sub_50:
        sub     ax, 0x50
        jmp     loc_0032

and_df:
        and     ax, 0xdf
        jmp     loc_0032

loc_0011:
        mov     bx, ax
        cmp     ax, 0x100
        jb      skip_fix_runes

        and     bx, 0xfeff
        or      bx, 0x80

skip_fix_runes:
        test    byte [bx+0x3117], 0x8 ; От этой таблицы регистров можно было бы избавиться.
        jz      loc_0032

        mov     al, [bp+0x6]
        mov     ah, 0x0
        add     ax, 0xffe0
        jmp     short loc_0032

loc_0032:
        pop     bp
        retf
