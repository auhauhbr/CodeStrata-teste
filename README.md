# CodeStrata

**Dig through the history of software — and the web.**

[![CI](https://github.com/JeffersonSantosKn/CodeStrata/actions/workflows/tests.yml/badge.svg)](https://github.com/JeffersonSantosKn/CodeStrata/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-D8A84E)

CodeStrata is a software-archaeology CLI that reconstructs how technology stacks changed over time. It can excavate **Git history** from an open-source repository or inspect **historical website snapshots** from the Wayback Machine.

The tool is intentionally evidence-first. A `react` dependency in `package.json` is strong evidence; a source signature is weaker. On archived websites, an explicit `jquery-1.12.4.min.js` asset is evidence for jQuery, while invisible server-side technology is left unknown instead of guessed.

## Two excavation modes

### 1. Git archaeology

Give CodeStrata a local repository or remote Git URL. It samples historical commits, reads files directly from Git objects, assigns evidence scores, and builds a timeline of technologies appearing, disappearing, and changing versions.

```bash
codestrata analyze https://github.com/owner/legacy-app.git \
  --granularity year \
  --html reports/git-history.html
```

Example output:

```text
CodeStrata — software archaeology
Target: https://github.com/example/legacy-app.git
History: 1842 commits · 8 snapshots · 14 events

Timeline
--------
2014-02-08  + jQuery ^1.11.0  [31fb107a]
2014-02-08  + PHP ^5.5        [31fb107a]
2017-09-12  + Bootstrap ^3.3  [9dc72c81]
2020-05-20  + React ^16.8.0   [94e32db1]
2020-05-20  + Webpack ^4.0    [94e32db1]
2021-01-14  - jQuery          [aa0184c2]
2023-09-01  + Docker          [fc47d09b]
```

### 2. Web archaeology

Give CodeStrata a public website URL. It asks the Internet Archive CDX index for historical HTML captures, samples representative eras, downloads only those pages, and looks for client-visible technology evidence.

```bash
codestrata web https://example.com \
  --from 2005 \
  --to 2025 \
  --granularity year \
  --html reports/web-history.html
```

Typical historical signals include jQuery, Bootstrap, Flash, AngularJS, React, Vue, Next.js and WordPress. CodeStrata does **not** pretend it can see a hidden PHP/Laravel/Django backend from archived HTML alone.

## Features

- Analyze a **local Git repository or remote Git URL**.
- Analyze a **public website through Wayback Machine snapshots**.
- Sample history by **year, quarter, or month** instead of checking every commit/capture blindly.
- Detect technologies from manifests, lockfiles, config files, source signatures, file structure, and archived HTML assets.
- Assign a **0–100 confidence score** from inspectable evidence.
- Track **introduced**, **removed**, and **version-changed** technologies.
- Inspect a single Git commit/ref with `snapshot`.
- Restrict website archaeology with `--from` / `--to` years.
- Export machine-readable **JSON**.
- Export a dependency-free **HTML report** with timeline and evidence details.
- Never execute code from the repositories or web pages being analyzed.

## Supported Git signals

| Area | Technologies / signals |
| --- | --- |
| Frontend | jQuery, React, Vue, Angular |
| CSS | Bootstrap, Tailwind CSS |
| JavaScript frameworks | Next.js, Express |
| PHP | PHP runtime constraints, Laravel, Symfony, Composer |
| Python | Python version pins, Django, Flask, FastAPI |
| Ruby | Ruby, Ruby on Rails |
| Languages | JavaScript, TypeScript, PHP, Python, Ruby, Java, Go, Rust |
| Build tooling | Webpack, Vite, Grunt, Gulp |
| Package managers | npm, Yarn, pnpm, Composer |
| Infrastructure | Docker, Docker Compose |
| Runtime | Node.js engine constraints |

## Supported archived-web signals

| Era / ecosystem | Detectable evidence |
| --- | --- |
| Legacy JavaScript | jQuery, MooTools, Prototype.js, Modernizr, RequireJS |
| Legacy browser platform | Adobe Flash / SWF |
| CSS | Bootstrap, Tailwind CSS asset markers |
| Frontend | React, Vue, AngularJS, Angular, Alpine.js, Svelte |
| Frameworks | Next.js |
| CMS | WordPress |

Archived-web detection is intentionally conservative: these are **client-visible** signals. Absence of a signal does not prove a technology was absent from the server.

## Install

Requirements: Python 3.11+ and Git. Web archaeology additionally needs internet access to `web.archive.org`.

```bash
git clone https://github.com/JeffersonSantosKn/CodeStrata.git
cd CodeStrata
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

You can also run directly from a checkout:

```bash
PYTHONPATH=src python -m codestrata --help
```

## Git usage

Analyze the current repository:

```bash
codestrata analyze .
```

Use more temporal resolution:

```bash
codestrata analyze . --granularity quarter --max-snapshots 32
```

Export both formats:

```bash
codestrata analyze . \
  --json reports/history.json \
  --html reports/history.html
```

Inspect one historical commit:

```bash
codestrata snapshot . --ref v2.0.0
```

Tune conservatism:

```bash
codestrata analyze . --min-confidence 60
```

## Web usage

Excavate the full available history:

```bash
codestrata web https://example.com
```

Limit the era and generate reports:

```bash
codestrata web https://example.com \
  --from 2000 \
  --to 2020 \
  --granularity year \
  --max-snapshots 20 \
  --json reports/example.json \
  --html reports/example.html
```

A finer `quarter` or `month` granularity can reveal migrations inside the same year, at the cost of more archive requests.

## How confidence works

A detector emits evidence rather than a final yes/no answer. The engine groups evidence by technology and caps accumulated confidence at 100.

```text
React
├─ package.json: dependency "react"       +80
├─ src/main.tsx: React import signature    +20
└─ confidence                              100%
```

A generic source pattern on its own may score only 20 and be hidden by the default `--min-confidence 40`. A manifest, dedicated config file, lockfile, or explicit archived asset can cross the threshold by itself.

Evidence is retained in JSON and displayed in HTML, including path/URL, reason, weight, and version hint when one is visible.

## Historical sampling

Checking every commit of a large repository — or downloading every Wayback capture — is both slow and redundant. CodeStrata groups history into buckets:

```text
--granularity year      # default
--granularity quarter
--granularity month
```

The newest state is preserved and `--max-snapshots` bounds work. The selected snapshot gives a **time bound**, not necessarily the exact commit or second where a technology first appeared.

## Architecture

```text
                  ┌──────────────────┐
Git repo ────────►│ Git sampler      │──┐
                  └──────────────────┘  │
                                        ├─► evidence ─► confidence ─► timeline
Website URL ─────►┌──────────────────┐  │                         │
                  │ Wayback CDX      │──┘                         ├─ terminal
                  │ + snapshot sampler│                            ├─ JSON
                  └──────────────────┘                             └─ HTML
```

Core modules:

- `git.py` — safe, read-only Git object access and temporary remote clones.
- `sampling.py` — representative Git commit sampling.
- `detectors/` — repository evidence producers.
- `wayback.py` — Internet Archive CDX/snapshot client.
- `web_sampling.py` — archive capture sampling.
- `web_detector.py` — archived HTML technology evidence.
- `analyzer.py` / `website_analyzer.py` — orchestration.
- `timeline.py` — introduced/removed/version-change reconstruction.
- `exporters/` — JSON and standalone HTML reports.
- `cli.py` — command-line interface.

## Important limitations

CodeStrata reports evidence, not omniscience. Git manifest versions may be constraints such as `^18.0` rather than exact installed packages. Time sampling may miss a short-lived technology between selected snapshots. Wayback pages can be missing, rate-limited, partially archived, or rewritten by the archive.

Most importantly, a public HTML snapshot generally cannot prove which server-side language, framework, database, or infrastructure produced it. CodeStrata leaves those unknown unless the analyzed Git source contains evidence.

## Tests

The test suite uses only the Python standard library. It includes:

- detector confidence tests;
- a temporary Git history that migrates jQuery → React/Webpack → Docker;
- sampling/export tests;
- a mocked Wayback history that migrates jQuery/Flash → Bootstrap/jQuery → Next.js/React.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Roadmap

- Binary-search the exact introduction/removal commit after a coarse Git transition is found.
- More ecosystems: Spring, Maven/Gradle, ASP.NET, SvelteKit, Astro, Nuxt, databases and CI providers.
- Parse lockfiles for exact dependency versions where practical.
- Monorepo-aware timelines by workspace.
- Better archive retry/backoff and optional local snapshot cache.
- Interactive web UI built on the existing JSON report format.
- Compare two repositories/sites side by side.

## Contributing

Detector contributions are especially welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the expected evidence/scoring style.

## License

MIT. See [`LICENSE`](LICENSE).
