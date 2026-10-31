// Чтение и правка сохранения Ultima VI (SAVEGAME/OBJLIST).
// Смещения сверены с движком Nuvie (ScummVM, engines/ultima/nuvie/save/obj_list.h, actors/actor_manager.cpp).
// Обычный скрипт без import/export: страница должна открываться из файла (file://), а тесты подключают его из Node.

(function (root) {
    'use strict';

    const ACTORS = 256;
    const TEMP_ACTORS = 203;            // с этого номера — временные персонажи (монстры)
    const POSITIONS = 0x100;            // 256 × 3 байта: x 10 бит, y 10 бит, z 4 бита
    const OBJECTS = 0x400;              // 256 × 2 байта: тип 10 бит, кадр 6 бит; 0 — персонажа нет
    const PARTY_NAMES = 0xf00;          // 16 × 14 байт
    const PARTY_ROSTER = 0xfe0;         // 16 байт, номера персонажей
    const PARTY_SIZE = 0xff0;
    const TALK_FLAGS = 0x17f1;          // 256 байт, setBit/hasBit в диалогах
    const GAME_TIME = 0x1bf3;           // минута, час, день, месяц, год (2 байта)
    const KARMA = 0x1bf9;
    const SIZE = 0x1c72;                // минимальный размер, до последнего поля, которое мы знаем

    // Размер карты по этажам: 0 — поверхность 1024×1024, 1–5 — подземелья и мир горгулий 256×256.
    function mapSize(z) {
        return z === 0 ? 1024 : 256;
    }

    function check(data) {
        if (!(data instanceof Uint8Array) || data.length < SIZE) {
            throw new Error(`Это не похоже на SAVEGAME/OBJLIST: ${data && data.length} байт, ожидалось не меньше ${SIZE}`);
        }
    }

    function getPosition(data, actor) {
        const o = POSITIONS + actor * 3;
        return {
            x: data[o] | (data[o + 1] & 0x3) << 8,
            y: data[o + 1] >> 2 | (data[o + 2] & 0xf) << 6,
            z: data[o + 2] >> 4,
        };
    }

    function setPosition(data, actor, {x, y, z}) {
        const size = mapSize(z);
        if (!(z >= 0 && z <= 5 && x >= 0 && x < size && y >= 0 && y < size)) {
            throw new Error(`Координаты вне карты: ${x}, ${y}, этаж ${z}`);
        }
        const o = POSITIONS + actor * 3;
        data[o] = x & 0xff;
        data[o + 1] = x >> 8 & 0x3 | (y & 0x3f) << 2;
        data[o + 2] = y >> 6 & 0xf | z << 4;
    }

    function getActor(data, actor) {
        const o = OBJECTS + actor * 2;
        return {
            number: actor,
            ...getPosition(data, actor),
            object: data[o] | (data[o + 1] & 0x3) << 8,
            present: (data[o] | data[o + 1] << 8) !== 0,
            talkFlags: data[TALK_FLAGS + actor],
        };
    }

    function getActors(data) {
        check(data);
        const result = [];
        for (let i = 1; i < TEMP_ACTORS; i++) {
            result.push(getActor(data, i));
        }
        return result;
    }

    function getParty(data) {
        check(data);
        const size = data[PARTY_SIZE];
        const members = [];
        for (let i = 0; i < size && i < 16; i++) {
            const name = data.slice(PARTY_NAMES + i * 14, PARTY_NAMES + i * 14 + 14);
            const end = name.indexOf(0);
            members.push({
                number: data[PARTY_ROSTER + i],
                name: Array.from(end < 0 ? name : name.slice(0, end)),   // байты в cp866
            });
        }
        return members;
    }

    // Клетки вокруг цели: первая — рядом с NPC с выбранной стороны, дальше — для остальных членов отряда.
    const SIDES = {
        south: [[0, 1], [-1, 2], [1, 2], [0, 2], [-1, 3], [1, 3], [0, 3], [-2, 3]],
        north: [[0, -1], [-1, -2], [1, -2], [0, -2], [-1, -3], [1, -3], [0, -3], [-2, -3]],
        east: [[1, 0], [2, -1], [2, 1], [2, 0], [3, -1], [3, 1], [3, 0], [3, -2]],
        west: [[-1, 0], [-2, -1], [-2, 1], [-2, 0], [-3, -1], [-3, 1], [-3, 0], [-3, -2]],
        here: [[0, 0], [-1, 1], [1, 1], [0, 1], [-1, 2], [1, 2], [0, 2], [-2, 2]],
    };

    // Переносит весь отряд к точке (x, y, z). side — с какой стороны встать (для NPC), here — ровно в точку.
    function teleportParty(data, {x, y, z}, side = 'south') {
        check(data);
        const offsets = SIDES[side];
        if (!offsets) {
            throw new Error(`Неизвестная сторона: ${side}`);
        }
        const size = mapSize(z);
        const party = getParty(data);
        party.forEach((member, i) => {
            const [dx, dy] = offsets[Math.min(i, offsets.length - 1)];
            setPosition(data, member.number, {
                x: Math.min(Math.max(x + dx, 0), size - 1),
                y: Math.min(Math.max(y + dy, 0), size - 1),
                z,
            });
        });
        return party.map(member => ({number: member.number, ...getPosition(data, member.number)}));
    }

    function teleportToActor(data, actor, side = 'south') {
        const target = getActor(data, actor);
        if (!target.present) {
            throw new Error(`Персонажа ${actor} сейчас нет в мире`);
        }
        return teleportParty(data, target, side);
    }

    function getTime(data) {
        check(data);
        const o = GAME_TIME;
        return {
            minute: data[o], hour: data[o + 1], day: data[o + 2], month: data[o + 3],
            year: data[o + 4] | data[o + 5] << 8,
        };
    }

    function setTime(data, {minute, hour, day, month, year}) {
        check(data);
        const fields = {minute: [minute, 0, 59], hour: [hour, 0, 23], day: [day, 1, 28], month: [month, 1, 12], year: [year, 0, 65535]};
        for (const [name, [value, min, max]] of Object.entries(fields)) {
            if (!(Number.isInteger(value) && value >= min && value <= max)) {
                throw new Error(`Неверное значение ${name}: ${value} (допустимо ${min}–${max})`);
            }
        }
        const o = GAME_TIME;
        data[o] = minute;
        data[o + 1] = hour;
        data[o + 2] = day;
        data[o + 3] = month;
        data[o + 4] = year & 0xff;
        data[o + 5] = year >> 8;
    }

    function getKarma(data) {
        check(data);
        return data[KARMA];
    }

    function setKarma(data, karma) {
        check(data);
        if (!(Number.isInteger(karma) && karma >= 0 && karma <= 99)) {
            throw new Error(`Карма должна быть от 0 до 99: ${karma}`);
        }
        data[KARMA] = karma;
    }

    function setTalkFlag(data, actor, bit, value) {
        check(data);
        if (!(bit >= 0 && bit < 8)) {
            throw new Error(`Номер бита 0–7: ${bit}`);
        }
        const o = TALK_FLAGS + actor;
        data[o] = value ? data[o] | 1 << bit : data[o] & ~(1 << bit);
    }

    const api = {
        ACTORS, TEMP_ACTORS, SIDES, mapSize, check,
        getActor, getActors, getParty, getPosition, setPosition,
        teleportParty, teleportToActor, getTime, setTime, getKarma, setKarma, setTalkFlag,
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.Objlist = api;
    }
})(this);
