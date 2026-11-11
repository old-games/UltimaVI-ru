bits 16

global sub_00a0

global fixmeup0
global fixmeup1

section CODE

; python3 -m tools.format unpacked/GAME.EXE 0x12350 0x123c6 0xa0

sub_00a0:
        push    bp
        mov     bp, sp
        push    si
        push    word [bp+0x6]
        push    word [0x9e3b]
        push    word [0x9e39]

fixmeup0: ; far call by absolute direct address
        call    0x2789:0x1d40
        or      ax, ax
        jz      loc_00d2
        xor     si, si
        jmp     loc_00cb

loc_00bc:
        les     bx, [0x9e39]
        add     bx, si
        mov     al, [es:bx+0x2]
        mov     [si-0x189c], al
        inc     si

loc_00cb:
        cmp     si, byte +0x32
        jl      loc_00bc
        jmp     loc_00d7

loc_00d2:
        mov     byte [0xe764], 0x0

loc_00d7:
        xor     si, si

; Имя кончается командой скрипта. В оригинале — любым байтом >= 0x80 (обычно 0xF1, описание), в версии 2 описание —
; байт 1, а 0x80..0xF1 — русские буквы (Ё/ё — 0xF0/0xF1). Но перед описанием может стоять и другая команда (0xF3
; у Фёдора, Эфемерида, Хендла), поэтому имя кончается и на байте >= 0xF2: иначе он печатался после имени («Фёдор<»).
loc_00d9:
        cmp     byte [si-0x189c], 1
        jz      loc_00ec
        cmp     byte [si-0x189c], 0xf2
        jae     loc_00ec
        mov     ax, si
        inc     si
        mov     bx, ax
        cmp     byte [bx-0x189c], 0x0
        jnz     loc_00d9

loc_00ec:
        or      si, si
        jnz     loc_0109
        push    ds
        mov     ax, 0x98e
        push    ax

fixmeup1: ; far call by absolute direct address
        call    0x464:0x3643
        pop     cx
        pop     cx

loc_0109:
        mov     byte [si-0x189c], 0x0
        mov     ax, 0xe764
        pop     si
        pop     bp
        retf    0x2
