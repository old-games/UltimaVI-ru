// Простейший zip без сжатия (метод STORE) — чтобы в Firefox и Safari, которые не умеют записывать файлы на диск,
// отдать изменённые файлы сохранения одним архивом.

(function (root) {
    'use strict';

    const CRC_TABLE = (() => {
        const table = new Uint32Array(256);
        for (let n = 0; n < 256; n++) {
            let c = n;
            for (let k = 0; k < 8; k++) {
                c = c & 1 ? 0xedb88320 ^ c >>> 1 : c >>> 1;
            }
            table[n] = c >>> 0;
        }
        return table;
    })();

    function crc32(data) {
        let c = 0xffffffff;
        for (const byte of data) {
            c = CRC_TABLE[(c ^ byte) & 0xff] ^ c >>> 8;
        }
        return (c ^ 0xffffffff) >>> 0;
    }

    // files: [{name, data: Uint8Array}], имена — ASCII. Возвращает Uint8Array архива.
    function makeZip(files) {
        const chunks = [];
        const central = [];
        let offset = 0;
        const u16 = value => [value & 0xff, value >> 8 & 0xff];
        const u32 = value => [value & 0xff, value >> 8 & 0xff, value >> 16 & 0xff, value >>> 24 & 0xff];
        // Дата и время в формате DOS: 01.01.2000 00:00.
        const time = 0;
        const date = (2000 - 1980) << 9 | 1 << 5 | 1;
        for (const {name, data} of files) {
            const nameBytes = Array.from(name, c => c.charCodeAt(0));
            const crc = crc32(data);
            const common = [...u16(10), ...u16(0), ...u16(0), ...u16(time), ...u16(date),
                ...u32(crc), ...u32(data.length), ...u32(data.length), ...u16(nameBytes.length), ...u16(0)];
            const header = Uint8Array.from([...u32(0x04034b50), ...common, ...nameBytes]);
            chunks.push(header, data);
            central.push(Uint8Array.from([...u32(0x02014b50), ...u16(20), ...common, ...u16(0), ...u16(0), ...u16(0),
                ...u32(0), ...u32(offset), ...nameBytes]));
            offset += header.length + data.length;
        }
        const centralSize = central.reduce((sum, chunk) => sum + chunk.length, 0);
        const end = Uint8Array.from([...u32(0x06054b50), ...u16(0), ...u16(0), ...u16(files.length), ...u16(files.length),
            ...u32(centralSize), ...u32(offset), ...u16(0)]);
        const parts = [...chunks, ...central, end];
        const result = new Uint8Array(parts.reduce((sum, chunk) => sum + chunk.length, 0));
        let position = 0;
        for (const part of parts) {
            result.set(part, position);
            position += part.length;
        }
        return result;
    }

    const api = {crc32, makeZip};

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.Zip = api;
    }
})(this);
