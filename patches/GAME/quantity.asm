bits 16

global object_name
global look_quantity
global look_print_name

global fixmeup0
global fixmeup1
%ifndef RUSSIAN
global fixmeup2
%endif
global fixmeup3
global fixmeup4

section CODE

; Формы единственного/множественного числа в названиях предметов (`стрел/а\ы`): putch печатает буквы после `/`,
; если флаг DS:0x49D равен 0, и после `\` — если не 0. Флаг ставит printf по последнему напечатанному числу
; (не равно 1), поэтому в «Используй-…» форма зависела от случайного числа (вес и урон из прошлого осмотра).
; object_name — замена вызова функции названия предмета 0x94c:0x3c9c во всех местах: после неё флаг ставится
; по количеству предметов в стопке (0x94c:0x21fd, 1 для нестопочных).
;
; В русской версии при осмотре и обыске количество печатается после названия: «золотые монеты (20)».
; look_quantity заменяет printf("%d ", количество) в функции 0x234d1 (артикль или количество перед названием)
; и только запоминает количество, look_print_name заменяет printf(название) после неё в 4 местах осмотра
; и дописывает « (N)», если количество не 1. В английской версии всё печатается как в оригинале.

%define PLURAL 0x49d ; флаг «последнее число не 1» для `/` и `\`

object_name:
        push    bp
        mov     bp, sp
        push    word [bp+0x6]

fixmeup0: ; far call by absolute direct address
        call    0x94c:0x3c9c ; название предмета, retf 2
        cmp     word [bp+0x6], byte +0x0
        jl      object_name_done
        push    ax
        push    word [bp+0x6]

fixmeup1: ; far call by absolute direct address
        call    0x94c:0x21fd ; количество предметов, retf 2
        cmp     ax, 0x1
        mov     ax, 0x0
        jz      object_name_set
        inc     ax
object_name_set:
        mov     [PLURAL], ax
        pop     ax
object_name_done:
        pop     bp
        retf    0x2

; printf(format, количество) — форма cdecl, аргументы снимает вызывающий.
look_quantity:
        push    bp
        mov     bp, sp
%ifdef RUSSIAN
        mov     ax, [bp+0xa]
        mov     [cs:quantity], ax
        mov     byte [cs:pending], 1
%else
        push    word [bp+0xa]
        push    word [bp+0x8]
        push    word [bp+0x6]

fixmeup2: ; far call by absolute direct address
        call    0x464:0x3643 ; printf
        add     sp, byte +0x6
%endif
        pop     bp
        retf

; printf(название) — форма cdecl, аргументы снимает вызывающий.
look_print_name:
        push    bp
        mov     bp, sp
        push    word [bp+0x8]
        push    word [bp+0x6]

fixmeup3: ; far call by absolute direct address
        call    0x464:0x3643 ; printf
        add     sp, byte +0x4
        cmp     byte [cs:pending], 0
        jz      print_name_done
        mov     byte [cs:pending], 0
        cmp     word [cs:quantity], byte +0x1
        jz      print_name_done
        push    word [cs:quantity]
        push    cs
        mov     ax, suffix
        push    ax

fixmeup4: ; far call by absolute direct address
        call    0x464:0x3643 ; printf
        add     sp, byte +0x6
print_name_done:
        pop     bp
        retf

suffix:
        db      ' (%d)', 0
pending:
        db      0
quantity:
        dw      0
