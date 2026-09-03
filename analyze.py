import csv
import ast
import re
from itertools import groupby

from lingpy import LexStat, Alignments, prosodic_string
from lingrex import CoPaR

from middleChinese import getMCReconstructions, getMCData, Reading, Final


def normalize_reading(reading: str) -> str:
    r = reading.split(' ')[0]
    if r.endswith('G'):
        r = r[:-1] + 'ng'
    if r.startswith('G'):
        r = r[1:]
    return r


def read_hanja_csv() -> dict[str, set[str]]:
    with open("hanja.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        result = {}
        for row in reader:
            hanja = row["ch"]
            readings = [normalize_reading(r) for r in ast.literal_eval(row['s'])]
            if hanja not in result:
                result[hanja] = set()
                result[hanja].update(readings)
    return result


def tokenize_mk(text: str) -> str:
    text = text.replace('ᆐ', 'ywey').replace('[]', '')
    regex = re.compile(r'(ch|kh|th|ph|ng|k|n|t|l|m|p|s|c|h|z)|(y?w?[aeiou])|y')
    tokens = []
    pos = 0
    while pos < len(text):
        m = regex.match(text, pos)
        if m is None or m.end() == pos:
            raise ValueError(f"No match at position {pos}: {text[pos:pos+20]!r} in {text!r}")
        token = m.group()
        if token in ['ya', 'ye', 'yo', 'yu', 'ywa', 'ywe']:
            if token[1:] == 'o':
                toks = ['y', 'wo']
            elif token[1:] == 'u':
                toks = ['y', 'wu']
            elif token[1:] == 'wa':
                toks = ['y', 'w', 'a']
            elif token[1:] == 'we':
                toks = ['y', 'w', 'e']
            else:
                toks = ['y', token[1:]]
        elif token in ['wa', 'we']:
            toks = ['w', token[1:]]
        else:
            toks = [token]
        tokens.extend(toks)
        pos = m.end()

    # convert to IPA
    ipa_map = {
        'c': 't͡s',
        'ch': 't͡sʰ',
        'kh': 'kʰ',
        'th': 'tʰ',
        'ph': 'pʰ',
        'ng': 'ŋ',
        'y': 'j',
        'e': 'ə',
        'o': 'ʌ',
        'u': 'ɨ',
        'wo': 'o',
        'wu': 'u',
    }
    tokens = [ipa_map.get(t, t) for t in tokens]

    return " ".join(tokens)


def tokenize_mc(reading: str) -> str:
    initial, final = reading.split(' ')
    initial = (
        initial
        .replace("'", 'ʔ')
        .replace('tr', 'ʈ')
        .replace('dr', 'ɖ')
        .replace('nr', 'ɳ')
        .replace('tsr', 'ʈ͡ʂ')
        .replace('dzr', 'ɖ͡ʐ')
        .replace('sr', 'ʂ')
        .replace('zr', 'ʐ')
        .replace('ts', 't͡s')
        .replace('dz', 'd͡z')
        .replace('tsy', 't͡ɕ')
        .replace('dzy', 'd͡ʑ')
        .replace('sy', 'ɕ')
        .replace('zy', 'ʑ')
        .replace('ny', 'ɲ')
        .replace('ng', 'ŋ')
        .replace('y', 'j')
    )
    if 'h' in initial[1:]:
        initial = initial.replace('h', 'ʰ')
    final = final.replace('ng', 'ŋ')
    final = " ".join(final)
    final = final.replace('ɨ ̯', 'ɨ̯')
    result = initial + " " + final
    return result


def get_overlap():
    mk_words = read_hanja_csv()
    mc_words = getMCReconstructions('baxter', False, True, chongniu='medial')

    # extract overlapping words with only 1 reading in each system
    overlap = {}
    for hanja, mk_readings in mk_words.items():
        mc_readings = mc_words.get(hanja)
        if mc_readings is None or len(mc_readings) != 1:
            continue
        overlap[hanja] = (mk_readings.pop(), mc_readings.pop())

    print(len(overlap), "overlapping characters with exactly 1 reading in each system")

    return overlap


def analyze_overlap():
    overlap = get_overlap()

    mc_finals = {}

    initial_types = {
        "脣音 / bilabial": "脣音",
        "舌頭音 / alveolar": "(半)舌音",
        "半舌音": "(半)舌音",
        "舌上音 / retroflex": "(半)舌音",
        "齒頭音 / dental": "齒頭音",
        "正齒音 / retroflex": "莊組",
        "正齒音 / post-alveolar": "章組",
        "牙音 / velar": "牙喉音",
        "喉音 / glottal": "牙喉音",
        "以母": "以母",
        "半齒音": "日母",
    }

    mc_words = getMCReconstructions('baxter', False, True, chongniu='medial')
    for hanja, baxters in mc_words.items():
        readings = getMCData(hanja)
        if readings is not None:
            for reading in readings:
                mc_final = "/".join(reading.final.names)
                mc_finals[reading.final.number] = mc_final

    mk_results = {}  # (final_number, initial_type) -> dict[mk_final, list[hanja]]
    for i, (hanja, (mk_reading, mc_reading)) in enumerate(overlap.items(), 1):
        reading, = getMCData(hanja)
        mk_reading = mk_reading.replace('ᆐ', 'ywey').replace('[]', '')
        mk_final = re.fullmatch(r'[^wyaeiou]*([wyaeiou]+.*)', mk_reading)[1]
        mc_final = "/".join(reading.final.names)
        mc_finals[reading.final.number] = mc_final
        key = (reading.final.number, initial_types[reading.initial.type])
        mk_results[key] = mk_results.get(key, dict())
        words = mk_results[key].get(mk_final, [])
        words.append(hanja)
        mk_results[key][mk_final] = words

    with open("outputs/mcmktable.tsv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        initial_groups = [key for key, _ in groupby(initial_types.values())]
        writer.writerow(["MC Final No", "MC Final", *initial_groups])

        for final_no in range(1, 161):

            # nothing in this row
            if final_no not in mc_finals:
                writer.writerow([final_no, "-"] + ["-"] * len(initial_groups))
                continue

            row = [final_no, mc_finals[final_no]]

            for initial_type in initial_groups:
                key = (final_no, initial_type)
                if key in mk_results:
                    data: list[tuple[str, list[str]]] = list(
                        sorted(mk_results[key].items(), key=lambda item: len(item[1]), reverse=True)
                    )

                    # filter out single occurrences if more than 5 words in this category
                    occurrences = sum(len(words) for _, words in data)
                    if occurrences >= 5:
                        data = [
                            (mk_final, words) for mk_final, words in data
                            if len(words) > 1
                        ]

                    row.append(",".join(f"{mk_final}({len(words)})" for mk_final, words in data))

                else:
                    # nothing here
                    row.append("-")

            writer.writerow(row)


def write_wordlist():
    overlap = get_overlap()

    # store into tsv file
    # in LingPy's TSV format with columns for ID, DOCULECT (language), CONCEPT, TOKENS (space-segmented IPA), and crucially COGID (cognate set IDs) and ALIGNMENT.
    with open("outputs/wordlist.tsv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["ID", "DOCULECT", "CONCEPT", "TOKENS", "IPA"])
        uid = 1
        for i, (hanja, (mk_reading, mc_reading)) in enumerate(overlap.items(), 1):
            mk_tokenized = tokenize_mk(mk_reading)
            mc_tokenized = tokenize_mc(mc_reading)
            writer.writerow([uid, "MK", hanja, mk_tokenized, "".join(mk_tokenized.split(" "))])
            uid += 1
            writer.writerow([uid, "MC", hanja, mc_tokenized, "".join(mc_tokenized.split(" "))])
            uid += 1


def analyze():
    lex = LexStat('outputs/wordlist.tsv')
    lex.get_scorer(runs=10000)
    lex.cluster(method='lexstat', threshold=0.6, ref='cogid')
    alm = Alignments(lex, ref='cogid')
    alm.align()
    alm.add_entries('structure', 'tokens',
                    lambda x: ' '.join(prosodic_string(x)))
    alm.output('tsv', filename='outputs/aligned_data')

    cop = CoPaR('outputs/aligned_data.tsv', ref='cogid', structure='structure', minrefs=2)
    cop.get_sites()  # extract alignment sites
    cop.cluster_sites()  # cluster sites into correspondence patterns

    for (structure, pattern), sites in cop.clusters.items():
        print(f'{structure} {pattern} ×{len(sites)}')

    cop.sites_to_pattern()  # secondary analysis, assigns sites to patterns
    cop.add_patterns()
    cop.write_patterns('outputs/my_patterns.tsv')  # export


if __name__ == "__main__":
    analyze_overlap()
    # write_wordlist()
    #analyze()
