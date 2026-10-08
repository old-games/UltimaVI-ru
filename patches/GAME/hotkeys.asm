bits 16

global hotkey_toupper
global command_getch
global yes_no_getch
global conversation_getch

global fixmeup0
global fixmeup1
global fixmeup2
global fixmeup3

section CODE

; Русские горячие клавиши. С RK.COM русская буква приходит от клавиатуры байтом cp866 0x80..0xff,
; а коды 0x80..0xff игра использует для событий интерфейса (иконки, портреты, листание отряда в getch),
; поэтому буква до этого места доходить не должна. Вызов toupper в обработчике событий (0x464:0x1d59)
; перенаправлен сюда: буквы команд переводятся в латинские, остальные русские — в 0x200 | буква
; (такие коды игра не знает и пропускает). «Д» — и «Двигать», и «Да», поэтому остаётся KEY_D,
; а латинской буквой становится в command_getch (M) и yes_no_getch (Y). В оригинале R — и отдых,
; и ремонт корабля (выбор в обработчике 0x2d7dd по [0x2c54] == [0x8e50], отряд в транспорте), а в русском
; это «О» и «Ч»: command_getch превращает KEY_O в R только вне транспорта, KEY_CH — только в транспорте.
; Диалогам (choice «дн» и ввод символа) нужна сама русская буква: hotkey_toupper запоминает её и код,
; в который она превратилась, а conversation_getch возвращает букву, если getch вернул этот код.

%define KEY_D 0x284
%define KEY_O 0x28e
%define KEY_CH 0x297
%define ACTIVE_ACTOR 0x2c54
%define PARTY_SIZE 0x8e50

hotkey_toupper:
        push    bp
        mov     bp, sp
        push    word [bp+0x6]

fixmeup0: ; far call by absolute direct address
        call    0x2ce6:0x3 ; toupper
        add     sp, byte +0x2

        mov     byte [cs:last_letter], 0
        cmp     ax, 0x80
        jb      .done
        cmp     ax, 0x100
        jae     .done

        mov     [cs:last_letter], al
        mov     bx, keys
.next:
        cmp     byte [cs:bx], 0
        jz      .other
        cmp     al, [cs:bx]
        jz      .found
        add     bx, byte +0x3
        jmp     .next

.found:
        mov     ax, [cs:bx+0x1]
        jmp     .done

.other:
        or      ax, 0x200

.done:
        mov     [cs:last_code], ax
        pop     bp
        retf

last_letter: ; последняя русская буква (заглавная cp866) или 0
        db      0
last_code: ; во что hotkey_toupper её превратила
        dw      0

keys: ; cp866, затем код клавиши
        db      0x80
        dw      'A' ; А — Атаковать
        db      0x81
        dw      'B' ; Б — Бой
        db      0x8a
        dw      'C' ; К — Колдовать
        db      0x82
        dw      'D' ; В — Выбросить
        db      0x8f
        dw      'G' ; П — Поднять
        db      0x91
        dw      'L' ; С — Смотреть
        db      0x84
        dw      KEY_D ; Д — Двигать / Да
        db      0x8e
        dw      KEY_O ; О — Отдыхать
        db      0x97
        dw      KEY_CH ; Ч — Чинить
        db      0x83
        dw      'T' ; Г — Говорить
        db      0x88
        dw      'U' ; И — Использовать
        db      0x8d
        dw      'N' ; Н — Нет
        db      0

; Замена вызова getch в цикле команд (0x7298 в файле).
command_getch:
fixmeup1: ; far call by absolute direct address
        call    0x464:0x2a59 ; getch
        cmp     ax, KEY_D
        jnz     .not_d
        mov     ax, 'M'
        retf

.not_d:
        mov     cl, [ACTIVE_ACTOR]
        cmp     cl, [PARTY_SIZE] ; ZF — отряд в транспорте
        jz      .vehicle
        cmp     ax, KEY_O
        jnz     .done
        mov     ax, 'R'
        retf

.vehicle:
        cmp     ax, KEY_CH
        jnz     .done
        mov     ax, 'R'

.done:
        retf

; Замена вызова getch в вопросах «да/нет» (сравнение с 'Y' и 'N').
yes_no_getch:
fixmeup2: ; far call by absolute direct address
        call    0x464:0x2a59 ; getch
        cmp     ax, KEY_D
        jnz     .done
        mov     ax, 'Y'
.done:
        retf

; Замена вызова getch в диалогах: choice (0x145a7) и ввод символа (0x144c0, 0x1453e).
conversation_getch:
fixmeup3: ; far call by absolute direct address
        call    0x464:0x2a59 ; getch
        cmp     byte [cs:last_letter], 0
        jz      .done
        cmp     ax, [cs:last_code]
        jnz     .done
        mov     al, [cs:last_letter]
        mov     ah, 0
.done:
        retf
