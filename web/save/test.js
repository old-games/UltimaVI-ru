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

console.log('objlist.js: OK');
