# Japanese law in 20 charts

[日本語](README.md)

Charts on every country's law, from the whole of global-law: [global-law visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations). These are the charts on Japan alone.

Twenty charts on Japanese law, drawn only from the data in this repository: the 8,982 laws in force in e-Gov 法令検索 (the Constitution, 2,078 Acts, 2,320 Cabinet Orders, 4,085 ministerial ordinances and more), one file per article; the 48,672 versions in force and 1,182 promulgated but not yet in force that e-Gov's revision record holds; and the 151,354 supplementary provisions (附則) that amending laws have left in the text of the laws they amended.

Open [`20-no-gurafu-de-miru-nihon-no-horei.html`](20-no-gurafu-de-miru-nihon-no-horei.html) in a browser. The page is one file with all its data inside; it loads only the d3 library and its fonts from the web. The controls at the top right switch the language (Japanese or English) and the theme (light or dark). Each chart names its data path in the repository, its record count and its limits, and has a table of every number under it. Hover over a mark for the exact values.

The charts are descriptive: they show what the record holds, not why.

## The charts

### I. The law in force

#### 1. 8,982 laws in force

The laws in force by kind, with their articles: 2,078 Acts against 6,405 Cabinet Orders and ministerial ordinances; the laws with the most articles (the Local Tax Act, 1,314).

![8,982 laws in force](stills/en/01.png)

#### 2. From Meiji to Reiwa

The laws in force by the year and era of their number: 49% Heisei, 11% Reiwa, and 165 numbered in the Meiji and Taishō eras; the oldest is the Calendar Reform Proclamation of 1872.

![From Meiji to Reiwa](stills/en/02.png)

#### 3. Katakana law

224 of the 263 laws in force numbered before 1947 still have articles in the pre-war katakana style (71 of them Acts); the Civil, Penal and Commercial Codes now read in hiragana.

![Katakana law](stills/en/03.png)

#### 4. Branch numbers

Articles numbered like "Article 14-2" (第十四条の二): 23% of the articles of Acts; 875 of the 1,101 articles of the Financial Instruments and Exchange Act.

![Branch numbers](stills/en/04.png)

#### 5. Disasters in law titles

The laws in force whose title names a disaster: 99 name the Great East Japan Earthquake, 88 of them numbered in 2011; the Great Hanshin-Awaji Earthquake, the Kumamoto and Noto Peninsula Earthquakes, COVID-19.

![Disasters in law titles](stills/en/05.png)

### II. A century of amendments

#### 6. The record of amendment

The 151,354 supplementary provisions of amending laws kept in the laws in force, by the year of the amending law: the most from 2000 (5,372).

![The record of amendment](stills/en/06.png)

#### 7. Omnibus Acts

The 15 Acts whose supplementary provisions sit in the most laws in force: 883 for Act No. 160 of 1999, 845 for Act No. 68 of 2022 (40% of the Acts in force).

![Omnibus Acts](stills/en/07.png)

#### 8. The most amended Acts

The 20 Acts that keep the most amending laws' provisions, by decade: 940 for the Local Tax Act; the median Act keeps 9.

![The most amended Acts](stills/en/08.png)

#### 9. How Acts set their start

The first provision of each amending Act's supplementary provisions, classified: Acts that leave their start to a Cabinet Order rose from 11% in 1947–1959 to 42% since 2020.

![How Acts set their start](stills/en/09.png)

### III. When law takes effect

#### 10. 1 April

The days on which versions took effect in 2018–2025, on a calendar: 29.2% on 1 April; the weekdays of promulgation and of entry into force.

![1 April](stills/en/10.png)

#### 11. From promulgation to entry into force

The days from promulgation to entry into force, by kind of amending law: a median of 283 days for versions written by Acts, 9 for Cabinet Orders, 2 for ministerial ordinances.

![From promulgation to entry into force](stills/en/11.png)

#### 12. The tax Act of every end of March

The Acts Partially Amending the Income Tax Act etc. of 2018–2026: all nine promulgated between 29 and 31 March, 40% of their versions in force on 1 April.

![The tax Act of every end of March](stills/en/12.png)

#### 13. Promulgated, not yet in force

The 1,182 versions waiting, by the month they are due: 304 on 1 April 2027; provisions promulgated in 1976 still have no day.

![Promulgated, not yet in force](stills/en/13.png)

### IV. The Diet, the Cabinet and the ministries

#### 14. Act numbers

The highest Act number of each year and the Acts in force: up to No. 358 in 1952 and No. 96 in 2025; in 2019, Nos. 1–20 of Heisei 31 and 1–74 of Reiwa 1.

![Act numbers](stills/en/14.png)

#### 15. The month Acts are promulgated

The 7,408 Acts since 1947 whose day of promulgation is known, by year and month: 23% in June, 19% in May.

![The month Acts are promulgated](stills/en/15.png)

#### 16. Members' bills

Cabinet bills (閣法) and members' bills of either House (衆法, 参法): 44% of the Acts in force numbered in the 2010s, and 35 of the 54 Basic Acts, began as members' bills.

![Members' bills](stills/en/16.png)

#### 17. Who made the ministerial ordinances

The ordinances in force by the ministry that made them: 1,527 of the 3,291 made by a single ministry come from ministries whose ordinances stop by 2000.

![Who made the ministerial ordinances](stills/en/17.png)

### V. The Constitution and the codes

#### 18. The Constitution and the codes

The Constitution keeps its text of 3 May 1947; the six codes keep the supplementary provisions of their amending laws (Civil Code 67, Commercial Code 66, Code of Criminal Procedure 63).

![The Constitution and the codes](stills/en/18.png)

#### 19. The Constitution and the codes article by article

When each article was last changed: since e-Gov's record began, 446 articles of the Civil Code and 190 of the Penal Code have been rewritten.

![The Constitution and the codes article by article](stills/en/19.png)

#### 20. A decade of the Civil and Penal Codes

The times their articles were changed, cumulated: 465 for the Civil Code, 218 for the Penal Code; the largest step, Act No. 44 of 2017 on 1 April 2020 (323 articles).

![A decade of the Civil and Penal Codes](stills/en/20.png)

## Data

As of commit `85525f9094`; e-Gov's data as of 2 November 2026.

| Dataset | Where in the repository | Records | Coverage |
| --- | --- | ---: | --- |
| Laws in force | `<kind>/<year>/<number>/` (ministerial ordinances and rules by issuer) | 8,982 laws, 239,810 articles | e-Gov's laws in force, one file per article; repealed laws are not included |
| Revisions | `laws.csv`, git history (`In-force:`, `Promulgated:`) | 49,854 versions (48,672 in force, 1,182 not yet) | from 2016–2017 for most laws; 3,539 laws hold only their text in force |
| Supplementary provisions | `<law>/suppl/<amending law>.md` | 151,354, from 7,421 amending Acts | the supplementary provisions amending laws left in each law's text, back to an amending law of 1900 |
| Texts read | supplementary provisions, article files | 7,421 provisions, 7,440 files judged in laws numbered before 1947, 4,095 articles of the Constitution and the codes | one file of supplementary provisions per amending Act (its promulgation day and start rule), every article of the laws numbered before 1947, every article of the Constitution and the six codes |

## Limits

- **Only laws in force.** Repealed laws are not included, so counts by year or era are of the laws that remain.
- **e-Gov's revision record starts in 2016–2017 for most laws.** Charts 10–13, 19 and 20 cover that period only. 3,539 laws hold only their text in force so far.
- **The supplementary provisions are those e-Gov keeps in the text.** Some laws do not keep those of old amendments (the Civil Code's start in 1926).
- **Categories are read from names, titles and texts.** Who introduced an Act (its law ID), how an Act sets its start, the katakana style, disaster names and the form of a title follow the rules in `src/prep.py`. Whatever no rule recognises counts as "other".
- **A version is one that changes a law's text.** Versions that only add an amending law's supplementary provisions are left out of charts 10–12, and two amendments of one law on one day make one version.
- **2026 is partial** (to 2 November) and drawn lighter.

## Rebuilding

```sh
python visualisations/src/make.py            # history, tree, supplementary provisions and texts -> src/.build/ -> 20-no-gurafu-de-miru-nihon-no-horei.html
node visualisations/src/stills.cjs           # images for these READMEs (needs Playwright; PLAYWRIGHT=<path> if not global)
```

`make.py` reads everything from git objects, so it also works in a blobless (`--filter=blob:none`) or `--no-checkout` clone, where it downloads only one file of supplementary provisions per amending Act, the articles of the laws numbered before 1947, the articles of the Constitution and the six codes, and the tables (`laws.csv`, `corpus.json`, `data/laws.json`, `data/paths.json`, `data/revisions.json`): about 20,000 small files. It reads `origin/main` (or `HEAD`) by default; `--ref` picks another branch or commit. It writes nothing into the repository except the page and the `src/.build/` folder (which git ignores).

| File | What it does |
| --- | --- |
| `src/make.py` | extracts the history, the tree, the supplementary provisions and the texts into `src/.build/`, then runs `prep.py` and `build.py` |
| `src/prep.py` | computes every number for the 20 charts and the data profile into `src/.build/data.json` |
| `src/page.tpl.html` | the page: text in both languages, the charts (d3), the tables |
| `src/build.py` | puts `data.json` into the template and writes the page |
| `src/stills.cjs` | draws each chart as a PNG into `stills/ja/` and `stills/en/` |

## Source and licence

The legal text and its revisions are from e-Gov 法令検索 (Digital Agency), used under the Public Data License 1.0 (PDL1.0). Laws and regulations are not protected by copyright in Japan (著作権法 第十三条第一号). See [`LICENSE`](../LICENSE).
