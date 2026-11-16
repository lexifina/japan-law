"""Compute every number for the 20 charts into <build>/data.json.

    python prep.py <build-dir>

Reads, from <build> (written by make.py): tree.tsv (every file of every law in force), log.tsv (one line per commit:
its author, which is the law that made the change, its trailers and the provisions its message lists), codes-names.tsv
(the files each commit wrote in the Constitution and the six codes), repo/laws.csv (every revision e-Gov holds, with
the amending law, its title and dates), rev-ids.txt (the revision id of each row of laws.csv, from data/revisions.json),
repo/data/laws.json and repo/data/paths.json (each law's folder, id, title and number), suppl-heads.jsonl (the start
of one supplementary-provisions file of every amending Act), old-texts.jsonl (text files of the laws numbered before
1952) and codes.jsonl (the articles of the Constitution and the six codes). Every rule that reads a category out of a
name, a title or a text is in this file.
"""
import collections, csv, json, os, re, statistics, sys
from datetime import date

B = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '.build')
R = os.path.join(B, 'repo')
OUT, PROFILE = {}, {}
D = lambda s: date.fromisoformat(s[:10])
csv.field_size_limit(1 << 30)


def jl(name):
    with open(os.path.join(B, name), encoding='utf-8') as fh:
        for line in fh:
            yield json.loads(line)


# ------------------------------------------------------------------ eras and numerals
ERA_START = {'m': 1868, 't': 1912, 's': 1926, 'h': 1989, 'r': 2019}
ERA_OF_DIGIT = {'1': 'm', '2': 't', '3': 's', '4': 'h', '5': 'r'}
ERA_KANJI = {'明治': 'm', '大正': 't', '昭和': 's', '平成': 'h', '令和': 'r'}
KD = '〇一二三四五六七八九'


def kanji_num(s):
    """一二三 / 百二十三 / 二〇二六 -> int"""
    if s == '元':
        return 1
    if s and all(c in KD for c in s):
        return int(''.join(str(KD.index(c)) for c in s))
    tot = cur = 0
    for c in s:
        if c in KD:
            cur = KD.index(c)
        elif c in '十百千':
            tot += (cur or 1) * {'十': 10, '百': 100, '千': 1000}[c]
            cur = 0
    return tot + cur


def west(era, y):
    return ERA_START[era] + int(y) - 1


# ------------------------------------------------------------------ the laws: folders, ids, titles
P = json.load(open(os.path.join(R, 'data', 'paths.json'), encoding='utf-8'))
LID2FO = {P['law_ids'].get(k, k): v for k, v in P['paths'].items()}
FO2LID = {v: k for k, v in LID2FO.items()}
LAWS = {x['law_id']: x for x in json.load(open(os.path.join(R, 'data', 'laws.json'), encoding='utf-8'))}
KINDS = P['kind_order']


def split_law(path):
    p = path.split('/')
    if p[0] == 'constitution':
        d = 2
    elif p[0] in ('ministerial-ordinance', 'rule', 'regulation'):
        d = 5 if p[1] == 'joint' else 4
    else:
        d = 3
    return '/'.join(p[:d]), p[d:]


SUP = re.compile(r'^([mtshr])(\d+)-(?:(\d{4})-)?([a-z]*)(\d+)(?:-(\d+))?\.md$')
FO = {}          # folder -> facts
with open(os.path.join(B, 'tree.tsv'), encoding='utf-8') as fh:
    for line in fh:
        path = line.rstrip('\n').split('\t')[0]
        if path.split('/', 1)[0] not in KINDS:
            continue
        fo, rest = split_law(path)
        f = FO.setdefault(fo, {'art': 0, 'br': [0, 0, 0, 0], 'rng': 0, 'sup': [], 'orig': False, 'main': False, 'pre': False, 'appdx': 0, 'files': 0})
        f['files'] += 1
        if len(rest) == 1:
            n = rest[0]
            m = re.match(r'^art-(\d+(?:-\d+)*)(-to-\d+(?:-\d+)*)?\.md$', n)
            if m:
                if m.group(2):                   # a range of deleted articles (第三十八条から第八十四条まで　削除): one file, not an article
                    f['rng'] += 1
                else:                            # one file per article
                    f['art'] += 1
                    f['br'][m.group(1).count('-')] += 1
            elif n == 'main.md':
                f['main'] = True
            elif n == 'preamble.md':
                f['pre'] = True
        elif rest[0] == 'suppl':
            if rest[1] == 'original.md':
                f['orig'] = True
            else:
                m = SUP.match(rest[1])
                assert m, path
                era, y, md, t, num, sub = m.groups()
                f['sup'].append((era, int(y), md or '', t or 'ac', int(num), sub or ''))
        elif rest[0] in ('appdx', 'main-appdx'):
            f['appdx'] += 1
assert len(FO) == len(LAWS), (len(FO), len(LAWS))
for fo, f in FO.items():
    lid = FO2LID[fo]
    x = LAWS[lid]
    f['lid'], f['title'], f['num'] = lid, x['title'], x['num']
    f['kind'] = fo.split('/')[0]
    yt = fo.split('/')[-2] if f['kind'] != 'constitution' else '1946'
    f['year'] = int(yt[:4])
    f['era'] = ERA_OF_DIGIT[lid[0]]
    f['issuer'] = fo.split('/')[1] if f['kind'] in ('ministerial-ordinance', 'rule', 'regulation') else ''
print('laws', len(FO))


def kind_of(fo):
    k = FO[fo]['kind']
    return 'dajokan' if k.startswith('dajokan') else k


def introducer(lid):
    """who introduced an Act, from e-Gov's law id: AC0000000 the Cabinet, AC1000000 members of the House of
    Representatives, AC0100000 members of the House of Councillors"""
    m = re.match(r'^\d{3}AC(\d{7})\d{3}$', lid or '')
    return {'0000000': 'cab', '1000000': 'hr', '0100000': 'hc'}.get(m.group(1)) if m else None


def short_title(t):
    return re.sub(r'^(明治|大正|昭和|平成|令和)[元〇一二三四五六七八九十百千]+年[^（]*第[〇一二三四五六七八九十百千]+号（(.+)）$', r'\2', t)


# ------------------------------------------------------------------ the revisions e-Gov holds (laws.csv + their target laws)
REV = []
ids = open(os.path.join(B, 'rev-ids.txt'), encoding='utf-8').read().split()
with open(os.path.join(R, 'laws.csv'), encoding='utf-8') as fh:
    for i, r in enumerate(csv.DictReader(fh)):
        r['target'] = ids[i].split('_', 1)[0]
        r['fo'] = LID2FO[r['target']]
        REV.append(r)
assert len(REV) == len(ids)
ST_IN = ('in force', 'baseline', 'oldest version available', 'enacted')
ST_FUT = ('not yet in force', 'scheduled (not yet fixed)')
print('revisions', len(REV), collections.Counter(r['status'] for r in REV))
hist_laws = {r['fo'] for r in REV if r['status'] in ('in force', 'baseline', 'enacted')}     # laws whose earlier versions are held
PROFILE.update(laws=len(FO), revisions=len(REV), versions=sum(r['status'] in ST_IN for r in REV), future=sum(r['status'] in ST_FUT for r in REV),
               with_history=len(hist_laws), current_only=len(FO) - len(hist_laws), head=os.environ.get('HEAD_SHA', ''))
corpus = json.load(open(os.path.join(R, 'corpus.json'), encoding='utf-8'))
PROFILE.update(record_to=corpus['record_to'], checked_on=corpus['checked_on'], built=date.today().isoformat())


# the commits: each revision e-Gov holds is written by a commit carrying its id (Revision:); a law published first as
# its text in force has two such commits for that revision (the text published alone, and the one restoring it after
# its earlier versions were appended): the second one's files are the change from the version before.
LOG = {}
with open(os.path.join(B, 'log.tsv'), encoding='utf-8') as fh:
    for r in csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE):
        LOG[r['sha']] = {k: r[k] for k in ('i', 'author', 'In-force', 'Kind', 'Label', 'Revision', 'new', 'amended', 'removed', 'subject')}
CF = {}
with open(os.path.join(B, 'commit-files.tsv'), encoding='utf-8') as fh:
    for line in fh:
        s, a_, b_ = line.rstrip('\n').split('\t')
        CF[s] = (int(a_), int(b_))
BYREV = {}
for s, r in LOG.items():
    for rv in r['Revision'].split(' ; '):
        if rv and (rv not in BYREV or LOG[BYREV[rv]]['Kind'] == 'baseline'):
            BYREV[rv] = s
for i, r in enumerate(REV):
    s = BYREV.get(ids[i])
    ns, no = CF.get(s, (0, 0)) if s else (0, 0)
    r['cls'] = 'none' if not s else 'text' if no else 'suppl' if ns else 'empty'
print('revision classes', collections.Counter((r['status'], r['cls']) for r in REV if r['status'] in ('in force', 'enacted')))
PROFILE.update(commits=len(LOG), law_commits=sum(1 for r in LOG.values() if r['author'] != 'Lexifina'))


def akind(lid):
    """the kind of an amending law, from its e-Gov id"""
    m = re.match(r'^\d{3}([A-Z]+)', lid or '')
    if not m:
        return ''
    return {'AC': 'act', 'CO': 'cabinet-order', 'IO': 'imperial-ordinance', 'M': 'ministerial-ordinance', 'R': 'rule', 'RJNJ': 'rule', 'RPMD': 'rule'}.get(m.group(1), 'other')


# ================================================================== I. the law in force
KORD = ['act', 'cabinet-order', 'ministerial-ordinance', 'rule', 'imperial-ordinance', 'dajokan', 'pm-decision', 'regulation', 'constitution']
c = {k: {'laws': 0, 'art': 0, 'hist': 0, 'main': 0} for k in KORD}
for fo, f in FO.items():
    k = kind_of(fo)
    c[k]['laws'] += 1
    c[k]['art'] += f['art']
    c[k]['hist'] += fo in hist_laws
    c[k]['main'] += f['main'] and not f['art']
longest = sorted(FO, key=lambda fo: -FO[fo]['art'])[:12]
OUT['c01'] = {'kinds': c, 'longest': [[fo, short_title(FO[fo]['title']), FO[fo]['art'], FO[fo]['num']] for fo in longest],
              'arts': sum(f['art'] for f in FO.values()), 'pre': sorted([fo, FO[fo]['title']] for fo in FO if FO[fo]['pre'])}
PROFILE.update(articles=OUT['c01']['arts'], files=sum(f['files'] for f in FO.values()))
print('c01', {k: (v['laws'], v['art']) for k, v in c.items()})

# 2. the year each law in force was numbered, by kind; the eras
by = collections.defaultdict(collections.Counter)
era = collections.defaultdict(collections.Counter)
for fo, f in FO.items():
    by[f['year']][kind_of(fo)] += 1
    era[f['era']][kind_of(fo)] += 1
old = sorted(FO, key=lambda fo: (FO[fo]['year'], fo))[:14]
OUT['c02'] = {'years': {y: dict(v) for y, v in sorted(by.items())}, 'eras': {e: dict(v) for e, v in era.items()},
              'oldest': [[fo, short_title(FO[fo]['title']), FO[fo]['num'], FO[fo]['year']] for fo in old],
              'era_change': [[fo, FO[fo]['title'], FO[fo]['num']] for fo in FO if FO[fo]['title'] == '元号を改める政令' or FO[fo]['title'] == '元号法']}
print('c02 eras', {e: sum(v.values()) for e, v in era.items()})

# 3. katakana: the text of the laws numbered before 1947 (every file), and a sample of those of 1947 to 1951.
# The pre-war style writes its particles in katakana between kanji (本法ハ…, 之ヲ…, 其ノ…); a file is in that style when
# such particles (ノ ヲ ニ ハ ト モ ヘ テ between two kanji) outnumber the same particles in hiragana. Loanwords written in
# katakana (エボラ出血熱, ピロプラズマ症) do not count. A file with fewer than two particles (削除, a table) is not judged.
KAN = r'[一-鿿々〇]'
OLDP = re.compile(KAN + r'[ノヲニハトモヘテ](?=' + KAN + ')')
NEWP = re.compile(KAN + r'[のをにはともへて](?=' + KAN + ')')


def kana_style(t):
    body = '\n'.join(l for l in t.split('\n') if l.strip() and not l.startswith('#') and not re.match(r'^（[^）]*）$', l.strip()))
    a, b = len(OLDP.findall(body)), len(NEWP.findall(body))
    return None if a + b < 2 else 'kata' if a > b else 'hira'


kat = collections.defaultdict(lambda: [0, 0])     # folder -> [katakana files, hiragana files]
first_text = {}                                    # folder -> the start of its first text file (main.md or the lowest article)
for o in jl('old-texts.jsonl'):
    fo, rest = split_law(o['p'])
    s = kana_style(o['t'])
    if s:
        kat[fo][0 if s == 'kata' else 1] += 1
    body = ' '.join(l.strip() for l in o['t'].split('\n') if l.strip() and not l.startswith('#') and not re.match(r'^（[^）]*）$', l.strip()))
    if body and not re.search(r'削除$', body) and (fo not in first_text or rest[0] == 'main.md'):
        first_text[fo] = body[:64]
for o in jl('codes.jsonl'):                       # the Constitution (1946) is read with the codes
    if o['p'].startswith('constitution/'):
        s = kana_style(o['t'])
        if s:
            kat['constitution/1946'][0 if s == 'kata' else 1] += 1
        if o['p'].endswith('/art-001.md'):
            first_text['constitution/1946'] = ' '.join(l.strip() for l in o['t'].split('\n') if l.strip() and not l.startswith('#') and not re.match(r'^（[^）]*）$', l.strip()))[:64]
style = {fo: ('kata' if v[0] and not v[1] else 'hira' if v[1] and not v[0] else 'mixed') for fo, v in kat.items()}
pre47 = [fo for fo in FO if FO[fo]['year'] < 1947]
late = [fo for fo in style if FO[fo]['year'] >= 1947]
assert not [fo for fo in late if style[fo] != 'hira'], 'a law numbered after 1946 in katakana: check the rule'
ERA_BIN = lambda f: 'm' if f['era'] == 'm' else 't' if f['era'] == 't' else 's'
grid = collections.defaultdict(collections.Counter)
for fo in pre47:
    grid[(ERA_BIN(FO[fo]), 'act' if FO[fo]['kind'] in ('act', 'constitution') else 'other')][style.get(fo, 'none')] += 1
lastin = {x['law_id']: x['last_in_force'] for x in LAWS.values()}
kat_acts = sorted((fo for fo in pre47 if style.get(fo) in ('kata', 'mixed') and FO[fo]['kind'] == 'act'), key=lambda fo: (FO[fo]['year'], fo))
hira_acts = sorted((fo for fo in pre47 if style.get(fo) == 'hira' and FO[fo]['kind'] == 'act'), key=lambda fo: (FO[fo]['year'], fo))
OUT['c03'] = {'grid': {f'{a}|{b}': dict(v) for (a, b), v in grid.items()},
              'n': {s: sum(1 for fo in pre47 if style.get(fo, 'none') == s) for s in ('kata', 'mixed', 'hira', 'none')}, 'pre47': len(pre47),
              'files_kata': sum(kat[fo][0] for fo in pre47), 'files_hira': sum(kat[fo][1] for fo in pre47),
              'late_checked': len(late), 'late_files': sum(sum(kat[fo]) for fo in late),
              'kata_acts': [[fo, short_title(FO[fo]['title']), FO[fo]['num'], FO[fo]['year'], lastin.get(FO[fo]['lid'], ''), FO[fo]['art'], style[fo], kat[fo][0], kat[fo][1]] for fo in kat_acts],
              'hira_acts': [[fo, short_title(FO[fo]['title']), FO[fo]['num'], FO[fo]['year'], FO[fo]['art']] for fo in hira_acts],
              'dots': [[fo, FO[fo]['year'], kind_of(fo), style.get(fo, 'none'), short_title(FO[fo]['title']), FO[fo]['num'], first_text.get(fo, ''), lastin.get(FO[fo]['lid'], '')]
                       for fo in sorted(pre47, key=lambda q: (FO[q]['year'], q))]}
print('c03', OUT['c03']['n'], 'katakana or mixed acts', len(kat_acts), 'hiragana acts', len(hira_acts), 'files', OUT['c03']['files_kata'], OUT['c03']['files_hira'])

# 4. branch numbers: 第十四条の二 is art-014-2
brk = {k: [0, 0, 0, 0] for k in KORD}
for fo, f in FO.items():
    for i in range(4):
        brk[kind_of(fo)][i] += f['br'][i]
acts_long = sorted((fo for fo in FO if FO[fo]['kind'] == 'act'), key=lambda fo: -FO[fo]['art'])[:16]
deep = []
with open(os.path.join(B, 'tree.tsv'), encoding='utf-8') as fh:
    for line in fh:
        p = line.split('\t', 1)[0]
        m = re.search(r'/art-(\d+(?:-\d+){3})\.md$', p)
        if m and p.startswith('act/'):
            deep.append([split_law(p)[0], m.group(1)])
share = {fo: sum(FO[fo]['br'][1:]) / FO[fo]['art'] for fo in FO if FO[fo]['kind'] == 'act' and FO[fo]['art'] >= 100}
OUT['c04'] = {'kinds': brk, 'long': [[fo, short_title(FO[fo]['title']), FO[fo]['art'], FO[fo]['br']] for fo in acts_long],
              'top_share': [[fo, short_title(FO[fo]['title']), FO[fo]['art'], FO[fo]['br']] for fo in sorted(share, key=lambda q: -share[q])[:10]],
              'deep': [[fo, short_title(FO[fo]['title']), n] for fo, n in deep], 'acts100': len(share), 'acts100_half': sum(v >= .5 for v in share.values())}
print('c04 acts', brk['act'], 'deep act articles', len(deep))


# ================================================================== II. a century of amendments, from the supplementary provisions
# Every amending law leaves its supplementary provisions (附則) in the text of each law it amends, and e-Gov keeps them
# there: suppl/h29-44.md in the Civil Code's folder is the 附則 of 平成二十九年法律第四十四号. One file is one pair
# (law in force, amending law). Acts are named <era><year>-<number>; other amending laws carry their day and kind.
def kgroup(fo):
    k = FO[fo]['kind']
    return {'act': 'act', 'cabinet-order': 'co', 'ministerial-ordinance': 'mo', 'rule': 'rule', 'regulation': 'rule', 'pm-decision': 'rule'}.get(k, 'old')


pairs = collections.defaultdict(collections.Counter)          # western year of the amending law -> kind of the amended law -> pairs
acts_y = collections.defaultdict(set)                         # western year -> amending Acts (era, year, number)
AMD = collections.defaultdict(set)                            # amending Act -> folders it amended
for fo, f in FO.items():
    for era, y, md, t, num, sub in f['sup']:
        wy = west(era, y)
        pairs[wy][kgroup(fo)] += 1
        if t == 'ac':
            acts_y[wy].add((era, y, num))
            AMD[(era, y, num)].add(fo)
npairs = sum(sum(v.values()) for v in pairs.values())
YS = list(range(1947, 2027))
OUT['c05'] = {'years': YS, 'pairs': {k: [pairs[y][k] for y in YS] for k in ('act', 'co', 'mo', 'rule', 'old')},
              'acts': [len(acts_y[y]) for y in YS], 'before': sum(sum(v.values()) for y, v in pairs.items() if y < 1947),
              'first': min(pairs), 'n': npairs}
PROFILE.update(pairs=npairs, amending_acts=len(AMD), laws_with_suppl=sum(1 for f in FO.values() if f['sup']))
print('c05 pairs', npairs, 'amending acts named', len(AMD), 'peak', max(YS, key=lambda y: sum(pairs[y].values())))

# the supplementary provisions' headings and first provision: the day an Act was promulgated, and how it set its start
HEAD = re.compile(r'附\s*則\s*（(明治|大正|昭和|平成|令和)([元〇一二三四五六七八九十]+)年([〇一二三四五六七八九十]+)月([〇一二三四五六七八九十]+)日法律第([〇一二三四五六七八九十百千]+)号）')
ACTDATE, START = {}, {}
for o in jl('suppl-heads.jsonl'):
    key = o['p'].rsplit('/', 1)[1][:-3]
    m = re.match(r'^([mtshr])(\d+)-(\d+)$', key)
    k = (m.group(1), int(m.group(2)), int(m.group(3)))
    h = HEAD.search(o['t'])
    if h:
        era, y, mo, d, num = h.groups()
        e = ERA_KANJI[era]
        if (e, kanji_num(y), kanji_num(num)) == k:
            ACTDATE[k] = f'{west(e, kanji_num(y))}-{kanji_num(mo):02d}-{kanji_num(d):02d}'
    START[k] = o['t']


def start_rule(t):
    """how an Act's supplementary provisions set the day it takes effect, read from the first sentence that says so
    (parentheses removed first, the part after ただし left out): on promulgation, 20 days after it (the general rule of
    法の適用に関する通則法 第二条), another fixed period after it, on a date it names, on a day a Cabinet Order sets, or on
    the day another law or a treaty takes effect"""
    body = re.sub(r'^#[^\n]*\n', '', t)
    prev = None
    while prev != body:
        prev, body = body, re.sub(r'（[^（）]*）', '', body)
    m = re.search(r'(この法律|本法|此ノ法律|此法律)[^。]*?(施行|之ヲ定ム)[^。]*。', body)
    if not m:
        return 'none', ''
    s = m.group(0).split('ただし')[0].split('但シ')[0]
    if re.search(r'(政令|勅令)(で|ヲ以テ|を以て)', s):
        return 'cab', s
    if re.search(r'起算して二十日を経過した日|起算シ二十日ヲ経過シタル日', s):
        return 'd20', s
    if re.search(r'(起算して|公布の後)[^。]*?(日|月|年|週間|箇月|ヶ月)を経過した日|起算シ[^。]*?経過シタル日', s):
        return 'period', s
    if re.search(r'公布の日から、?(これを)?施行|公布ノ日ヨリ(之ヲ)?施行', s):
        return 'prom', s
    if re.search(r'(明治|大正|昭和|平成|令和)[元〇一二三四五六七八九十]+年[〇一二三四五六七八九十]+月[〇一二三四五六七八九十]+日(から|ヨリ)', s):
        return 'fixed', s
    if re.search(r'施行の日|施行日|効力を生ずる日|効力発生の日|効力を生ずる時', s):
        return 'linked', s
    return 'other', s


rule_dec = collections.defaultdict(collections.Counter)
rule_ex = collections.defaultdict(list)
for k, t in START.items():
    r_, s = start_rule(t)
    wy = west(k[0], k[1])
    dec = 0 if wy < 1947 else 1950 if wy < 1960 else wy // 10 * 10      # 1950 stands for 1947-1959
    rule_dec[dec][r_] += 1
    if len(rule_ex[r_]) < 6:
        rule_ex[r_].append(s[:70])
DECS = list(range(1950, 2030, 10))
OUT['c08'] = {'decs': DECS, 'rules': {d: dict(rule_dec[d]) for d in DECS}, 'n': len(START), 'pre1947': dict(rule_dec[0])}
print('c08', {d: dict(rule_dec[d]) for d in DECS})
for k_, v in rule_ex.items():
    print('  ', k_, v[:4])

# the amending Acts that reached the most laws in force; their titles where the repository holds them
TITLE_OF = {}
for x in LAWS.values():
    TITLE_OF[x['law_id']] = x['title']
for r in REV:
    if r['law_id'] and r['title'] and not TITLE_OF.get(r['law_id']):
        TITLE_OF[r['law_id']] = r['title']
ERA_DIGIT = {v: k for k, v in ERA_OF_DIGIT.items()}
ERA_NAME = {'m': '明治', 't': '大正', 's': '昭和', 'h': '平成', 'r': '令和'}


def act_ids(k):
    pre, suf = f'{ERA_DIGIT[k[0]]}{k[1]:02d}AC', f'{k[2]:03d}'
    return [i for i in TITLE_OF if len(i) == 15 and i.startswith(pre) and i.endswith(suf)]


top = sorted(AMD, key=lambda k: (-len(AMD[k]), k))[:16]
rows = []
for k in top:
    fos = AMD[k]
    ids_ = act_ids(k)
    title = next((TITLE_OF[i] for i in ids_ if TITLE_OF[i]), '')
    oldest = min(fos, key=lambda fo: (FO[fo]['year'], fo))
    rows.append({'k': f'{k[0]}{k[1]}-{k[2]}', 'era': k[0], 'ey': k[1], 'no': k[2], 'year': west(k[0], k[1]), 'title': title, 'n': len(fos),
                 'by': dict(collections.Counter(kgroup(fo) for fo in fos)), 'eras': dict(collections.Counter(FO[fo]['era'] for fo in fos)), 'date': ACTDATE.get(k, ''), 'start': start_rule(START.get(k, ''))[1][:160],
                 'inforce': any(i in LAWS for i in ids_), 'oldest': [oldest, short_title(FO[oldest]['title']), FO[oldest]['year']]})
OUT['c06'] = {'rows': rows, 'acts_in_force': sum(1 for f in FO.values() if f['kind'] == 'act'),
              'over100': sum(1 for v in AMD.values() if len(v) >= 100), 'over10': sum(1 for v in AMD.values() if len(v) >= 10), 'n': len(AMD)}
print('c06', [(r['k'], r['n'], r['title'][:20], r['date']) for r in rows[:8]])

# the Acts that keep the supplementary provisions of the most amending laws, by decade of the amending law
DEC7 = list(range(1940, 2030, 10))
acts = [fo for fo in FO if FO[fo]['kind'] == 'act']
most = sorted(acts, key=lambda fo: (-len(FO[fo]['sup']), fo))[:20]
OUT['c07'] = {'decs': DEC7, 'rows': [{'fo': fo, 't': short_title(FO[fo]['title']), 'num': FO[fo]['num'], 'year': FO[fo]['year'], 'n': len(FO[fo]['sup']),
                                       'v': [sum(1 for s in FO[fo]['sup'] if west(s[0], s[1]) // 10 * 10 == d) for d in DEC7],
                                       'before': sum(1 for s in FO[fo]['sup'] if west(s[0], s[1]) < 1940), 'art': FO[fo]['art']} for fo in most],
              'dist': [sum(1 for fo in acts if lo <= len(FO[fo]['sup']) <= hi) for lo, hi in ((0, 0), (1, 4), (5, 19), (20, 99), (100, 10 ** 6))],
              'acts': len(acts), 'median': statistics.median(len(FO[fo]['sup']) for fo in acts)}
print('c07', [(r['t'][:12], r['n']) for r in OUT['c07']['rows'][:6]], OUT['c07']['dist'], OUT['c07']['median'])


# ================================================================== III. the calendar of entry into force (e-Gov's revision record)
# A version made by a named law ("in force", or a law's own first text, "enacted"); e-Gov's labelled first texts and the
# texts published alone are left out, since no law is named for them. e-Gov adds an amending law's supplementary
# provisions to each law it amends on the day it is promulgated, often long before the amendment itself takes effect:
# a version whose commit writes only files in suppl/ is that, and is left out of the calendar and the delays.
VER = [r for r in REV if r['status'] == 'enacted' or (r['status'] == 'in force' and r['cls'] == 'text')]
SUPONLY = [r for r in REV if r['status'] == 'in force' and r['cls'] == 'suppl']
PROFILE.update(ver_text=len(VER), ver_suppl=len(SUPONLY), ver_unknown=sum(1 for r in REV if r['status'] == 'in force' and r['cls'] in ('none', 'empty')))
print('versions changing the text', len(VER), 'supplementary provisions only', len(SUPONLY))
FULL = range(2018, 2026)
cal = collections.Counter()
wd_in, wd_pub = [0] * 7, [0] * 7
for r in VER:
    y = int(r['in_force'][:4])
    if y in FULL:
        cal[(int(r['in_force'][5:7]), int(r['in_force'][8:10]))] += 1
        wd_in[D(r['in_force']).weekday()] += 1
        if r['promulgated']:
            wd_pub[D(r['promulgated']).weekday()] += 1
yr_share = []
for y in range(2017, 2027):
    rs = [r for r in VER if r['in_force'][:4] == str(y)]
    yr_share.append([y, len(rs), sum(r['in_force'][5:] == '04-01' for r in rs), sum(r['in_force'][5:] == '01-01' for r in rs), sum(r['in_force'][8:] == '01' for r in rs)])
top_days = collections.Counter(r['in_force'] for r in VER).most_common(12)
lead = {}
for d, n in top_days:
    c_ = collections.Counter((r['law_num'], r['title']) for r in VER if r['in_force'] == d)
    lead[d] = [[k[0], k[1], v] for k, v in c_.most_common(2)] + [len({r['fo'] for r in VER if r['in_force'] == d})]
OUT['c09'] = {'cal': [[m, d_, n] for (m, d_), n in sorted(cal.items())], 'wd_in': wd_in, 'wd_pub': wd_pub, 'years': yr_share,
              'top': [[d, n, lead[d]] for d, n in top_days], 'n': sum(cal.values())}
print('c09', OUT['c09']['n'], 'apr1', cal[(4, 1)], round(100 * cal[(4, 1)] / sum(cal.values()), 1), 'top', top_days[:4])

# 10. from promulgation to entry into force, by kind of amending law
AK = ['act', 'cabinet-order', 'ministerial-ordinance', 'rule']
BK = [(0, 0), (1, 30), (31, 91), (92, 182), (183, 365), (366, 730), (731, 10 ** 6)]
dl = {k: [] for k in AK}
for r in VER:
    if r['status'] != 'in force' or not r['promulgated']:
        continue
    k = akind(r['law_id'])
    if k in dl:
        dl[k].append((D(r['in_force']) - D(r['promulgated'])).days)
act_days = collections.Counter(dl['act'])
spikes = []
for d_, n in act_days.most_common(14):
    c_ = collections.Counter(r['law_num'] for r in VER if r['status'] == 'in force' and r['promulgated'] and akind(r['law_id']) == 'act' and (D(r['in_force']) - D(r['promulgated'])).days == d_)
    spikes.append([d_, n, c_.most_common(1)[0]])
stages = collections.defaultdict(set)
for r in REV:
    if akind(r['law_id']) == 'act' and ((r['status'] == 'in force' and r['cls'] == 'text') or r['status'] in ST_FUT) and r['in_force'][:4] < '2100':
        stages[r['law_id']].add(r['in_force'])
OUT['c10'] = {'buckets': {k: [sum(1 for v in dl[k] if lo <= v <= hi) for lo, hi in BK] for k in AK}, 'neg': {k: sum(1 for v in dl[k] if v < 0) for k in AK},
              'med': {k: statistics.median(dl[k]) for k in AK if dl[k]}, 'n': {k: len(dl[k]) for k in AK},
              'acthist': sorted([d_, n] for d_, n in act_days.items() if 0 <= d_ <= 1200), 'spikes': spikes,
              'stages': collections.Counter(min(len(v), 10) for v in stages.values()), 'acts': len(stages),
              'maxstage': max(([len(v), k] for k, v in stages.items()), key=lambda q: q[0])}
OUT['c10']['maxstage'] += [TITLE_OF.get(OUT['c10']['maxstage'][1], ''), next((r['law_num'] for r in REV if r['law_id'] == OUT['c10']['maxstage'][1]), '')]
print('c10', OUT['c10']['buckets'], OUT['c10']['med'], spikes[:6])

# 11. the annual tax act: 所得税法等の一部を改正する法律, each year at the end of March
tax = collections.defaultdict(list)
for r in REV:
    if r['law_id'] and re.match(r'^所得税法等の一部を改正する(等の)?法律$', r['title']) and ((r['status'] == 'in force' and r['cls'] == 'text') or r['status'] in ST_FUT):
        tax[(r['law_id'], r['law_num'], r['promulgated'])].append(r)
rows = []
for (lid, num, prom), rs in sorted(tax.items(), key=lambda kv: kv[0][2]):
    if not prom or int(prom[:4]) < 2018:
        continue
    days = collections.Counter(r['in_force'] for r in rs if r['in_force'][:4] < '2100')
    rows.append({'lid': lid, 'num': num, 'prom': prom, 'n': len(rs), 'laws': len({r['fo'] for r in rs}), 'days': sorted(days.items()),
                 'fut': sum(r['status'] != 'in force' for r in rs), 'nodate': sum(r['in_force'][:4] >= '2100' for r in rs),
                 'laws_l': sorted({short_title(FO[r['fo']]['title']) for r in rs})[:40]})
OUT['c11'] = {'rows': rows}
print('c11', [(r['num'], r['prom'], r['n'], r['laws'], len(r['days']), r['days'][-1][0]) for r in rows])

# 12. promulgated, not yet in force (the branch mishiko holds them; laws.csv lists them with the day they will take effect)
FUT = [r for r in REV if r['status'] in ST_FUT]
mon = collections.defaultdict(collections.Counter)
for r in FUT:
    key = 'none' if r['in_force'][:4] >= '2100' else r['in_force'][:7]
    mon[key]['fixed' if r['status'] == 'not yet in force' else 'latest'] += 1
waiting = sorted(FUT, key=lambda r: (r['promulgated'] or '9999', r['law_num']))
seen, oldest = set(), []
for r in waiting:
    if r['law_num'] in seen:
        continue
    seen.add(r['law_num'])
    oldest.append([r['law_num'], r['title'], r['promulgated'], r['in_force'], r['status'], sum(1 for q in FUT if q['law_num'] == r['law_num'])])
    if len(oldest) >= 8:
        break
day_top = collections.Counter(r['in_force'] for r in FUT if r['in_force'][:4] < '2100').most_common(6)
OUT['c12'] = {'months': {k: dict(v) for k, v in sorted(mon.items())}, 'n': len(FUT), 'oldest': oldest, 'top': day_top,
              'laws': len({r['fo'] for r in FUT}), 'by_kind': dict(collections.Counter(akind(r['law_id']) for r in FUT)),
              'acts': len({r['law_id'] for r in FUT if akind(r['law_id']) == 'act'})}
print('c12', len(FUT), day_top[:3], oldest[:3])


# ================================================================== IV. the Diet, the Cabinet and the ministries
# 13. Act numbers: Acts are numbered from 1 in each year of an era; the highest number the repository names for a year
EYS = collections.defaultdict(set)          # (era, year) -> Act numbers named anywhere in the repository
INF = collections.defaultdict(set)          # (era, year) -> numbers of the Acts in force
for k in AMD:
    EYS[(k[0], k[1])].add(k[2])
ACT_IDS = set()
for x in LAWS.values():
    if re.match(r'^\d{3}AC\d{10}$', x['law_id']):
        ACT_IDS.add(x['law_id'])
        e, y, n_ = ERA_OF_DIGIT[x['law_id'][0]], int(x['law_id'][1:3]), int(x['law_id'][-3:])
        INF[(e, y)].add(n_)
for r in REV:
    for i in (r['law_id'], r['target']):
        if re.match(r'^\d{3}AC\d{10}$', i or ''):
            ACT_IDS.add(i)
for i in ACT_IDS:
    EYS[(ERA_OF_DIGIT[i[0]], int(i[1:3]))].add(int(i[-3:]))
nums = []
for (e, y), s in EYS.items():
    wy = west(e, y)
    if wy >= 1947:
        nums.append([wy, e, y, max(s), len(s), len(INF[(e, y)])])
nums.sort(key=lambda q: (q[0], ERA_START[q[1]]))
OUT['c13'] = {'rows': nums, 'full_years': [q[0] for q in nums if q[4] == q[3]],
              'min_cover_2000': min(q[4] / q[3] for q in nums if q[0] >= 2000), 'min_cover_2016': min(q[4] / q[3] for q in nums if q[0] >= 2016)}
print('c13', [q for q in nums if q[0] in (1947, 1989, 2019, 2025)], 'every number named in', OUT['c13']['full_years'], round(OUT['c13']['min_cover_2000'], 3))

# 14. the day each Act was promulgated: from its supplementary provisions' heading, or from e-Gov's record
for r in REV:
    for i, d_ in ((r['law_id'], r['promulgated']),):
        if re.match(r'^\d{3}AC\d{10}$', i or '') and d_:
            ACTDATE.setdefault((ERA_OF_DIGIT[i[0]], int(i[1:3]), int(i[-3:])), d_)
cm = collections.Counter()
for k, d_ in ACTDATE.items():
    if int(d_[:4]) >= 1947:
        cm[(int(d_[:4]), int(d_[5:7]))] += 1
cover = {}
for q in nums:
    cover.setdefault(q[0], [0, 0])
    cover[q[0]][1] += q[3]
for k, d_ in ACTDATE.items():
    wy = west(k[0], k[1])
    if wy in cover:
        cover[wy][0] += 1
OUT['c14'] = {'cells': [[y, m, n] for (y, m), n in sorted(cm.items())], 'cover': sorted([y, a_, b_] for y, (a_, b_) in cover.items()), 'n': sum(cm.values())}
print('c14 dated acts since 1947', sum(cm.values()), 'by month', [sum(n for (y, m), n in cm.items() if m == mm) for mm in range(1, 13)])

# 15. who introduced the Acts: the Cabinet (閣法) or members of either House (衆法, 参法)
dec_in = collections.defaultdict(collections.Counter)
tcls = collections.defaultdict(collections.Counter)


def tclass(t):
    t = re.sub(r'（[^）]*）$', '', t)
    if t.endswith('基本法'):
        return 'kihon'
    if re.search(r'(推進|促進)(法|に関する法律)$', t):
        return 'suishin'
    return 'other'


for x in LAWS.values():
    w = introducer(x['law_id'])
    if not w:
        continue
    fo = LID2FO[x['law_id']]
    dec_in[FO[fo]['year'] // 10 * 10][w] += 1
    tcls[tclass(x['title'])][w] += 1
yr_in = collections.defaultdict(collections.Counter)
for i in ACT_IDS:
    yr_in[west(ERA_OF_DIGIT[i[0]], int(i[1:3]))][introducer(i)] += 1
OUT['c15'] = {'decs': {d: dict(v) for d, v in sorted(dec_in.items())}, 'years': {y: dict(yr_in[y]) for y in range(2014, 2027)},
              'maxnum': {q[0]: q[3] for q in nums if q[0] >= 2014}, 'tcls': {k: dict(v) for k, v in tcls.items()},
              'kihon': sorted([short_title(x['title']), introducer(x['law_id']), FO[LID2FO[x['law_id']]]['year']] for x in LAWS.values() if introducer(x['law_id']) and tclass(x['title']) == 'kihon')}
print('c15', {d: dict(v) for d, v in sorted(dec_in.items())}, {k: dict(v) for k, v in tcls.items()})

# 16. the ministerial ordinances in force, by the ministry that made them (its name is in the ordinance's number)
ISS = collections.defaultdict(lambda: {'n': 0, 'art': 0, 'per': [0] * 5, 'first': 9999, 'last': 0, 'name': collections.Counter()})
PER = [(0, 1946), (1947, 1988), (1989, 2000), (2001, 2018), (2019, 2100)]
joint = 0
for fo, f in FO.items():
    if f['kind'] != 'ministerial-ordinance':
        continue
    if f['issuer'] == 'joint':
        joint += 1
        continue
    s = ISS[f['issuer']]
    s['n'] += 1
    s['art'] += f['art']
    s['first'], s['last'] = min(s['first'], f['year']), max(s['last'], f['year'])
    s['per'][next(i for i, (a_, b_) in enumerate(PER) if a_ <= f['year'] <= b_)] += 1
    m = re.match(r'^(明治|大正|昭和|平成|令和)[元〇一二三四五六七八九十百]+年(.+?)(令|規則|規程)第', f['num'])
    if m:
        s['name'][m.group(2) + m.group(3)] += 1
OUT['c16'] = {'rows': sorted([[k, v['n'], v['art'], v['per'], v['first'], v['last'], v['name'].most_common(1)[0][0] if v['name'] else ''] for k, v in ISS.items()], key=lambda q: -q[1]),
              'joint': joint, 'n': sum(v['n'] for v in ISS.values())}
gone = [q for q in OUT['c16']['rows'] if q[5] <= 2000]
print('c16 single-ministry', OUT['c16']['n'], 'by ministries with nothing after 2000', sum(q[1] for q in gone), [q[6] for q in gone][:12])

# 17. disasters named in the titles of the laws in force
# (災害 also means a workplace accident or an injury on duty: 労働者災害補償, 公務災害, 災害給付 are not counted)
DIS = [('higashi', r'東日本大震災|東北地方太平洋沖地震'), ('genpatsu', r'原子力(発電所の)?事故|放射性物質による環境の汚染|原子力損害'), ('hanshin', r'阪神[・・]淡路大震災'),
       ('kumamoto', r'熊本地震'), ('noto', r'能登半島地震'), ('corona', r'新型コロナウイルス'),
       ('other', r'震災|地震|津波|噴火|火山|豪雨|豪雪|台風|風水害|水害|激甚|被災|防災|災害')]
NOT_DISASTER = re.compile(r'労働者災害|公務災害|労働災害|船員災害|炭鉱災害|鉱山災害|災害補償|災害給付')
dis = collections.defaultdict(collections.Counter)
dlist = collections.defaultdict(list)
for fo, f in FO.items():
    t = f['title']
    for k, p in DIS:
        if re.search(p, t) and not (k == 'other' and NOT_DISASTER.search(t) and not re.search(r'震災|地震|津波|噴火|豪雨|豪雪|台風', t)):
            dis[f['year']][k] += 1
            dlist[k].append([fo, short_title(t), f['year'], f['kind']])
            break
OUT['c17'] = {'years': {y: dict(v) for y, v in sorted(dis.items())}, 'n': {k: len(v) for k, v in dlist.items()},
              'kinds': {k: dict(collections.Counter(q[3] for q in v)) for k, v in dlist.items()},
              'list': {k: sorted(v, key=lambda q: (q[2], q[0]))[:60] for k, v in dlist.items()}}
print('c17', OUT['c17']['n'], {k: v for k, v in OUT['c17']['kinds'].items()})


# ================================================================== V. the Constitution and the codes
CODES = ['constitution/1946', 'act/1896/089', 'act/1899/048', 'act/1907/045', 'act/1996/109', 'act/1948/131', 'act/2005/086']
OLD = {v: k for k, v in P['paths'].items() if v in CODES}           # new folder -> old folder name (minpo, ...)
NEW_OF_OLD = {k: v for v, k in OLD.items()}


def to_new(p):
    head, _, rest = p.partition('/')
    if head in NEW_OF_OLD:
        return NEW_OF_OLD[head] + '/' + rest
    return p


def art_key(name):
    m = re.match(r'^art-(\d+(?:-\d+)*)(?:-to-\d+(?:-\d+)*)?\.md$', name)
    return tuple(int(x) for x in m.group(1).split('-')) if m else None


# the text of every article: 削除 marks an article whose number is kept after its provisions were removed
DEL = re.compile(r'^第[〇一二三四五六七八九十百千]+条(?:の[〇一二三四五六七八九十百千]+)*(?:から第[〇一二三四五六七八九十百千]+条(?:の[〇一二三四五六七八九十百千]+)*まで|及び第[〇一二三四五六七八九十百千]+条(?:の[〇一二三四五六七八九十百千]+)*)?\s*削除$')
ART = {}
for o in jl('codes.jsonl'):
    fo, rest = split_law(o['p'])
    if not art_key(rest[0]):
        continue
    body = [l.strip() for l in o['t'].split('\n') if l.strip() and not l.startswith('#') and not re.match(r'^（[^）]*）$', l.strip())]
    ART[o['p']] = {'del': len(body) == 1 and bool(DEL.match(body[0])), 'head': body[0][:40] if body else ''}
# the last change of each article: the newest In-force day among the commits that wrote its file (e-Gov's first text included)
last = {}
with open(os.path.join(B, 'codes-names.tsv'), encoding='utf-8') as fh:
    for line in fh:
        s, st, p = line.rstrip('\n').split('\t')
        L_ = LOG[s]
        if L_['author'] == 'Lexifina' or st not in 'AM':
            continue
        p = to_new(p)
        d_ = L_['In-force'][:10]
        if p not in last or d_ > last[p][0]:
            last[p] = (d_, L_['author'])
c19 = {}
for fo in CODES:
    arts = sorted((p for p in ART if p.startswith(fo + '/')), key=lambda p: art_key(p.rsplit('/', 1)[1]))
    base = min(last[p][0] for p in arts)
    c19[fo] = {'base': base, 'arts': [[p.rsplit('/', 1)[1][4:-3], last[p][0], re.sub(r' \(.*\)$', '', last[p][1]), int(ART[p]['del'])] for p in arts]}
    print('c19', fo, len(arts), 'base', base, 'deleted', sum(ART[p]['del'] for p in arts), 'changed after base', sum(last[p][0] > base for p in arts))
OUT['c19'] = c19
# the codes' cards and the amending laws whose supplementary provisions they keep
OUT['c18'] = {fo: {'title': FO[fo]['title'], 'num': FO[fo]['num'], 'year': FO[fo]['year'], 'art': FO[fo]['art'], 'br': sum(FO[fo]['br'][1:]),
                   'del': sum(1 for p in ART if p.startswith(fo + '/') and ART[p]['del']), 'pre': FO[fo]['pre'],
                   'sup': sorted([west(s[0], s[1]), s[3], f'{s[0]}{s[1]}-{s[4]}'] for s in FO[fo]['sup']),
                   'versions': LAWS[FO[fo]['lid']]['in_force_versions'], 'first': LAWS[FO[fo]['lid']]['first'], 'last': LAWS[FO[fo]['lid']]['last_in_force'],
                   'future': LAWS[FO[fo]['lid']]['future_versions']} for fo in CODES}

# the Civil Code and the Penal Code since e-Gov's first text: the article files each version wrote, and in which Book
BOOKS = {'act/1896/089': [(1, 174), (175, 398), (399, 724), (725, 881), (882, 1050)], 'act/1907/045': [(1, 72), (73, 264)]}
steps = {}
for fo in ('act/1896/089', 'act/1907/045'):
    per = collections.OrderedDict()
    with open(os.path.join(B, 'codes-names.tsv'), encoding='utf-8') as fh:
        for line in fh:
            s, st, p = line.rstrip('\n').split('\t')
            L_ = LOG[s]
            p = to_new(p)
            if L_['author'] == 'Lexifina' or not p.startswith(fo + '/'):
                continue
            q = per.setdefault(s, {'d': L_['In-force'][:10], 'a': re.sub(r' \(.*\)$', '', L_['author']), 'base': L_['Kind'] == 'baseline' or L_['author'].startswith('e-Gov'),
                                   'A': 0, 'M': 0, 'D': 0, 'sup': 0, 'books': [0] * len(BOOKS[fo])})
            nm = p.rsplit('/', 1)[1]
            k = art_key(nm)
            if '/suppl/' in p:
                q['sup'] += 1
            elif k and '-to-' not in nm:
                # an article file added or rewritten; files deleted, and the files of ranges of deleted articles (e-Gov
                # merged the single 削除 files of 第三十八条から第八十四条まで into one on 2017-06-02), are not changes of text
                q[st] += 1
                if st in 'AM':
                    q['books'][next((i for i, (a_, b_) in enumerate(BOOKS[fo]) if a_ <= k[0] <= b_), len(BOOKS[fo]) - 1)] += 1
    rows = sorted(per.values(), key=lambda q: q['d'])
    steps[fo] = [[q['d'], q['a'], q['A'], q['M'], q['D'], q['sup'], q['books'], int(q['base'])] for q in rows]
    print('c20', fo, len(rows), 'article changes after the first text', sum(q['A'] + q['M'] + q['D'] for q in rows if not q['base']))
OUT['c20'] = steps

# ------------------------------------------------------------------ out
OUT['profile'] = PROFILE
with open(os.path.join(B, 'data.json'), 'w', encoding='utf-8') as fh:
    json.dump({'charts': {k: v for k, v in OUT.items() if k != 'profile'}, 'profile': PROFILE}, fh, ensure_ascii=False, separators=(',', ':'))
print('profile', PROFILE)
print('data.json', os.path.getsize(os.path.join(B, 'data.json')))
