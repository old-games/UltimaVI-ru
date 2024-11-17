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

