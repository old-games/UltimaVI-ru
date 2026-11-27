bits 16

global menu_toupper

global fixmeup0

section CODE

; Главное меню (выбор пункта, 0x3374 в файле): Ctrl+Q — выход в DOS. В русской версии и Ctrl+В (та же клавиша,
; что Ctrl+D, код 0x04), как в игре (GAME.EXE, hotkeys.asm).
menu_toupper:
        push    bp
        mov     bp, sp
        push    word [bp+0x6]

fixmeup0: ; far call by absolute direct address
        call    0x1240:0xf ; toupper
        add     sp, byte +0x2
%ifdef RUSSIAN
        cmp     ax, 0x04
        jnz     .done
        mov     ax, 0x11
.done:
%endif
        pop     bp
        retf
