// Интерфейс редактора сохранений. Данные о NPC — npc.js (python3 -m tools.web_npc), формат — objlist.js.
'use strict';

const $ = id => document.getElementById(id);
const NPCS = window.NPC_DATA.npcs;
const NPC_BY_ID = new Map(NPCS.map(npc => [npc.id, npc]));
const FLAGS = window.NPC_DATA.flags;
const ITEMS = window.NPC_DATA.items;
const itemKey = (obj, frame = 0) => `${obj}:${frame}`;
const ITEM_BY_KEY = new Map(ITEMS.map(item => [itemKey(item.obj, item.frame), item]));
const SPELLS = window.NPC_DATA.spells;
const BOOKS = window.NPC_DATA.books;
const GOLD = 88;
const READABLE = new Set([151, 152]);   // книга, свиток: качество = номер текста + 1
const KEY = 64;
const REAGENTS = [65, 66, 67, 68, 69, 70, 71, 72];
const Z_NAMES = ['поверхность', 'подземелье 1', 'подземелье 2', 'подземелье 3', 'подземелье 4', 'мир горгулий'];

// cp866: только то, что встречается в именах отряда.
const CP866 = 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмноп' + '░'.repeat(48) + 'рстуфхцчшщъыьэюяЁё';

const state = {
    data: null,         // Uint8Array содержимого OBJLIST
    folder: null,       // FileSystemDirectoryHandle каталога SAVEGAME (Chrome/Edge)
    fileName: 'OBJLIST',
    blocks: null,       // Map имя → Uint8Array файлов OBJBLKxx (только при открытой папке)
    blockNames: null,   // Map имя в верхнем регистре → настоящее имя файла
    dirty: new Set(),   // какие OBJBLKxx изменены
    backedUp: new Set(),// для каких файлов уже сделан .BAK в этом сеансе
    selected: null,     // номер выбранного NPC
    item: null,         // ключ выбранного предмета (obj:frame)
    changes: [],
};

function decodeName(bytes) {
    return bytes.map(b => b < 0x80 ? String.fromCharCode(b) : CP866[b - 0x80] || '?').join('');
}

function npcName(id) {
    const npc = NPC_BY_ID.get(id);
    return npc ? npc.russian : `№${id}`;
}

function place({x, y, z}) {
    return `${x}, ${y}${z ? `, ${Z_NAMES[z] || 'этаж ' + z}` : ''}`;
}

function setStatus(text, error = false) {
    $('status').textContent = text;
    $('status').className = error ? 'error' : 'muted';
}

function addChange(text) {
    state.changes.push(text);
    renderChanges();
    setStatus(state.folder ? 'Есть несохранённые изменения — нажми «Сохранить».' : 'Есть изменения — нажми «Скачать OBJLIST».');
}

function guard(action) {
    try {
        action();
    } catch (error) {
        setStatus(error.message, true);
    }
}

// ---------- Открытие и сохранение ----------

async function findEntry(directory, name, kind) {
    for await (const entry of directory.values()) {
        if (entry.kind === kind && entry.name.toUpperCase() === name.toUpperCase()) {
            return entry;
        }
    }
    return null;
}

async function openFolder() {
    if (!window.showDirectoryPicker) {
        setStatus('Этот браузер не умеет открывать папки — выбери файл SAVEGAME/OBJLIST.', true);
        return;
    }
    await openFolderHandle(await window.showDirectoryPicker({mode: 'readwrite'}));
}

async function openFolderHandle(directory) {
    // Можно выбрать и саму папку игры, и SAVEGAME внутри неё.
    if (!await findEntry(directory, 'OBJLIST', 'file')) {
        const savegame = await findEntry(directory, 'SAVEGAME', 'directory');
        if (!savegame) {
            throw new Error(`В «${directory.name}» нет ни SAVEGAME, ни OBJLIST.`);
        }
        directory = savegame;
    }
    const handle = await findEntry(directory, 'OBJLIST', 'file');
    if (!handle) {
        throw new Error('В SAVEGAME нет файла OBJLIST — сохранись в игре.');
    }
    state.folder = directory;
    state.fileName = handle.name;
    state.blocks = new Map();
    state.blockNames = new Map();
    for await (const entry of directory.values()) {
        if (entry.kind === 'file' && /^OBJBLK[A-Z]{2}$/i.test(entry.name)) {
            const name = entry.name.toUpperCase();
            state.blocks.set(name, new Uint8Array(await (await entry.getFile()).arrayBuffer()));
            state.blockNames.set(name, entry.name);
        }
    }
    load(new Uint8Array(await (await handle.getFile()).arrayBuffer()), `${directory.name}/${handle.name}`);
}

async function openFile(file) {
    state.folder = null;
    state.blocks = null;
    state.fileName = file.name;
    load(new Uint8Array(await file.arrayBuffer()), file.name);
}

function load(data, source) {
    Objlist.check(data);
    state.data = data;
    state.dirty = new Set();
    state.backedUp = new Set();
    state.changes = [];
    state.selected = null;
    for (const id of ['save', 'restore']) {
        $(id).disabled = !state.folder;
    }
    for (const id of ['download', 'search', 'teleport', 'apply-time']) {
        $(id).disabled = false;
    }
    for (const id of ['give-member', 'item-search', 'give', 'give-gold', 'give-reagents', 'give-spells']) {
        $(id).disabled = !state.blocks;
    }
    $('item-list').classList.toggle('disabled', !state.blocks);
    renderAll();
    setStatus(`Открыто: ${source} (${data.length} байт).`);
}

async function writeFile(name, data) {
    const handle = await state.folder.getFileHandle(name, {create: true});
    const writable = await handle.createWritable();
    await writable.write(data);
    await writable.close();
}

// Перед первой записью файла в этом сеансе кладём рядом копию NAME.BAK.
async function writeWithBackup(name, data) {
    if (!state.backedUp.has(name)) {
        const original = await (await (await state.folder.getFileHandle(name)).getFile()).arrayBuffer();
        await writeFile(`${name}.BAK`, original);
        state.backedUp.add(name);
    }
    await writeFile(name, data);
}

async function save() {
    await writeWithBackup(state.fileName, state.data);
    for (const name of state.dirty) {
        await writeWithBackup(state.blockNames.get(name), state.blocks.get(name));
    }
    state.dirty = new Set();
    state.changes = [];
    renderChanges();
    setStatus('Сохранено. Копии до правок — файлы *.BAK в SAVEGAME. Запускай GAME.EXE.');
}

// Возвращает все файлы, для которых есть .BAK (OBJLIST и OBJBLKxx), и перечитывает папку.
async function restore() {
    const backups = [];
    for await (const entry of state.folder.values()) {
        if (entry.kind === 'file' && /\.BAK$/i.test(entry.name)) {
            backups.push(entry);
        }
    }
    if (!backups.some(entry => entry.name.toUpperCase() === 'OBJLIST.BAK')) {
        throw new Error('OBJLIST.BAK нет — нечего возвращать.');
    }
    for (const backup of backups) {
        await writeFile(backup.name.slice(0, -4), await (await backup.getFile()).arrayBuffer());
    }
    const folder = state.folder;
    await openFolderHandle(folder);
    setStatus(`Возвращено из копий: ${backups.map(entry => entry.name).join(', ')}.`);
}

function download() {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([state.data]));
    link.download = 'OBJLIST';
    link.click();
    URL.revokeObjectURL(link.href);
    setStatus('Положи скачанный OBJLIST в SAVEGAME игры вместо старого.');
}

// ---------- Отображение ----------

function renderAll() {
    renderParty();
    renderItems();
    renderNpcs();
    renderTime();
    renderFlags();
    renderChanges();
}

function renderParty() {
    const rows = Objlist.getParty(state.data).map(member => {
        const actor = Objlist.getActor(state.data, member.number);
        return `<tr><td>${member.number}</td><td>${decodeName(member.name)}</td><td>${place(actor)}</td></tr>`;
    });
    $('party').innerHTML = rows.join('');
}

function renderNpcs() {
    const query = $('search').value.trim().toLowerCase();
    const side = () => document.querySelector('input[name=side]:checked').value;
    const tbody = $('npcs');
    tbody.innerHTML = '';
    for (const npc of NPCS) {
        if (query && !`${npc.id} ${npc.russian} ${npc.english}`.toLowerCase().includes(query)) {
            continue;
        }
        const actor = Objlist.getActor(state.data, npc.id);
        const row = document.createElement('tr');
        row.className = 'npc' + (actor.present ? '' : ' absent') + (npc.id === state.selected ? ' selected' : '');
        row.innerHTML = `<td>${npc.id}</td><td>${npc.russian}</td><td>${npc.english}</td>`
            + `<td>${actor.present ? place(actor) : 'нет в мире'}</td><td></td>`;
        if (actor.present) {
            const button = document.createElement('button');
            button.textContent = 'Телепорт';
            button.onclick = event => {
                event.stopPropagation();
                guard(() => {
                    Objlist.teleportToActor(state.data, npc.id, side());
                    addChange(`Отряд перенесён к ${npc.russian} (${place(actor)})` + moveInventories());
                    renderParty();
                });
            };
            row.lastChild.append(button);
        }
        row.onclick = () => {
            state.selected = npc.id;
            renderNpcs();
            renderFlags();
        };
        tbody.append(row);
    }
}

function renderItems() {
    const members = Objlist.getParty(state.data);
    $('give-member').innerHTML = members
        .map(member => `<option value="${member.number}">${decodeName(member.name)}</option>`).join('');
    const query = $('item-search').value.trim().toLowerCase();
    const list = $('item-list');
    list.innerHTML = '';
    for (const item of ITEMS) {
        if (query && !`${item.obj} ${item.russian} ${item.english}`.toLowerCase().includes(query)) {
            continue;
        }
        const key = itemKey(item.obj, item.frame);
        const row = document.createElement('div');
        row.className = 'item' + (key === state.item ? ' selected' : '');
        const icon = document.createElement('span');
        icon.className = 'icon';
        icon.style.backgroundPosition = `-${item.icon % 32 * 32}px -${Math.floor(item.icon / 32) * 32}px`;
        const text = document.createElement('span');
        text.textContent = `${item.russian} — ${item.english} `
            + `(№${item.obj}${item.frame ? `, кадр ${item.frame}` : ''}${item.stackable ? ', стопка' : ''})`;
        row.append(icon, text);
        row.onclick = () => guard(() => {
            state.item = key;
            list.querySelectorAll('.selected').forEach(other => other.classList.remove('selected'));
            row.classList.add('selected');
            renderQualityHelper();
        });
        list.append(row);
    }
}

// Подсказка к полю «качество» для выбранного предмета.
function renderQualityHelper() {
    const item = ITEM_BY_KEY.get(state.item);
    const row = $('quality-helper-row');
    let options = [];
    if (item && READABLE.has(item.obj)) {
        $('quality-helper-label').textContent = 'Текст:';
        options = BOOKS.map(book => [book.quality, `${book.quality - 1}: ${book.russian} — ${book.english}`]);
    } else if (item && item.obj === KEY) {
        const actor = Number($('give-member').value);
        const position = Objlist.getPosition(state.data, actor);
        const file = Objblk.blockName(position);
        $('quality-helper-label').textContent = `Замки на участке ${file}:`;
        const distance = lock => Math.abs(lock.x - position.x) + Math.abs(lock.y - position.y);
        options = Objblk.locks(state.blocks.get(file))
            .filter(lock => lock.z === position.z)
            .sort((a, b) => distance(a) - distance(b))
            .map(lock => [lock.quality, `${lock.name} (${lock.x}, ${lock.y}), в ${distance(lock)} кл. — замок ${lock.quality}`]);
        if (!options.length) {
            options = [[0, 'на этом участке нет дверей и сундуков с замками']];
        }
    }
    row.classList.toggle('hidden', !options.length);
    $('quality-helper').innerHTML = options.map(([value, text]) => `<option value="${value}">${text}</option>`).join('');
    if (options.length) {
        $('item-quality').value = options[0][0];
    }
}

function renderTime() {
    const time = Objlist.getTime(state.data);
    for (const key of ['hour', 'minute', 'day', 'month', 'year']) {
        $(`t-${key}`).value = time[key];
    }
    $('karma').value = Objlist.getKarma(state.data);
}

function renderFlags() {
    if (state.selected === null) {
        $('flags-section').classList.add('hidden');
        return;
    }
    $('flags-section').classList.remove('hidden');
    const npc = NPC_BY_ID.get(state.selected);
    $('flags-npc').textContent = `${npc.russian} (${npc.english}, №${npc.id})`;
    const value = Objlist.getActor(state.data, npc.id).talkFlags;
    const usage = FLAGS[npc.id] || {};
    const container = $('flags');
    container.innerHTML = '';
    for (let bit = 0; bit < 8; bit++) {
        const label = document.createElement('label');
        const box = document.createElement('input');
        box.type = 'checkbox';
        box.checked = Boolean(value & 1 << bit);
        box.onchange = () => guard(() => {
            Objlist.setTalkFlag(state.data, npc.id, bit, box.checked);
            addChange(`${npc.russian}: бит ${bit} ${box.checked ? 'установлен' : 'сброшен'}`);
        });
        label.append(box, ` бит ${bit}`);
        const div = document.createElement('div');
        div.append(label);
        for (const use of usage[bit] || []) {
            const hint = document.createElement('div');
            hint.className = 'hint';
            hint.textContent = `${use.script}:${use.line} — ${use.operation}: ${use.text}`;
            div.append(hint);
        }
        if (!usage[bit]) {
            const hint = document.createElement('div');
            hint.className = 'hint';
            hint.textContent = 'в скриптах не используется';
            div.append(hint);
        }
        container.append(div);
    }
}

function renderChanges() {
    $('changes').innerHTML = state.changes.length
        ? state.changes.map(change => `<li>${change}</li>`).join('')
        : '<li class="muted">Пока нет.</li>';
}

// ---------- Действия ----------

function giveTarget() {
    const actor = Number($('give-member').value);
    return {actor, file: Objblk.blockName(Objlist.getPosition(state.data, actor)), name: $('give-member').selectedOptions[0].textContent};
}

function give(key, qty) {
    const {actor, file, name} = giveTarget();
    const item = ITEM_BY_KEY.get(key);
    if (!item) {
        throw new Error('Выбери предмет в списке.');
    }
    if (!(Number.isInteger(qty) && qty >= 1)) {
        throw new Error('Количество — целое число от 1.');
    }
    const {obj, frame} = item;
    const quality = Number($('item-quality').value);
    if (!item.stackable && !(Number.isInteger(quality) && quality >= 0 && quality <= 255)) {
        throw new Error('Качество — от 0 до 255.');
    }
    if (item.stackable) {
        Objblk.addItem(state.blocks, file, actor, {obj, frame, qty, stackable: true});
    } else {
        if (qty > 50) {
            throw new Error('Нескладываемых предметов — не больше 50 за раз.');
        }
        for (let i = 0; i < qty; i++) {
            Objblk.addItem(state.blocks, file, actor, {obj, frame, quality});
        }
    }
    state.dirty.add(file);
    return `${name}: ${item.russian} ×${qty}` + (!item.stackable && quality ? `, качество ${quality}` : '');
}

function giveSpells() {
    const {actor, file, name} = giveTarget();
    const before = new Map(state.blocks);
    const added = Objblk.addSpells(state.blocks, file, actor, SPELLS.map(spell => spell.number));
    for (const [block, data] of state.blocks) {
        if (data !== before.get(block)) {
            state.dirty.add(block);     // книга могла лежать в другом файле
        }
    }
    return `${name}: книга заклинаний, добавлено заклинаний — ${added}`;
}

// Вещи отряда лежат в файле участка, где стоит персонаж; игра грузит только участки рядом с отрядом.
// После телепорта переносим инвентарь каждого члена отряда в файл его нового участка.
function moveInventories() {
    if (!state.blocks) {
        return ' — вещи отряда остались на старом месте: чтобы перенести и их, открой папку игры в Chrome/Edge';
    }
    let count = 0;
    for (const member of Objlist.getParty(state.data)) {
        const target = Objblk.blockName(Objlist.getPosition(state.data, member.number));
        const result = Objblk.moveInventories(state.blocks, [member.number], target);
        result.changed.forEach(name => state.dirty.add(name));
        count += result.count;
    }
    return count ? `, вещи отряда (${count}) перенесены` : '';
}

function teleportToCoordinates() {
    const target = {x: Number($('tp-x').value), y: Number($('tp-y').value), z: Number($('tp-z').value)};
    if (!Number.isInteger(target.x) || !Number.isInteger(target.y) || !Number.isInteger(target.z)) {
        throw new Error('Укажи x, y и этаж целыми числами.');
    }
    Objlist.teleportParty(state.data, target, 'here');
    addChange(`Отряд перенесён в ${place(target)}` + moveInventories());
    renderParty();
}

function applyTime() {
    const time = {};
    for (const key of ['hour', 'minute', 'day', 'month', 'year']) {
        time[key] = Number($(`t-${key}`).value);
    }
    Objlist.setTime(state.data, time);
    const karma = Number($('karma').value);
    Objlist.setKarma(state.data, karma);
    addChange(`Время ${time.hour}:${String(time.minute).padStart(2, '0')}, ${time.day}.${time.month}.${time.year}, карма ${karma}`);
}

const async_ = action => () => action().catch(error => {
    if (error.name !== 'AbortError') {
        setStatus(error.message, true);
    }
});

$('open-folder').onclick = async_(openFolder);
$('open-file').onchange = event => event.target.files[0] && async_(() => openFile(event.target.files[0]))();
$('save').onclick = async_(save);
$('restore').onclick = async_(restore);
$('download').onclick = () => guard(download);
$('search').oninput = () => renderNpcs();
$('teleport').onclick = () => guard(teleportToCoordinates);
$('apply-time').onclick = () => guard(applyTime);
$('item-search').oninput = () => renderItems();
$('give-member').onchange = () => guard(renderQualityHelper);
$('quality-helper').onchange = () => { $('item-quality').value = $('quality-helper').value; };
$('give').onclick = () => guard(() => addChange(give(state.item, Number($('item-qty').value))));
$('give-gold').onclick = () => guard(() => addChange(give(itemKey(GOLD), 5000)));     // стопки, качество не важно
$('give-reagents').onclick = () => guard(() => addChange(REAGENTS.map(obj => give(itemKey(obj), 20)).join('; ')));
$('give-spells').onclick = () => guard(() => addChange(giveSpells()));
