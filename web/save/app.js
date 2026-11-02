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
// Карты web/save/maps/ (tools/web_npc.py): 4 пикселя на клетку, куски 1024×1024 = 256×256 клеток,
// поверхность — 4×4 куска (1024 клетки), подземелья и мир горгулий — один кусок (256 клеток).
const MAP_PIECE = 256;
const mapTiles = level => level === 0 ? 1024 : 256;
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
    pick: null,         // выбранная на карте клетка {x, y, z}
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
    setStatus(state.folder ? 'Есть несохранённые изменения — нажми «Сохранить».'
        : `Есть изменения — нажми «${downloadLabel()}».`);
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
        // Firefox и Safari: папку можно только прочитать, изменённые файлы отдаём архивом.
        $('open-folder-input').click();
        return;
    }
    await openFolderHandle(await window.showDirectoryPicker({mode: 'readwrite'}));
}

// Папка, выбранная через <input webkitdirectory>: список файлов с путями от выбранной папки.
async function openFolderFiles(files) {
    files = Array.from(files);
    const objlists = files.filter(file => file.name.toUpperCase() === 'OBJLIST');
    // Если выбрана папка игры, OBJLIST лежит в SAVEGAME; берём тот, у которого путь короче всего.
    const depth = file => file.webkitRelativePath.split('/').length;
    const objlist = objlists.sort((a, b) => depth(a) - depth(b))[0];
    if (!objlist) {
        throw new Error('В выбранной папке нет SAVEGAME/OBJLIST — выбери папку игры или SAVEGAME.');
    }
    const directory = objlist.webkitRelativePath.split('/').slice(0, -1).join('/');
    state.folder = null;
    state.fileName = objlist.name;
    state.blocks = new Map();
    state.blockNames = new Map();
    for (const file of files) {
        const parent = file.webkitRelativePath.split('/').slice(0, -1).join('/');
        if (parent === directory && /^OBJBLK[A-Z]{2}$/i.test(file.name)) {
            const name = file.name.toUpperCase();
            state.blocks.set(name, new Uint8Array(await file.arrayBuffer()));
            state.blockNames.set(name, file.name);
        }
    }
    if (!state.blocks.size) {
        throw new Error(`Рядом с ${objlist.webkitRelativePath} нет файлов OBJBLKxx.`);
    }
    load(new Uint8Array(await objlist.arrayBuffer()), `${objlist.webkitRelativePath || objlist.name} (только чтение)`);
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
    $('download').textContent = downloadLabel();
    for (const id of ['give-member', 'item-search', 'give', 'give-gold', 'give-reagents', 'give-spells']) {
        $(id).disabled = !state.blocks;
    }
    $('item-list').classList.toggle('disabled', !state.blocks);
    renderAll();
    showParty();
    $('map-teleport').disabled = !state.pick;
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

function downloadLabel() {
    return state.blocks && !state.folder ? 'Скачать изменённые файлы (SAVEGAME.zip)' : 'Скачать OBJLIST';
}

function saveAs(data, name) {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([data]));
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function download() {
    if (state.blocks && !state.folder) {
        const files = [{name: state.fileName, data: state.data}];
        for (const name of [...state.dirty].sort()) {
            files.push({name: state.blockNames.get(name), data: state.blocks.get(name)});
        }
        saveAs(Zip.makeZip(files), 'SAVEGAME.zip');
        setStatus(`Распакуй SAVEGAME.zip в папку SAVEGAME игры с заменой файлов: ${files.map(f => f.name).join(', ')}.`);
    } else {
        saveAs(state.data, 'OBJLIST');
        setStatus('Положи скачанный OBJLIST в SAVEGAME игры вместо старого.');
    }
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

// ---------- Карта ----------

function mapLevel() {
    return Number($('map-level').value);
}

function mapZoom() {
    return Number($('map-zoom').value);
}

function renderMap() {
    const level = mapLevel();
    const zoom = mapZoom();
    const tiles = mapTiles(level);
    const canvas = $('map-canvas');
    canvas.innerHTML = '';
    canvas.style.width = canvas.style.height = `${tiles * zoom}px`;
    canvas.classList.toggle('pixelated', zoom >= 4);
    const pieces = tiles / MAP_PIECE;
    for (let row = 0; row < pieces; row++) {
        for (let column = 0; column < pieces; column++) {
            const image = document.createElement('img');
            image.src = `maps/${level}_${row}_${column}.webp`;
            image.style.left = `${column * MAP_PIECE * zoom}px`;
            image.style.top = `${row * MAP_PIECE * zoom}px`;
            image.style.width = image.style.height = `${MAP_PIECE * zoom}px`;
            image.draggable = false;
            image.onerror = () => $('map-missing').classList.remove('hidden');
            canvas.append(image);
        }
    }
    renderMapMarkers();
}

function addMarker(className, {x, y}, size, title) {
    const zoom = mapZoom();
    const marker = document.createElement('div');
    marker.className = `marker ${className}`;
    marker.style.left = `${(x + 0.5) * zoom}px`;
    marker.style.top = `${(y + 0.5) * zoom}px`;
    if (size) {
        marker.style.width = marker.style.height = `${size}px`;
    }
    if (title) {
        marker.title = title;
    }
    $('map-canvas').append(marker);
    return marker;
}

function renderMapMarkers() {
    const canvas = $('map-canvas');
    canvas.querySelectorAll('.marker, .map-label').forEach(marker => marker.remove());
    const labels = $('map-labels').checked && mapZoom() >= 3;
    const level = mapLevel();
    const size = Math.max(6, mapZoom() + 2);
    if (state.data) {
        for (const npc of NPCS) {
            const actor = Objlist.getActor(state.data, npc.id);
            if (!actor.present || actor.z !== level) {
                continue;
            }
            const marker = addMarker(`npc${npc.id === state.selected ? ' selected' : ''}`, actor, size,
                `${npc.russian} (${npc.english}, №${npc.id}) — ${actor.x}, ${actor.y}`);
            marker.onclick = event => {
                event.stopPropagation();
                if (!(drag && drag.moved)) {
                    guard(() => teleportToNpc(npc));
                }
            };
            if (labels) {
                const label = document.createElement('div');
                label.className = `map-label${npc.id === state.selected ? ' selected' : ''}`;
                label.textContent = npc.russian;
                label.style.left = `${(actor.x + 0.5) * mapZoom()}px`;
                label.style.top = `${(actor.y + 0.5) * mapZoom()}px`;
                canvas.append(label);
            }
        }
        for (const member of Objlist.getParty(state.data)) {
            const actor = Objlist.getActor(state.data, member.number);
            if (actor.z === level) {
                addMarker('party', actor, size + 2);
            }
        }
    }
    if (state.pick && state.pick.z === level) {
        addMarker('pick', state.pick);
    }
}

function mapCell(event) {
    const rect = $('map-canvas').getBoundingClientRect();
    const zoom = mapZoom();
    const tiles = mapTiles(mapLevel());
    const x = Math.floor((event.clientX - rect.left) / zoom);
    const y = Math.floor((event.clientY - rect.top) / zoom);
    return x >= 0 && y >= 0 && x < tiles && y < tiles ? {x, y, z: mapLevel()} : null;
}

function centerMap({x, y}) {
    const view = $('map-view');
    const zoom = mapZoom();
    view.scrollLeft = x * zoom - view.clientWidth / 2;
    view.scrollTop = y * zoom - view.clientHeight / 2;
}

function showParty() {
    if (!state.data) {
        return;
    }
    const avatar = Objlist.getActor(state.data, Objlist.getParty(state.data)[0].number);
    if (mapLevel() !== avatar.z) {
        $('map-level').value = avatar.z;
        renderMap();
    }
    centerMap(avatar);
}

function teleportToNpc(npc) {
    const side = document.querySelector('input[name=side]:checked').value;
    const actor = Objlist.getActor(state.data, npc.id);
    Objlist.teleportToActor(state.data, npc.id, side);
    addChange(`Отряд перенесён к ${npc.russian} (${place(actor)})` + moveInventories());
    renderParty();
}

function renderParty() {
    const rows = Objlist.getParty(state.data).map(member => {
        const actor = Objlist.getActor(state.data, member.number);
        return `<tr><td>${member.number}</td><td>${decodeName(member.name)}</td><td>${place(actor)}</td></tr>`;
    });
    $('party').innerHTML = rows.join('');
    renderMapMarkers();
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
                guard(() => teleportToNpc(npc));
            };
            row.lastChild.append(button);
        }
        row.onclick = () => {
            state.selected = npc.id;
            renderNpcs();
            renderFlags();
            renderMapMarkers();
            if (actor.present) {
                $('map-level').value = actor.z;
                renderMap();
                centerMap(actor);
            }
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
        return ' — вещи отряда остались на старом месте: чтобы перенести и их, открой папку игры, а не один файл';
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
$('open-folder-input').onchange = event => event.target.files.length
    && async_(() => openFolderFiles(event.target.files))();
$('open-file').onchange = event => event.target.files[0] && async_(() => openFile(event.target.files[0]))();
$('save').onclick = async_(save);
$('restore').onclick = async_(restore);
$('download').onclick = () => guard(download);
$('search').oninput = () => renderNpcs();
$('teleport').onclick = () => guard(teleportToCoordinates);
$('apply-time').onclick = () => guard(applyTime);
$('map-level').onchange = () => { renderMap(); showPartyIfHere(); };
// Меняет масштаб, оставляя на месте точку карты под (offsetX, offsetY) — координатами внутри окна карты.
function setMapZoom(zoom, offsetX, offsetY) {
    const view = $('map-view');
    offsetX = offsetX ?? view.clientWidth / 2;
    offsetY = offsetY ?? view.clientHeight / 2;
    const old = mapZoom();
    const point = {x: (view.scrollLeft + offsetX) / old, y: (view.scrollTop + offsetY) / old};
    $('map-zoom').value = String(zoom);
    renderMap();
    view.scrollLeft = point.x * zoom - offsetX;
    view.scrollTop = point.y * zoom - offsetY;
}

$('map-zoom').onchange = () => {
    // В select уже новое значение: старый масштаб берём из размера карты.
    const zoom = mapZoom();
    const old = Number($('map-canvas').style.width.replace('px', '')) / mapTiles(mapLevel()) || zoom;
    $('map-zoom').value = String(old);
    setMapZoom(zoom);
};

// Колесо мыши — масштаб; прокрутку копим, чтобы тачпад не перескакивал через уровни.
let wheel = 0;
$('map-view').addEventListener('wheel', event => {
    event.preventDefault();
    wheel += event.deltaMode === 1 ? event.deltaY * 40 : event.deltaY;
    if (Math.abs(wheel) < 60) {
        return;
    }
    const zooms = [...$('map-zoom').options].map(option => Number(option.value));
    const index = zooms.indexOf(mapZoom()) + (wheel < 0 ? 1 : -1);
    wheel = 0;
    if (index < 0 || index >= zooms.length) {
        return;
    }
    const rect = $('map-view').getBoundingClientRect();
    setMapZoom(zooms[index], event.clientX - rect.left, event.clientY - rect.top);
}, {passive: false});

// Перетаскивание — сдвиг карты; короткий клик без сдвига выбирает клетку.
let drag = null;
$('map-canvas').addEventListener('mousedown', event => {
    if (event.button === 0) {
        drag = {x: event.clientX, y: event.clientY, left: $('map-view').scrollLeft, top: $('map-view').scrollTop, moved: false};
        event.preventDefault();
    }
});
window.addEventListener('mousemove', event => {
    if (!drag) {
        return;
    }
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.moved && Math.hypot(dx, dy) > 4) {
        drag.moved = true;
        $('map-canvas').classList.add('dragging');
    }
    if (drag.moved) {
        $('map-view').scrollLeft = drag.left - dx;
        $('map-view').scrollTop = drag.top - dy;
    }
});
window.addEventListener('mouseup', () => {
    if (drag && drag.moved) {
        // клик после перетаскивания не должен выбирать клетку
        setTimeout(() => { drag = null; }, 0);
    } else {
        drag = null;
    }
    $('map-canvas').classList.remove('dragging');
});
$('map-party').onclick = () => guard(showParty);
$('map-labels').onchange = () => renderMapMarkers();
$('map-canvas').onmousemove = event => {
    const cell = mapCell(event);
    $('map-hover').textContent = cell ? `${cell.x}, ${cell.y}` : '—';
};
$('map-canvas').onclick = event => {
    if (drag && drag.moved) {
        return;
    }
    const cell = mapCell(event);
    if (!cell) {
        return;
    }
    state.pick = cell;
    $('map-pick').textContent = place(cell);
    $('tp-x').value = cell.x;
    $('tp-y').value = cell.y;
    $('tp-z').value = cell.z;
    $('map-teleport').disabled = !state.data;
    renderMapMarkers();
};
$('map-teleport').onclick = () => guard(() => {
    Objlist.teleportParty(state.data, state.pick, 'here');
    addChange(`Отряд перенесён в ${place(state.pick)}` + moveInventories());
    renderParty();
});
for (const id of ['px-x', 'px-y']) {
    $(id).oninput = () => {
        const value = Number($(id).value);
        if ($(id).value !== '' && Number.isFinite(value)) {
            $(id === 'px-x' ? 'tp-x' : 'tp-y').value = Math.floor(value / 16);
        }
    };
}
function showPartyIfHere() {
    if (state.data && Objlist.getActor(state.data, Objlist.getParty(state.data)[0].number).z === mapLevel()) {
        showParty();
    }
}
renderMap();
$('item-search').oninput = () => renderItems();
$('give-member').onchange = () => guard(renderQualityHelper);
$('quality-helper').onchange = () => { $('item-quality').value = $('quality-helper').value; };
$('give').onclick = () => guard(() => addChange(give(state.item, Number($('item-qty').value))));
$('give-gold').onclick = () => guard(() => addChange(give(itemKey(GOLD), 5000)));     // стопки, качество не важно
$('give-reagents').onclick = () => guard(() => addChange(REAGENTS.map(obj => give(itemKey(obj), 20)).join('; ')));
$('give-spells').onclick = () => guard(() => addChange(giveSpells()));
