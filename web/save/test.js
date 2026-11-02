// Тест objlist.js: node web/save/test.js (из корня репозитория).
// Образец — шаблон SAVEGAME/OBJLIST в конце распакованного LZDNGBLK (см. tools/party.py).
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Objlist = require('./objlist.js');

const root = path.join(__dirname, '..', '..');
const template = new Uint8Array(fs.readFileSync(path.join(root, 'unpacked', 'LZDNGBLK')).subarray(0xf1ea));
const copy = () => new Uint8Array(template);

// Начальное состояние новой игры: отряд в замке Лорда Бритиша.
{
    const data = copy();
    assert.deepStrictEqual(Objlist.getParty(data).map(m => m.number), [1, 2, 3, 4]);
    assert.deepStrictEqual(Objlist.getPosition(data, 1), {x: 307, y: 352, z: 0});
    assert.deepStrictEqual(Objlist.getPosition(data, 5), {x: 307, y: 348, z: 0});   // Лорд Бритиш
    assert.deepStrictEqual(Objlist.getTime(data), {minute: 0, hour: 8, day: 4, month: 7, year: 161});
    assert.strictEqual(Objlist.getKarma(data), 75);
}

// Запись и чтение координат во всём диапазоне не задевают соседей.
{
    const data = copy();
    for (const position of [{x: 0, y: 0, z: 0}, {x: 1023, y: 1023, z: 0}, {x: 255, y: 255, z: 5}, {x: 513, y: 77, z: 0}]) {
        Objlist.setPosition(data, 10, position);
        assert.deepStrictEqual(Objlist.getPosition(data, 10), position);
    }
    assert.deepStrictEqual(Objlist.getPosition(data, 9), Objlist.getPosition(template, 9));
    assert.deepStrictEqual(Objlist.getPosition(data, 11), Objlist.getPosition(template, 11));
    assert.throws(() => Objlist.setPosition(data, 10, {x: 300, y: 0, z: 1}));
}

// Телепорт к NPC: весь отряд рядом с ним, больше ничего не меняется.
{
    const data = copy();
    const target = Objlist.getPosition(data, 6);
    Objlist.teleportToActor(data, 6, 'east');
    assert.deepStrictEqual(Objlist.getPosition(data, 1), {x: target.x + 1, y: target.y, z: target.z});
    const changed = [];
    data.forEach((byte, i) => byte !== template[i] && changed.push(i));
    const party = [1, 2, 3, 4].flatMap(n => [0x100 + n * 3, 0x101 + n * 3, 0x102 + n * 3]);
    assert(changed.every(i => party.includes(i)), `лишние изменения: ${changed.map(i => i.toString(16))}`);
}

// Время, карма, флаги разговора.
{
    const data = copy();
    Objlist.setTime(data, {minute: 30, hour: 23, day: 28, month: 12, year: 300});
    assert.deepStrictEqual(Objlist.getTime(data), {minute: 30, hour: 23, day: 28, month: 12, year: 300});
    assert.throws(() => Objlist.setTime(data, {minute: 0, hour: 24, day: 1, month: 1, year: 1}));
    Objlist.setKarma(data, 99);
    assert.strictEqual(Objlist.getKarma(data), 99);
    Objlist.setTalkFlag(data, 5, 7, true);
    Objlist.setTalkFlag(data, 5, 0, true);
    assert.strictEqual(Objlist.getActor(data, 5).talkFlags, 0x81);
    Objlist.setTalkFlag(data, 5, 7, false);
    assert.strictEqual(Objlist.getActor(data, 5).talkFlags, 0x01);
}

// Перенос инвентаря отряда между файлами участков (блоки из LZOBJBLK: 20 — участок замка с вещами отряда).
{
    const Objblk = require('./objblk.js');
    const raw = fs.readFileSync(path.join(root, 'unpacked', 'LZOBJBLK'));
    const blocks = [];
    for (let p = 0; p < raw.length;) {
        const count = raw[p] | raw[p + 1] << 8;
        blocks.push(new Uint8Array(raw.subarray(p, p + 2 + count * 8)));
        p += 2 + count * 8;
    }
    const map = new Map([['OBJBLKCC', blocks[20]], ['OBJBLKEH', blocks[37]], ['OBJBLKAA', blocks[0]]]);
    const party = [1, 2, 3, 4];
    const before = new Map([...map].map(([name, data]) => [name, Objblk.parse(data)]));
    assert.deepStrictEqual([...Objblk.inventoryCount(map, party)], [['OBJBLKCC', 43]]);
    assert.strictEqual(Objblk.blockName({x: 307, y: 352, z: 0}), 'OBJBLKCC');
    assert.strictEqual(Objblk.blockName({x: 570, y: 948, z: 0}), 'OBJBLKEH');
    assert.strictEqual(Objblk.blockName({x: 10, y: 10, z: 3}), 'OBJBLKCI');

    const result = Objblk.moveInventories(map, party, 'OBJBLKEH');
    assert.deepStrictEqual(result, {changed: ['OBJBLKCC', 'OBJBLKEH'], count: 43});
    assert.deepStrictEqual([...Objblk.inventoryCount(map, party)], [['OBJBLKEH', 43]]);
    assert.deepStrictEqual(map.get('OBJBLKAA'), blocks[0]);

    // Ничего не потерялось и не задвоилось; ссылки на контейнеры ведут на те же предметы.
    const describe = (records, i, seen = 0) => {
        const r = records[i];
        const own = Array.from(r.slice(3)).join(',') + ':' + (r[0] & 0x18);
        if ((r[0] & 0x18) !== 0x08) {
            return own + '@' + (r[1] | (r[2] & 3) << 8);
        }
        assert(seen < 10);
        const parentIndex = r[1] | (r[2] & 3) << 8 | (r[2] >> 2 & 0x3f) << 10;
        assert(parentIndex < i, 'контейнер должен идти раньше содержимого');
        return own + ' in ' + describe(records, parentIndex, seen + 1);
    };
    const all = records => records.map((_, i) => describe(records, i)).sort();
    const beforeAll = [...all(before.get('OBJBLKCC')), ...all(before.get('OBJBLKEH'))].sort();
    const after = new Map([...map].map(([name, data]) => [name, Objblk.parse(data)]));
    assert.deepStrictEqual([...all(after.get('OBJBLKCC')), ...all(after.get('OBJBLKEH'))].sort(), beforeAll);
    assert.strictEqual(after.get('OBJBLKCC').length + 43, before.get('OBJBLKCC').length);
}

// Выдача предметов и заклинаний.
{
    const Objblk = require('./objblk.js');
    const raw = fs.readFileSync(path.join(root, 'unpacked', 'LZOBJBLK'));
    const count = raw[0] | raw[1] << 8;
    const map = new Map([['OBJBLKAA', new Uint8Array(raw.subarray(0, 2 + count * 8))], ['OBJBLKCC', Objblk.serialize([])]]);
    const records = () => Objblk.parse(map.get('OBJBLKCC'));
    const type = r => r[4] | (r[5] & 3) << 8;

    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 88, qty: 5000, stackable: true});
    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 88, qty: 300, stackable: true});
    assert.strictEqual(records().length, 1);
    assert.strictEqual(records()[0][6] | records()[0][7] << 8, 5300);
    assert.strictEqual(Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 88, qty: 65000, stackable: true}), 65535);
    Objblk.addItem(map, 'OBJBLKCC', 2, {obj: 88, qty: 7, stackable: true});     // у другого персонажа — своя стопка
    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 43});
    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 43});
    assert.strictEqual(records().filter(r => type(r) === 43).length, 2);
    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 77, frame: 2, qty: 3, stackable: true});     // стопки разных вариантов
    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 77, frame: 3, qty: 4, stackable: true});     // не смешиваются
    Objblk.addItem(map, 'OBJBLKCC', 1, {obj: 77, frame: 2, qty: 5, stackable: true});
    assert.deepStrictEqual(records().filter(r => type(r) === 77).map(r => [r[5] >> 2, r[6]]), [[2, 8], [3, 4]]);

    assert.strictEqual(Objblk.addSpells(map, 'OBJBLKCC', 1, [0, 1, 16]), 3);
    assert.strictEqual(Objblk.addSpells(map, 'OBJBLKCC', 1, [1, 16, 17]), 1);
    const book = records().findIndex(r => type(r) === 57);
    assert.strictEqual(records()[book][0] & 0x18, 0x18, 'книга должна быть в руке');
    const spells = records().filter(r => type(r) === 58);
    assert.deepStrictEqual(spells.map(r => r[7]).sort((a, b) => a - b), [0, 1, 16, 17]);
    assert(spells.every(r => (r[0] & 0x18) === 0x08 && (r[1] | (r[2] & 3) << 8 | (r[2] >> 2 & 0x3f) << 10) === book));
    assert.deepStrictEqual([...Objblk.inventoryCount(map, [1])], [['OBJBLKCC', 10]]);

    // Книга с текстом и ключ к замку: качество сохраняется.
    Objblk.addItem(map, 'OBJBLKCC', 2, {obj: 151, quality: 7});
    Objblk.addItem(map, 'OBJBLKCC', 2, {obj: 64, quality: 14});
    assert.deepStrictEqual(records().filter(r => type(r) === 151 || type(r) === 64).map(r => [type(r), r[7]]), [[151, 7], [64, 14]]);

    // Замки на участке замка (блок 20 из LZOBJBLK).
    const castle = raw;
    let p = 0;
    for (let i = 0; i < 20; i++) {
        p += 2 + (castle[p] | castle[p + 1] << 8) * 8;
    }
    const block = castle.subarray(p, p + 2 + (castle[p] | castle[p + 1] << 8) * 8);
    assert.deepStrictEqual(Objblk.locks(block).map(lock => [lock.obj, lock.x, lock.y, lock.quality]),
        [[297, 296, 357, 14], [300, 304, 382, 1], [300, 311, 382, 1]]);
}

// Архив для Firefox и Safari: эталонная CRC-32 и разбор собственного zip.
{
    const Zip = require('./zip.js');
    assert.strictEqual(Zip.crc32(Buffer.from('123456789')), 0xcbf43926);
    const files = [{name: 'OBJLIST', data: copy()}, {name: 'OBJBLKCC', data: Uint8Array.of(1, 2, 3)}];
    const zip = Buffer.from(Zip.makeZip(files));
    const end = zip.length - 22;
    assert.strictEqual(zip.readUInt32LE(end), 0x06054b50);
    assert.strictEqual(zip.readUInt16LE(end + 10), 2);
    let offset = zip.readUInt32LE(end + 16);
    for (const file of files) {
        assert.strictEqual(zip.readUInt32LE(offset), 0x02014b50);
        const nameLength = zip.readUInt16LE(offset + 28);
        assert.strictEqual(zip.toString('ascii', offset + 46, offset + 46 + nameLength), file.name);
        const local = zip.readUInt32LE(offset + 42);
        const start = local + 30 + zip.readUInt16LE(local + 26);
        assert.deepStrictEqual(new Uint8Array(zip.subarray(start, start + zip.readUInt32LE(local + 18))), file.data);
        assert.strictEqual(zip.readUInt32LE(local + 14), Zip.crc32(file.data));
        offset += 46 + nameLength;
    }
}

console.log('objlist.js, objblk.js, zip.js: OK');
