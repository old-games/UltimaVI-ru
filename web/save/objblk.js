// Предметы на участках карты: SAVEGAME/OBJBLKxx. Формат сверен с движком Nuvie (ObjManager::loadObj, addObjToContainer).
// Файл: u16 число предметов, затем по 8 байт: статус, x/y/z (10/10/4 бит), тип/кадр (10/6 бит), количество, качество.
// Игра хранит инвентарь персонажа в файле того участка, где он стоит, и грузит только участки рядом с отрядом,
// поэтому при телепорте вещи отряда нужно переносить в файл участка назначения.

(function (root) {
    'use strict';

    const RECORD = 8;
    const LOCATION = 0x18;      // биты статуса: где предмет
    const IN_CONTAINER = 0x08;
    const IN_INVENTORY = 0x10;
    const READIED = 0x18;

    // Поверхность: OBJBLK + буква участка по x + буква по y (участки 128×128, A–H). Подземелья: AI–EI для этажей 1–5.
    function blockName({x, y, z}) {
        const letter = n => String.fromCharCode(65 + n);
        return z === 0 ? `OBJBLK${letter(x >> 7)}${letter(y >> 7)}` : `OBJBLK${letter(z - 1)}I`;
    }

    function parse(data) {
        const count = data[0] | data[1] << 8;
        if (data.length !== 2 + count * RECORD) {
            throw new Error(`Неверный размер файла предметов: ${data.length} байт для ${count} предметов`);
        }
        const records = [];
        for (let i = 0; i < count; i++) {
            records.push(data.slice(2 + i * RECORD, 2 + (i + 1) * RECORD));
        }
        return records;
    }

    function serialize(records) {
        const data = new Uint8Array(2 + records.length * RECORD);
        data[0] = records.length & 0xff;
        data[1] = records.length >> 8;
        records.forEach((record, i) => data.set(record, 2 + i * RECORD));
        return data;
    }

    const location = record => record[0] & LOCATION;
    const x = record => record[1] | (record[2] & 0x3) << 8;
    // Предмет в контейнере: номер контейнера в этом же файле — 10 бит в x и младшие 6 бит y.
    const parent = record => x(record) | (record[2] >> 2 & 0x3f) << 10;

    function setParent(record, index) {
        record[1] = index & 0xff;
        record[2] = index >> 8 & 0x3 | (index >> 10 & 0x3f) << 2;
    }

    // Номера предметов в инвентаре персонажей actors (в руках, надетые, в сумках на любой глубине).
    function inventoryIndices(records, actors) {
        const selected = new Set();
        records.forEach((record, i) => {
            const where = location(record);
            if ((where === IN_INVENTORY || where === READIED) && actors.has(x(record))) {
                selected.add(i);
            }
        });
        records.forEach((record, i) => {
            if (location(record) === IN_CONTAINER && selected.has(parent(record))) {
                selected.add(i);   // содержимое идёт после контейнера, поэтому одного прохода хватает
            }
        });
        return selected;
    }

    // Вырезает из records предметы с номерами selected и возвращает [оставшиеся, вырезанные] с исправленными ссылками.
    function split(records, selected) {
        const rest = [];
        const taken = [];
        const newIndex = new Map();
        records.forEach((record, i) => {
            const target = selected.has(i) ? taken : rest;
            newIndex.set(i, target.length);
            target.push(new Uint8Array(record));
        });
        for (const [list, inSelection] of [[rest, false], [taken, true]]) {
            list.forEach(record => {
                if (location(record) === IN_CONTAINER) {
                    const old = parent(record);
                    if (selected.has(old) !== inSelection) {
                        throw new Error('Контейнер и его содержимое оказались в разных файлах');
                    }
                    setParent(record, newIndex.get(old));
                }
            });
        }
        return [rest, taken];
    }

    // blocks: Map имя файла → Uint8Array. Переносит инвентарь actors из всех файлов в файл target.
    // Возвращает имена изменённых файлов и число перенесённых предметов.
    function moveInventories(blocks, actors, target) {
        const actorSet = new Set(actors);
        if (!blocks.has(target)) {
            throw new Error(`Нет файла ${target} в SAVEGAME`);
        }
        const changed = new Set();
        const moved = [];
        for (const [name, data] of blocks) {
            if (name === target) {
                continue;
            }
            const records = parse(data);
            const selected = inventoryIndices(records, actorSet);
            if (selected.size === 0) {
                continue;
            }
            const [rest, taken] = split(records, selected);
            blocks.set(name, serialize(rest));
            changed.add(name);
            moved.push(taken);
        }
        if (moved.length) {
            const records = parse(blocks.get(target));
            for (const taken of moved) {
                const base = records.length;
                for (const record of taken) {
                    if (location(record) === IN_CONTAINER) {
                        setParent(record, base + parent(record));
                    }
                    records.push(record);
                }
            }
            blocks.set(target, serialize(records));
            changed.add(target);
        }
        return {changed: [...changed], count: moved.reduce((sum, taken) => sum + taken.length, 0)};
    }

    function inventoryCount(blocks, actors) {
        const actorSet = new Set(actors);
        const result = new Map();
        for (const [name, data] of blocks) {
            const count = inventoryIndices(parse(data), actorSet).size;
            if (count) {
                result.set(name, count);
            }
        }
        return result;
    }

    const SPELLBOOK = 57;
    const SPELL = 58;       // качество = номер заклинания ((круг - 1) * 16 + номер в круге)
    const objectType = record => record[4] | (record[5] & 0x3) << 8;

    function makeRecord(status, xValue, obj, {frame = 0, qty = 0, quality = 0} = {}) {
        return Uint8Array.of(status, xValue & 0xff, xValue >> 8 & 0x3, 0, obj & 0xff, obj >> 8 & 0x3 | frame << 2,
            qty & 0xff, quality);
    }

    function check(blocks, name) {
        if (!blocks.has(name)) {
            throw new Error(`Нет файла ${name} в SAVEGAME`);
        }
    }

    // Кладёт предмет в инвентарь персонажа actor (файл name — участок, где он стоит). Стопки складываются с уже
    // лежащими в инвентаре (не в сумках), количество до 65535 хранится в байтах количества и качества.
    function addItem(blocks, name, actor, {obj, qty = 1, frame = 0, quality = 0, stackable = false, readied = false}) {
        check(blocks, name);
        const records = parse(blocks.get(name));
        if (stackable) {
            if (!(Number.isInteger(qty) && qty >= 1 && qty <= 65535)) {
                throw new Error(`Количество 1–65535: ${qty}`);
            }
            const stack = records.find(r => location(r) === IN_INVENTORY && x(r) === actor && objectType(r) === obj
                && r[5] >> 2 === frame);
            if (stack) {
                const total = Math.min((stack[6] | stack[7] << 8) + qty, 65535);
                stack[6] = total & 0xff;
                stack[7] = total >> 8;
                blocks.set(name, serialize(records));
                return total;
            }
            records.push(makeRecord(IN_INVENTORY, actor, obj, {frame, qty: qty & 0xff, quality: qty >> 8}));
        } else {
            records.push(makeRecord(readied ? READIED : IN_INVENTORY, actor, obj, {frame, quality}));
        }
        blocks.set(name, serialize(records));
        return qty;
    }

    // Кладёт заклинания в книгу персонажа; если книги нет ни в одном файле — выдаёт её в руку (колдовать можно
    // только с книгой в руке) в файле name.
    // Возвращает число добавленных заклинаний.
    function addSpells(blocks, name, actor, numbers) {
        check(blocks, name);
        let bookFile = null;
        let book = -1;
        for (const [file, data] of blocks) {
            const records = parse(data);
            const index = records.findIndex(r => (location(r) === IN_INVENTORY || location(r) === READIED)
                && x(r) === actor && objectType(r) === SPELLBOOK);
            if (index >= 0) {
                bookFile = file;
                book = index;
                break;
            }
        }
        if (book < 0) {
            addItem(blocks, name, actor, {obj: SPELLBOOK, readied: true});
            bookFile = name;
            book = parse(blocks.get(name)).length - 1;
        }
        const records = parse(blocks.get(bookFile));
        const known = new Set(records.filter(r => location(r) === IN_CONTAINER && parent(r) === book
            && objectType(r) === SPELL).map(r => r[7]));
        let added = 0;
        for (const number of numbers) {
            if (!known.has(number)) {
                const record = makeRecord(IN_CONTAINER, 0, SPELL, {quality: number});
                setParent(record, book);
                records.push(record);
                known.add(number);
                added++;
            }
        }
        blocks.set(bookFile, serialize(records));
        return added;
    }

    // Двери (дубовая, с окном, кедровая, стальная) и сундуки на карте, у которых есть замок: ключ открывает их,
    // если его качество равно качеству двери (и не 0).
    const LOCKABLE = new Map([[297, 'дверь'], [298, 'дверь с окном'], [299, 'кедровая дверь'], [300, 'стальная дверь'],
        [98, 'сундук']]);

    function locks(data) {
        return parse(data)
            .filter(r => location(r) === 0 && LOCKABLE.has(objectType(r)) && r[7] !== 0)
            .map(r => ({
                obj: objectType(r),
                name: LOCKABLE.get(objectType(r)),
                x: x(r),
                y: r[2] >> 2 | (r[3] & 0xf) << 6,
                z: r[3] >> 4,
                quality: r[7],
            }));
    }

    // Яйца — невидимые объекты 335 на карте, из которых игра выпускает монстров (Nuvie, EggManager::spawn_egg).
    // Количество яйца — шанс в процентах (100 — всегда и ровно столько монстров, сколько указано), качество —
    // время (0–9 всегда, 10–19 днём, 20–29 ночью) * 10 + отношение к отряду (0 по умолчанию, 1 нейтральные,
    // 2 злые, 3 добрые, 4 хаотичные). Внутри — «зародыши»: тип монстра, количество (до скольких), качество — режим
    // поведения. Третий байт зародыша во всех яйцах игры 0x7b — повторяем.
    const EGG = 335;
    const y = record => record[2] >> 2 | (record[3] & 0xf) << 6;
    const z = record => record[3] >> 4;

    function mapRecord(status, position, obj, {frame = 0, qty = 0, quality = 0} = {}) {
        return Uint8Array.of(status, position.x & 0xff, position.x >> 8 & 0x3 | (position.y & 0x3f) << 2,
            position.y >> 6 & 0xf | position.z << 4, obj & 0xff, obj >> 8 & 0x3 | frame << 2, qty & 0xff, quality);
    }

    // Вставляет records в list по номеру index; номера контейнеров у остальных предметов сдвигаются.
    function insert(list, index, records) {
        list.forEach(record => {
            if (location(record) === IN_CONTAINER && parent(record) >= index) {
                setParent(record, parent(record) + records.length);
            }
        });
        list.splice(index, 0, ...records);
    }

    // Яйца на клетке (только лежащие на карте) — номера записей.
    function eggsAt(records, position) {
        const result = [];
        records.forEach((record, i) => {
            if (location(record) === 0 && objectType(record) === EGG && x(record) === position.x
                && y(record) === position.y && z(record) === position.z) {
                result.push(i);
            }
        });
        return result;
    }

    // Кладёт яйцо с монстрами embryos [{obj, count, worktype}] на клетку position. Предметы на карте в файлах
    // игры отсортированы по y, затем x — яйцо встаёт на своё место (после предметов той же клетки).
    function addEgg(blocks, position, embryos, {chance = 100, quality = 2} = {}) {
        const name = blockName(position);
        check(blocks, name);
        if (!embryos.length || embryos.some(e => !(Number.isInteger(e.count) && e.count >= 1 && e.count <= 255))) {
            throw new Error('Количество монстров 1–255');
        }
        const records = parse(blocks.get(name));
        let index = records.findIndex(r => location(r) === 0
            && (y(r) > position.y || y(r) === position.y && x(r) > position.x));
        if (index < 0) {
            index = records.length;
        }
        const added = [mapRecord(0, position, EGG, {qty: chance, quality})];
        for (const {obj, count, worktype} of embryos) {
            const record = makeRecord(IN_CONTAINER, 0, obj, {qty: count, quality: worktype});
            setParent(record, index);
            record[3] = 0x7b;
            added.push(record);
        }
        insert(records, index, added);
        blocks.set(name, serialize(records));
        return name;
    }

    // Убирает яйца с клетки вместе с содержимым. Возвращает число убранных яиц.
    function removeEggs(blocks, position) {
        const name = blockName(position);
        check(blocks, name);
        const records = parse(blocks.get(name));
        const eggs = eggsAt(records, position);
        if (!eggs.length) {
            return 0;
        }
        const selected = new Set(eggs);
        records.forEach((record, i) => {
            if (location(record) === IN_CONTAINER && selected.has(parent(record))) {
                selected.add(i);
            }
        });
        blocks.set(name, serialize(split(records, selected)[0]));
        return eggs.length;
    }

    // Все яйца в файлах blocks: [{x, y, z, chance, quality, embryos: [{obj, count, worktype}]}].
    function eggs(blocks) {
        const result = [];
        for (const data of blocks.values()) {
            const records = parse(data);
            records.forEach((record, i) => {
                if (location(record) !== 0 || objectType(record) !== EGG) {
                    return;
                }
                const embryos = records.filter(r => location(r) === IN_CONTAINER && parent(r) === i)
                    .map(r => ({obj: objectType(r), count: r[6], worktype: r[7]}));
                result.push({x: x(record), y: y(record), z: z(record), chance: record[6], quality: record[7], embryos});
            });
        }
        return result;
    }

    const api = {blockName, parse, serialize, inventoryIndices, moveInventories, inventoryCount, addItem, addSpells, locks,
        EGG, addEgg, removeEggs, eggsAt, eggs};

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.Objblk = api;
    }
})(this);
