bits 16

global disk_toupper
global drive_toupper
global yes_no_toupper
global option_toupper

global fixmeup0
global fixmeup1
global fixmeup2
global fixmeup3

section CODE

; Русские буквы в ответах INSTALL.EXE. Ввод — getch (DOS, int 21h AH=7), затем toupper; вызов toupper в каждом
; вопросе перенаправлен сюда. С русской раскладкой буква приходит байтом cp866: «а»..«п» 0xa0..0xaf,
; «р»..«я» 0xe0..0xef, «А»..«Я» 0x80..0x9f. Латинские буквы оригинала работают как раньше.

; Номер русской буквы в алфавите (А = 0 .. Я = 31) в al, CF = 1, если это не русская буква (кроме Ё).
russian_index:
        cmp     al, 0x80
        jb      .no
        cmp     al, 0xa0
        jb      .upper
        cmp     al, 0xb0
        jb      .lower
        cmp     al, 0xe0
        jb      .no
        cmp     al, 0xf0
        jae     .no
        sub     al, 0xe0 - 0x10 ; р..я -> 16..31
        clc
        ret
.lower:
        sub     al, 0xa0 ; а..п -> 0..15
        clc
        ret
.upper:
        sub     al, 0x80
        clc
        ret
.no:
        stc
        ret

; toupper(аргумент) оригинала, результат в ax.
%macro call_toupper 1
        push    bp
        mov     bp, sp
        push    word [bp+0x6]
%1: ; far call by absolute direct address
        call    0x4ee:0x6 ; toupper
        add     sp, byte +0x2
        pop     bp
%endmacro

; Если номер русской буквы в dl равен %1 — вернуть латинскую %2.
%macro map_letter 2
        cmp     dl, %1
        jnz     %%next
        mov     ax, %2
        retf
%%next:
%endmacro

; «Установить на жёсткий диск (Ж) или на дискету (Д)?» — H или F.
disk_toupper:
        call_toupper fixmeup0
        mov     dx, ax
        call    russian_index
        xchg    ax, dx ; ax — буква, dl — номер в алфавите (флаги xchg не меняет)
        jc      .done
        map_letter 6, 'H' ; Ж
        map_letter 4, 'F' ; Д
.done:
        retf

; «Сделано ли всё это (Д/Н)?», мышь, драйвер, «Всё верно?» — Y или N.
yes_no_toupper:
        call_toupper fixmeup1
        mov     dx, ax
        call    russian_index
        xchg    ax, dx ; ax — буква, dl — номер в алфавите (флаги xchg не меняет)
        jc      .done
        map_letter 4, 'Y' ; Д
        map_letter 13, 'N' ; Н
.done:
        retf

; Порт: «(а) 218  (б) 288 ...» — а..е -> A..F (по порядку в алфавите).
option_toupper:
        call_toupper fixmeup2
        mov     dx, ax
        call    russian_index
        xchg    ax, dx ; ax — буква, dl — номер в алфавите (флаги xchg не меняет)
        jc      .done
        cmp     dl, 6
        jae     .done
        mov     al, dl
        add     al, 'A'
        mov     ah, 0
.done:
        retf

; Буква диска («C:»): русская буква -> латинская на той же клавише (ЙЦУКЕН -> QWERTY), с русской раскладкой
; клавиша C даёт «с». Буквы на клавишах-знаках ([ ] ; ' , .) не меняются, isalpha их не пропустит.
drive_toupper:
        call_toupper fixmeup3
        mov     dx, ax
        call    russian_index
        xchg    ax, dx ; ax — буква, dl — номер в алфавите (флаги xchg не меняет)
        jc      .done
        mov     bl, dl
        mov     bh, 0
        mov     dl, [cs:bx+qwerty]
        or      dl, dl
        jz      .done
        mov     al, dl
        mov     ah, 0
.done:
        retf

qwerty: ; А Б В Г Д Е Ж З И Й К Л М Н О П Р С Т У Ф Х Ц Ч Ш Щ Ъ Ы Ь Э Ю Я
        db      'F', 0, 'D', 'U', 'L', 'T', 0, 'P', 'B', 'Q', 'R', 'K', 'V', 'Y', 'J', 'G'
        db      'H', 'C', 'N', 'E', 'A', 0, 'W', 'X', 'I', 'O', 0, 'S', 'M', 0, 0, 'Z'
