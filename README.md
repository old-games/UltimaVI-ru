# Ultima VI: Russian Edition

Structure:

- `original` — original files;
- `unpacked` — unpacked files (when it's possible);
- `conversations` — scripts;
- `patches` — fixes for executables;
- `documentation` — manuals.

## Status

|               | Decoder | Encoder | Translation |
|--------------:|:-------:|:-------:|:-----------:|
| Conversations |    ✅    |    ✅    |      ⏳      |
|          Book |    ✅    |    ✅    |      ⏳      |
|          Look |    ✅    |    ✅    |      ⏳      |

## Build

```
python3 -m tools.build
```

Or:

```
python3 -m tools.build english
```

## Test

```
docker-compose run --build test
```

## Время суток в диалогах: $T и $V

`$T` — время суток в первой форме, `$V` — во второй. Обе формы задаются в `patches/translation.json`
у строк `morning`, `afternoon`, `evening` через `|`: `"утра|утром"`, `"дня|днём"`, `"вечера|вечером"` —
тогда «Доброго $T» → «Доброго утра», «Чем помочь этим $V?» → «Чем помочь этим утром?». Без `|` `$V`
совпадает с `$T`. Утро — до 12 часов, день — до 18, дальше вечер.

## Графика: заставка, меню, создание персонажа

Перерисованные кадры лежат в `graphics/` как PNG: `graphics/MAINMENU.SHP/000.png` — кадр 0 архива `MAINMENU.SHP`.
Сборка (`tools.build`, русские данные) собирает из них архивы `*.SHP`; кадры без PNG остаются оригинальными.
PNG — indexed с палитрой игры, прозрачный цвет — индекс 255 (подробности в `tools/shapes.py`).

Перерисовки ведутся в «Системе Переводчик». Обновить `graphics/` из выгрузки СП (ZIP проекта или распакованная
папка) — `python3 -m tools.shapes import project.zip`: в `graphics/` попадают только кадры, отличающиеся от
оригинала. Оригиналы кадров с текстом для загрузки в СП — `python3 -m tools.shapes export original <папка>`.

## Шрифты

Шрифты игры хранятся текстом: `tools/U6.CH.txt` (основной, 8×8) и `tools/U6.SET.txt` (пропорциональный: заставка,
создание персонажа); сборка делает из них `U6.CH` и `U6.SET`. Раскладка — CP866.

Для банка шрифтов СП — BDF: `python3 -m tools.bdf export tools/U6.CH.txt U6_CH.bdf Ultima6-U6.CH`. Поправленный
в СП шрифт (скачать BDF из карточки шрифта) — обратно: `python3 -m tools.bdf import U6_CH.bdf tools/U6.CH.txt`.
Импорт меняет только знаки 0x20–0xFF, которые есть в BDF; символы вне CP866 пропускает с предупреждением, знак
неверной ширины или выходящий за 8 строк — ошибка.

## Как найти артефакты?

### Способ 1

1. Перейти в Actions: https://github.com/old-games/UltimaVI-ru/actions
2. Кликнуть слева по Build: https://github.com/old-games/UltimaVI-ru/actions/workflows/build.yml
3. Открыть из списка нужную джобу: https://github.com/old-games/UltimaVI-ru/actions/runs/4086596193
4. Артефакты находятся внизу страницы

### Способ 2

1. Кликнуть на зелёную галочку слева от хэша коммита
2. Кликнуть на Build / build (pull\_request) Details: https://github.com/old-games/UltimaVI-ru/actions/runs/4095611799/jobs/7062643513
3. Кликнуть слева по Summary: https://github.com/old-games/UltimaVI-ru/actions/runs/4095611799
4. Артефакты находятся внизу страницы

