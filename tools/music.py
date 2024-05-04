def decode(data):
    commands = [
        'note',
        'note_on',
        'note_off_on',
        'carrier',
        'modulator',
        'portamento',
        'vibrato',
        'instrument',
    ]
    result = []
    index = 0
    offsets = {}
    while index < len(data):
        offsets[index] = len(result)
        command = data[index]
        index += 1
        high = command >> 4
        low = command & 0x0f
        assert high in (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x0e, 0x0f), hex(high)

        # FIXME remove arguments from everywhere
        # FIXME add signed argument
        if high < 3:
            tone = data[index]
            tone_low = tone & 0x1f
            assert tone_low < 24
            octave = tone >> 5
            index += 1
            result.append({'command': commands[high], 'channel': low, 'octave': octave, 'tone': tone_low})

        elif high < 8:
            arg = data[index]
            index += 1
            result.append({'command': commands[high], 'channel': low, 'argument': arg})

        elif high == 8:
            assert low in (1, 2, 3, 5, 6), hex(low)
            if low == 1:
                count = data[index]
                index += 1
                start = int.from_bytes(data[index:index+2], 'little')
                index += 2
                result.append({'command': 'repeat', 'count': count, 'start': start})

            elif low == 2:
                arg = data[index]
                index += 1
                result.append({'command': 'sleep', 'duration': arg})

            elif low == 3:
                arg = data[index]
                index += 1
                assert arg < 9
                index += 11
                result.append({'command': 'data', 'instrument': arg, 'data': list(data[index-11:index])})

            elif low == 5:
                arg = data[index]
                index += 1
                result.append({'command': 'fade_in', 'argument': arg})

            else:
                assert low == 6
                arg = data[index]
                index += 1
                result.append({'command': 'fade_out', 'argument': arg})

        elif high == 0x0e:
            result.append({'command': 'loop'})

        elif high == 0x0f:
            result.append({'command': 'return'})

    assert index == len(data)

    for item in result:
        if item['command'] == 'repeat':
            item['start'] = offsets[item['start']] + 1

    return result
