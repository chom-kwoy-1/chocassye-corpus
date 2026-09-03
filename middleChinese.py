import csv
import os
import pathlib
import re
from dataclasses import dataclass, field


@dataclass
class Initial:
    type: str
    rhyme_group: str
    baxter: str
    karlgren: str
    shao: str
    wangli: str
    pulleyblank: str
    zhengzhang: str
    lirong: str
    panwuyun: str


@dataclass
class Final:
    number: int
    group: str
    names: list[str]
    division: int
    baxter: str
    karlgren: str
    shao: str
    wangli: str
    pulleyblank: str
    zhengzhang: str
    lirong: str
    panwuyun: str


@dataclass
class Reading:
    initial: Initial
    final: Final
    rhyme_group: str
    division: str
    open_closed: str
    chongniu: str
    tone: str
    fanqie: str


@dataclass
class _ReadingData:
    initial: str
    rhyme_group: str
    division: str
    open_closed: str
    chongniu: str
    tone: str
    fanqie: str


def _read_initials_csv(file_path: str) -> dict[str, Initial]:
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        result: dict[str, Initial] = {}
        for row in reader:
            initial = Initial(
                type=row["Type"],
                rhyme_group=row["Rhyme Group"],
                baxter=row["Baxter"],
                karlgren=row["Karlgren"],
                shao=row["Shao"],
                wangli=row["Wang Li"],
                pulleyblank=row["Pulleyblank"],
                zhengzhang=row["Zhengzhang"],
                lirong=row["Li Rong"],
                panwuyun=row["Pan Wuyun"],
            )
            result[initial.rhyme_group] = initial
        return result


def _read_finals_csv(
    file_path: str,
) -> dict[str, Final]:
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        table: list[Final] = []
        for row in reader:
            final = Final(
                number=int(row["No"]),
                group=row["Group"],
                names=[name.strip() for name in row["Name"].split("/")],
                division=int(row["Div"]),
                baxter=row["Baxter"],
                karlgren=row["Karlgren"],
                shao=row["Shao"],
                wangli=row["Wang Li"],
                pulleyblank=row["Pulleyblank"],
                zhengzhang=row["Zhengzhang"],
                lirong=row["Li Rong"],
                panwuyun=row["Pan Wuyun"],
            )
            table.append(final)

    name_map: dict[str, Final] = {}
    for final in table:
        for name in final.names:
            name_map[name] = final

    return name_map


def _read_mc_data_files(dir_path: str) -> dict[str, list[_ReadingData]]:
    print("Start reading MC data files:")
    mc_data: dict[str, list[_ReadingData]] = {}

    line_pattern = re.compile(r'\["([^"])"\] *= *\{((?:\s*"[^"]*",?\s*)+)\}')
    reading_pattern = re.compile(
        r'"([^"])([^"])([^"])([^"]) ([^"])([^"][^"]|0)(?:-(重鈕))?(?:\?|？)?"'
    )

    for entry in sorted(os.listdir(dir_path)):
        full_path = os.path.join(dir_path, entry)
        if not os.path.isfile(full_path):
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        for line in content.split("\n"):
            if (
                line.startswith("return")
                or line.startswith("}")
                or line.strip() == ""
            ):
                continue

            m = line_pattern.search(line)
            if m is None:
                print("Invalid line:", line)
                continue

            char = m.group(1)
            readings_str = m.group(2)
            readings: list[_ReadingData] = []

            for piece in readings_str.split(","):
                piece = piece.strip()
                if not piece:
                    continue
                rm = reading_pattern.search(piece)
                if rm is None:
                    print("Invalid reading:", char, piece)
                    continue
                readings.append(
                    _ReadingData(
                        initial=rm.group(1),
                        rhyme_group=rm.group(2),
                        division=rm.group(3),
                        open_closed=rm.group(4),
                        chongniu=rm.group(7) or "",
                        tone=rm.group(5),
                        fanqie=rm.group(6),
                    )
                )
            mc_data[char] = readings

    print("Finished reading MC data files.")
    return mc_data


# --- Module-level initialization ---

rootdir = pathlib.Path(__file__).parent
_MC_INITIALS_DATA = _read_initials_csv(str(rootdir / "MCinitials.csv"))
_MC_FINALS_DATA = _read_finals_csv(str(rootdir / "MCfinals.csv"))
_MIDDLE_CHINESE_DATA = _read_mc_data_files(str(rootdir / "MCData/"))
_CHECKED_TONE_COUNTERPARTS = {
    '東': '屋', '冬': '沃', '鍾': '燭', '江': '覺', '真': '質', '眞': '質', '臻': '櫛', '諄': '術', '痕': '麧', '魂': '沒',
    '欣': '迄', '文': '物', '寒': '曷', '桓': '末', '元': '月', '刪': '黠', '山': '鎋', '仙': '薛', '先': '屑', '唐': '鐸',
    '陽': '藥', '庚': '陌', '耕': '麥', '清': '昔', '青': '錫', '登': '德', '蒸': '職', '侵': '緝', '談': '盍', '嚴': '業',
    '凡': '乏', '銜': '狎', '咸': '洽', '鹽': '葉', '添': '帖', '覃': '合',
}

def _get_mc_initial(rhyme_group: str) -> Initial | None:
    return _MC_INITIALS_DATA.get(rhyme_group)


def _get_mc_final(
    rhyme_group: str,
    open_closed: str,
    division: str,
    chongniu: str,
    tone: str,
) -> Final | None:
    chongniu = "重鈕三" if chongniu else division
    candidates = [
        rhyme_group + chongniu + open_closed,
        rhyme_group + chongniu,
        rhyme_group + division + open_closed,
        rhyme_group + open_closed,
        rhyme_group + division,
        rhyme_group,
    ]
    for key_ in candidates:
        key = (_CHECKED_TONE_COUNTERPARTS.get(key_[0], key_[0]) if tone == "入" else key_[0]) + key_[1:]
        result = _MC_FINALS_DATA.get(key)
        if result is not None:
            return result
    return None


def getMCData(char: str) -> list[Reading] | None:
    data = _MIDDLE_CHINESE_DATA.get(char)
    if data is None:
        return None

    readings: list[Reading] = []
    for record in data:
        initial = _get_mc_initial(record.initial)
        final = _get_mc_final(
            record.rhyme_group,
            record.open_closed,
            record.division,
            record.chongniu,
            record.tone,
        )
        if initial is None or final is None:
            print(
                "Bad lookup:",
                char,
                record.initial,
                record.rhyme_group,
                record.division,
                record.open_closed,
                record.chongniu,
            )
        readings.append(
            Reading(
                initial=initial,  # type: ignore[arg-type]
                final=final,  # type: ignore[arg-type]
                rhyme_group=record.rhyme_group,
                division=record.division,
                open_closed=record.open_closed,
                chongniu=record.chongniu,
                tone=record.tone,
                fanqie=record.fanqie,
            )
        )
    return readings


CHONGNIU_RHYME_GROUPS = "支脂祭眞質仙薛宵侵緝鹽葉"
SEMI_CHONGNIU_RHYME_GROUPS = CHONGNIU_RHYME_GROUPS + "諄庚陌清昔幽"

def getMCReconstructions(
        author: str,
        include_tone: bool,
        spaced: bool,
        chongniu: str | None = None,
) -> dict[str, list[str]]:
    result = {}
    for char in _MIDDLE_CHINESE_DATA.keys():
        readings = getMCData(char)
        if readings is None:
            continue
        for reading in readings:
            initial = getattr(reading.initial, author)
            final = getattr(reading.final, author)
            if author == 'baxter':
                is_chongniu_initial = initial in ['p', 'ph', 'b', 'm', 'k', 'kh', 'g', 'ng', "'", 'x', 'h']
                is_semi_chongniu_rhyme_group = (
                    reading.rhyme_group in SEMI_CHONGNIU_RHYME_GROUPS and
                    reading.division == '三'
                )
                if is_semi_chongniu_rhyme_group:
                    if not is_chongniu_initial:
                        # ignore chongniu for not applicable initials
                        final = re.sub('^ji(?=e)', 'j', final)
                        final = re.sub('^jwi(?=e)', 'jw', final)
                        final = re.sub('^ji', 'i', final)
                        final = re.sub('^jwi', 'wi', final)
                if 'y' in initial and final.startswith("j"):
                    final = final[1:]
                if is_semi_chongniu_rhyme_group and is_chongniu_initial:
                    if chongniu is None:
                        pass
                    elif chongniu == "medial":
                        # Replace chongniu-III with medial glides
                        chongniu_IV = 'ji' in final or 'jwi' in final
                        final = re.sub('^ji(?=e)', 'j', final)
                        final = re.sub('^jwi(?=e)', 'jw', final)
                        final = re.sub('^ji', 'i', final)
                        final = re.sub('^jwi', 'wi', final)
                        if not chongniu_IV:
                            final = re.sub('^j', 'ɨ̯', final)
                            if 'ɨ̯' not in final:
                                final = 'ɨ̯' + final
                    elif chongniu == "vowel":
                        raise NotImplementedError("vowel chongniu not implemented yet")
            if spaced:
                recon = initial + " " + final
            else:
                recon = initial + final
            if include_tone:
                if reading.tone == '上':
                    recon += " X" if spaced else "X"
                if reading.tone == '去':
                    recon += " H" if spaced else "H"
            if char not in result:
                result[char] = []
            result[char].append(recon)
    return result
