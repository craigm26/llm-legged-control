#!/usr/bin/env python3
"""Build index.html from the experiment outputs in duckbench/sim/malik."""
import json, csv, html, os, shutil, hashlib, subprocess
SRC = os.path.expanduser('~/projects/duckbench/sim/malik')
OUT = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(f'{SRC}/results.json'))
import datetime; DATE = datetime.datetime.fromisoformat(R['date'].replace('Z','+00:00')).astimezone().strftime('%Y-%m-%d')
NEU = json.load(open(f'{SRC}/neutral.json'))
rows = list(csv.reader(open(f'{SRC}/commands_open_loop.csv')))
os.makedirs(f'{OUT}/data', exist_ok=True); os.makedirs(f'{OUT}/sim', exist_ok=True)
for f in ['results.json', 'commands_open_loop.csv', 'neutral.json', 'run.log']: shutil.copy(f'{SRC}/{f}', f'{OUT}/data/{f}')
for f in ['lib.mjs', 'run.mjs', 'probe.mjs', 'diag.mjs', 'diag2.mjs']: shutil.copy(f'{SRC}/{f}', f'{OUT}/sim/{f}')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
DB = os.path.expanduser('~/projects/duckbench')
duckbench_sha = subprocess.check_output(['git', '-C', DB, 'rev-parse', 'HEAD']).decode().strip()

TERR = list(R['terrains'].keys())
CTRL = []
for r in R['results']:
    if r['controller'] not in [c['id'] for c in CTRL]: CTRL.append({'id': r['controller'], 'label': r['label']})
res = {(r['controller'], r['terrain']): r for r in R['results']}
esc = html.escape

# ── figure 1: small multiples, standing out of 10 per terrain, one panel per controller
def fig_standing():
    W, H, pad, pb = 300, 165, 28, 40
    bw = (W - 2 * pad) / len(TERR)
    panels = []
    for c in CTRL:
        bars = []
        for i, t in enumerate(TERR):
            r = res[(c['id'], t)]; n = r['standing']
            h = (H - pad - pb) * n / 10
            x = pad + i * bw + 4; y = H - pb - h
            tip = f"{esc(c['label'])} on {t}: {n} of 10 standing at 6 s, median travelled {r['travelledMedian']:.2f} m, walked off the bank in {r['leftBank']} runs"
            bars.append(f'<rect class="bar" x="{x:.1f}" y="{y:.1f}" width="{bw-8:.1f}" height="{h:.1f}" rx="3"><title>{tip}</title></rect>')
            bars.append(f'<text class="val" x="{x + (bw-8)/2:.1f}" y="{y-3:.1f}" text-anchor="middle">{n}</text>')
            cx = x + (bw-8)/2
            bars.append(f'<text class="tick" x="{cx:.1f}" y="{H-pb+10}" text-anchor="end" transform="rotate(-38 {cx:.1f} {H-pb+10})">{t}</text>')
        grid = ''.join(f'<line class="grid" x1="{pad}" x2="{W-pad}" y1="{H-pb-(H-pad-pb)*k/10:.1f}" y2="{H-pb-(H-pad-pb)*k/10:.1f}"/>' for k in (5, 10))
        panels.append(f'<figure class="panel"><figcaption>{esc(c["label"])}</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(c["label"])}: standing episodes of 10 per terrain">{grid}{"".join(bars)}<text class="tick" x="{pad-4}" y="{H-pb-(H-pad-pb)+4}" text-anchor="end">10</text><text class="tick" x="{pad-4}" y="{H-pb+4}" text-anchor="end">0</text></svg></figure>')
    return '<div class="multiples">' + ''.join(panels) + '</div>'

# ── figure 2: trunk x over time, seed 0, on a chosen terrain, four controllers
SERIES = [('A_open_loop', 'A open loop', 'var(--s1)'), ('B_feedback', 'B gait + balance', 'var(--s2)'), ('C_policy', 'C policy', 'var(--s3)'), ('C_policy_hh', 'C+ policy, heading hold', 'var(--s4)')]
def fig_trace(terrain, seed=0):
    W, H, pl, pr, pb = 640, 240, 44, 150, 30
    xs = lambda t: pl + (W - pl - pr) * t / 6.0
    ymax = 1.2
    ys = lambda v: H - pb - (H - pb - 12) * max(-0.1, min(ymax, v)) / ymax
    out = [f'<line class="axis" x1="{pl}" x2="{W-pr}" y1="{ys(0):.1f}" y2="{ys(0):.1f}"/>']
    for v in (0.25, 0.5, 0.75, 1.0):
        out.append(f'<line class="grid" x1="{pl}" x2="{W-pr}" y1="{ys(v):.1f}" y2="{ys(v):.1f}"/><text class="tick" x="{pl-6}" y="{ys(v)+4:.1f}" text-anchor="end">{v:.2f} m</text>')
    for s in range(0, 7): out.append(f'<text class="tick" x="{xs(s):.1f}" y="{H-8}" text-anchor="middle">{s} s</text>')
    labels = []
    for cid, name, col in SERIES:
        ep = res[(cid, terrain)]['episodes'][seed]
        pts = ' '.join(f'{xs(i/50):.1f},{ys(p[0]):.1f}' for i, p in enumerate(ep['trace']))
        out.append(f'<polyline class="line" style="stroke:{col}" points="{pts}"><title>{esc(name)}, seed {seed}, {terrain}: travelled {ep["travelled"]:.2f} m, {"fell at %.2f s" % ep["fellAt"] if ep["fellAt"] is not None else "standing at 6 s"}</title></polyline>')
        if ep['fellAt'] is not None:
            k = int(ep['fellAt'] * 50); p = ep['trace'][k]
            out.append(f'<circle class="mark" style="fill:{col}" cx="{xs(k/50):.1f}" cy="{ys(p[0]):.1f}" r="4"><title>{esc(name)} fell at {ep["fellAt"]} s</title></circle>')
        tail = 'fell %.1f s' % ep['fellAt'] if ep['fellAt'] is not None else '%.2f m' % ep['travelled']
        labels.append([ys(ep['trace'][-1][0]), f'{name}, {tail}', col])
    # direct labels in the right margin, pushed apart so none overlap
    labels.sort(key=lambda l: l[0])
    for i in range(1, len(labels)):
        if labels[i][0] - labels[i-1][0] < 13: labels[i][0] = labels[i-1][0] + 13
    for y, text, col in labels:
        out.append(f'<text class="label" style="fill:{col}" x="{W-pr+6}" y="{y+4:.1f}">{esc(text)}</text>')
    legend = ''.join(f'<span class="key"><i style="background:{col}"></i>{esc(n)}</span>' for _, n, col in SERIES)
    return f'<div class="legend">{legend}</div><svg viewBox="0 0 {W} {H}" role="img" aria-label="Trunk x position over time on {terrain}, seed {seed}">{"".join(out)}</svg>'

# ── figure 3: terrain profiles
def fig_terrains():
    W, H = 300, 90
    out = []
    for t, v in R['terrains'].items():
        pts = ' '.join(f'{20 + (W-30) * x / 2.0:.1f},{H - 14 - 900 * h:.1f}' for x, h in v['profile'])
        first = f'20,{H-14}'
        out.append(f'<figure class="panel"><figcaption>{t}</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="ground profile {t}"><polygon class="ground" points="{first} {pts} {20+(W-30):.1f},{H-14}"/><text class="tick" x="20" y="{H-2}">0 m</text><text class="tick" x="{20+(W-30)/2:.0f}" y="{H-2}" text-anchor="middle">1 m</text><text class="tick" x="{20+(W-30):.0f}" y="{H-2}" text-anchor="end">2 m</text><text class="tick" x="{W-4}" y="12" text-anchor="end" font-size="8">{esc(v["note"])}</text></svg></figure>')
    return '<div class="multiples">' + ''.join(out) + '</div>'

# ── tables
def table_results():
    h = '<table class="results"><thead><tr><th>Controller</th>' + ''.join(f'<th>{t}</th>' for t in TERR) + '</tr></thead><tbody>'
    for c in CTRL:
        h += f'<tr><th scope="row">{esc(c["label"])}</th>'
        for t in TERR:
            r = res[(c['id'], t)]
            cls = 'good' if r['standing'] == 10 else ('bad' if r['standing'] == 0 else 'mid')
            h += f'<td class="{cls}"><b>{r["standing"]}</b>/10<br><small>{r["travelledMedian"]:.2f} m</small>{"<br><small>off bank " + str(r["leftBank"]) + "</small>" if r["leftBank"] else ""}</td>'
        h += '</tr>'
    return h + '</tbody></table>'

def table_tuning(kind, cols):
    rows_ = R['tuning'][kind]
    h = f'<details><summary>{len(rows_)} grid points, flat floor, seeds 0 to 2 (score = 100 + metres if standing at 6 s, else seconds survived + metres)</summary><div class="scroll"><table><thead><tr>' + ''.join(f'<th>{c}</th>' for c in cols) + '<th>score</th><th>standing</th><th>travelled</th><th>fell at (s)</th></tr></thead><tbody>'
    for r in sorted(rows_, key=lambda r: -r['score']):
        h += '<tr>' + ''.join(f'<td>{r["params"][c]}</td>' for c in cols) + f'<td>{r["score"]:.3f}</td><td>{r["standing"]}/3</td><td>{r["travelled"]:.3f}</td><td>{", ".join(str(v) for v in r["fellAt"])}</td></tr>'
    return h + '</tbody></table></div></details>'

def table_commands(n=25):
    h = '<div class="scroll"><table class="cmd"><thead><tr>' + ''.join(f'<th>{esc(c)}</th>' for c in rows[0]) + '</tr></thead><tbody>'
    for r in rows[1:1+n]: h += '<tr>' + ''.join(f'<td>{v}</td>' for v in r) + '</tr>'
    return h + f'</tbody></table></div><p class="muted">First {n} of {len(rows)-1} rows. Every row is one 20 ms control tick: fourteen servo position targets in radians, the whole 6 s table in <a href="data/commands_open_loop.csv">commands_open_loop.csv</a>.</p>'

def table_neutral():
    h = '<div class="scroll"><table><thead><tr><th>joint</th><th>HOME (rad)</th><th>measured standing target (rad)</th><th>delta</th></tr></thead><tbody>'
    for j, hm, n in zip(NEU['joints'], NEU['home'], NEU['neutral']): h += f'<tr><td>{j}</td><td>{hm:.4f}</td><td>{n:.4f}</td><td>{n-hm:+.4f}</td></tr>'
    return h + '</tbody></table></div>'

bestA = R['best']['open_loop']['params']; bestB = R['best']['feedback']['params']
def n_of(cid, t): return res[(cid, t)]['standing']
summary = {c['id']: sum(n_of(c['id'], t) for t in TERR) for c in CTRL}

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>An LLM at 50 Hz</title>
<meta name="description" content="A checkable answer to the challenge: can an LLM output the high frequency control commands for a legged robot in varying terrain? Three controllers, eight terrains, one MuJoCo plant, every number reproducible.">
<style>
:root{{color-scheme:light dark;--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--ink3:#7a7975;--rule:#e4e2dc;--card:#f4f3ef;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--good:#dff3e6;--bad:#fbe3e2;--mid:#fff3d6}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--ink3:#8f8e87;--rule:#34332f;--card:#242422;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--good:#173d26;--bad:#4a1f1e;--mid:#4a3a12}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,"Iowan Old Style","Times New Roman",serif}}
main{{max-width:880px;margin:0 auto;padding:32px 20px 80px}}
h1{{font-size:2.4rem;line-height:1.1;margin:.2em 0 .3em;letter-spacing:-.01em}}h2{{font-size:1.5rem;margin:2.2em 0 .5em;border-top:1px solid var(--rule);padding-top:1em}}h3{{font-size:1.1rem;margin:1.6em 0 .4em}}
p,li{{max-width:70ch}}a{{color:var(--s1)}}.muted{{color:var(--ink2);font-size:.92rem}}small{{color:var(--ink2)}}
blockquote{{margin:1.2em 0;padding:.6em 1em;border-left:3px solid var(--s1);background:var(--card);font-style:italic}}
.hero{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:1.4em 0}}
.tile{{background:var(--card);border-radius:8px;padding:12px 14px}}.tile b{{display:block;font-size:2rem;line-height:1.1;font-family:ui-monospace,Menlo,Consolas,monospace}}.tile span{{color:var(--ink2);font-size:.9rem}}
.multiples{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin:1em 0}}
.panel{{margin:0;background:var(--card);border-radius:8px;padding:8px 8px 4px}}.panel figcaption{{font-size:.85rem;color:var(--ink2);padding:2px 4px 6px;font-family:system-ui,sans-serif}}
svg{{width:100%;height:auto;display:block;font-family:system-ui,sans-serif}}
.bar{{fill:var(--s1)}}.val{{font-size:11px;fill:var(--ink)}}.tick{{font-size:10px;fill:var(--ink3)}}.grid{{stroke:var(--rule);stroke-width:1}}.axis{{stroke:var(--ink3);stroke-width:1}}
.line{{fill:none;stroke-width:2;stroke-linejoin:round}}.label{{font-size:11px;font-weight:600}}.mark{{stroke:var(--bg);stroke-width:2}}.ground{{fill:var(--s1);opacity:.45}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font:.85rem system-ui,sans-serif;color:var(--ink2);margin:.6em 0}}.key i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
table{{border-collapse:collapse;font:.85rem system-ui,sans-serif;width:100%}}th,td{{padding:6px 8px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}}th[scope=row]{{font-weight:500;max-width:220px}}
.results td{{text-align:center}}.results td.good{{background:var(--good)}}.results td.bad{{background:var(--bad)}}.results td.mid{{background:var(--mid)}}
.scroll{{overflow-x:auto;margin:.6em 0}}.cmd td,.cmd th{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.72rem;white-space:nowrap;padding:3px 6px}}
code,pre{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.85em}}pre{{background:var(--card);padding:12px 14px;border-radius:8px;overflow-x:auto}}
details{{margin:.6em 0}}summary{{cursor:pointer;color:var(--ink2)}}
.byline{{color:var(--ink2);font-size:.95rem}}
</style>
</head>
<body>
<main>
<p class="byline">Craig Merry, pairing with Claude Code · {DATE} · <a href="https://github.com/craigm26/llm-legged-control">source, data and sim</a></p>
<h1>An LLM at 50 Hz</h1>
<p class="muted">A checkable answer to a challenge posed on X on 7 September 2026.</p>
<blockquote>Can you prompt an LLM to output the high frequency control commands for a legged robot in varying terrain e.g. ashish-kmr.github.io RSS 2021, CoRL 2022 (this is by now 5 year old technology, so I am not picking a particularly hard task).<br><small>@JitendraMalikCV, 7 Sep 2026</small></blockquote>

<p><strong>Short answer: no, and here is the receipt.</strong> I asked Claude to write the 50 Hz joint commands for the smallest legged robot on my desk, a Pollen Microduck, and ran them in the same MuJoCo plant that scores the robot's own trained policy. The LLM's open-loop command table never stood for six seconds on a flat floor, let alone on terrain. Its hand-written balance law can hold a stand but not a walk. The five-year-old recipe, a PPO policy at 50 Hz reading 61 proprioceptive numbers, walks on everything up to its training limit. What the LLM was good for was everything around the loop: the terrains, the instruments, the sign conventions, and finding that the servos cannot even hold the nominal pose without feedback.</p>

<div class="hero">
<div class="tile"><b>{summary['A_open_loop']}/{10*len(TERR)}</b><span>LLM open-loop table: episodes still standing at 6 s, all terrains</span></div>
<div class="tile"><b>{summary['B_feedback']}/{10*len(TERR)}</b><span>LLM gait plus LLM balance law</span></div>
<div class="tile"><b>{summary['C_policy']}/{10*len(TERR)}</b><span>trained PPO policy, 0.3 m/s: all of flat, 5 mm rough and most of a 10 mm ledge</span></div>
<div class="tile"><b>{n_of('C_policy','ledge10')} then {n_of('C_policy','ledge15')}</b><span>policy on a 10 mm ledge, then on a 15 mm ledge, of 10</span></div>
</div>

<h2>What was tested</h2>
<p><strong>The robot.</strong> Pollen Robotics' Microduck: a 25 cm, roughly 800 g biped with fourteen position-servo joints the policy drives (five per leg, four in the neck and head) plus a mouth. Its runtime runs the policy at 50 Hz over a 61-value proprioceptive observation. This is not a quadruped and not the A1 or the Cassie in the cited papers. It is the legged robot I have a verified simulator for, and it is harder for open loop, not easier: the servos are weak (kp 0.55 N·m/rad, torque limit ±0.64 N·m) and the standing pose is not statically stable on them.</p>
<p><strong>The plant.</strong> duckbench's <code>scene.mjb</code> (sha256 {sha(f'{DB}/sim/scene.mjb')}…), MuJoCo {json.load(open(f'{DB}/sim/node_modules/mujoco/package.json'))['version']} WASM, 5 ms timestep, four substeps per 20 ms control tick. The same plant and the same control loop that every published duckbench number went through, at duckbench commit <code>{duckbench_sha[:7]}</code>.</p>
<p><strong>The terrains.</strong> Eight, laid from the bench's bank of movable blocks along a 340 mm wide lane. Each block is 200 mm tall with its top at the tread, so a ledge is a real vertical face, not a slope. Pollen trains this robot on steps capped at 15 mm because, in their words in the training config, "the robot can only lift its feet ~1-2 cm". The terrains bracket that.</p>
{fig_terrains()}

<h3>Three controllers</h3>
<ol>
<li><strong>A. The LLM's open-loop 50 Hz table.</strong> Claude wrote a parametric gait by hand (a hip pitch sinusoid, a knee lift during swing, an ankle that keeps the sole flat, a hip roll weight shift, a 1 s amplitude ramp), expanded it into a literal table of fourteen servo targets every 20 ms, and the table is played with no sensor read after t = 0. This is the challenge as posed. Its five parameters were tuned on the flat floor only with a 72-point grid, three seeds each, then frozen. The best: f = {bestA['f']} Hz, hip {bestA['A']} rad, knee {bestA['K']} rad, roll {bestA['Rl']} rad.</li>
<li><strong>B. The same gait plus an LLM-written balance law.</strong> Projected gravity and the gyro feed hip pitch and hip roll offsets every tick. Gains tuned on the flat floor with a 27-point grid: kp = {bestB['kp']}, kr = {bestB['kr']}, kd = {bestB['kd']}. This is the "code as policy" reading of the challenge.</li>
<li><strong>C. Pollen's trained policy.</strong> <code>alpha_walking.onnx</code> (sha256 {sha(f'{DB}/sim/alpha_walking.onnx')}…), PPO in mjlab, run through the bench's canonical observation and actuation path with a 0.3 m/s forward command. Not tuned. <strong>C+</strong> adds a heading hold on the command input (a yaw rate proportional to lateral drift and heading) so the blind policy stays on the 340 mm lane; that is a planner-level input, the kind of thing the post says LLMs are fine at.</li>
</ol>
<p>Two controls make the failures legible. <strong>A0</strong> plays the measured standing servo targets with zero gait amplitude. <strong>B0</strong> is the balance law alone, no gait. And C is also run at 0.2 m/s, which turns out to be inside the policy's command dead zone.</p>

<h3>Protocol</h3>
<p>Every episode: reset with a perturbed start (±2 mm trunk, ±0.02 rad per joint; seed 0 is nominal), 25 ticks of settle under the standing policy, then 300 ticks (6 s) of the controller under test. An episode <em>fell</em> when projected gravity z rose above −0.7 or the trunk dropped below 60 mm, and is <em>standing</em> if at the last tick gravity z is below −0.9 and the trunk is above 90 mm. Ten seeds per cell. The step blocks do not collide with each other (the bench's standard isolation); block-to-robot contact is untouched.</p>

<h2>Results</h2>
<p>Episodes still standing at six seconds, of ten, per terrain.</p>
{fig_standing()}
<p class="muted">Below each bar count in the table: the median distance travelled along the lane, and how many runs walked off the side of the 340 mm lane before the end.</p>
{table_results()}

<h3>Trunk position on the 10 mm rough terrain, seed 0</h3>
<p>Forward position of the trunk over the six seconds. A dot marks the tick the fall criterion fired.</p>
{fig_trace('rough10')}
<h3>The same on the flat floor</h3>
{fig_trace('flat')}

<h3>What the numbers say</h3>
<ul>
<li><strong>Open loop cannot even stand here.</strong> Holding the robot's nominal HOME pose on its position servos falls at 0.64 s on a flat floor (see <code>diag.mjs</code> in the log). The servos sag under the trunk and nothing corrects it. The LLM's fix was to measure what the trained standing policy actually asks the servos for at steady state (its hip roll targets sit 0.18 rad away from HOME, see the table below) and use that as the gait's neutral pose. That holds a stand, A0: {n_of('A_hold','flat')}/10 on flat.</li>
<li><strong>The LLM's gait never walks.</strong> Best of 72 grid points on the flat floor still fell at about {R['best']['open_loop']['score']:.1f} s. On terrain, A stood in {summary['A_open_loop']} of {10*len(TERR)} episodes. Every open-loop table an LLM writes has this shape: its feet leave the ground on a clock, and the plant does not read the clock.</li>
<li><strong>An LLM can write a balance law that stands.</strong> B0 holds a stand {n_of('B_hold','flat')}/10 on flat with a negative pitch gain (the sign had to be found by trying both). Adding the gait to it gives B: {summary['B_feedback']} of {10*len(TERR)}. A PD on gravity is a stabiliser, not a gait.</li>
<li><strong>The trained policy walks, up to its training limit.</strong> C+ stands {n_of('C_policy_hh','flat')}/10 on flat, {n_of('C_policy_hh','rough5')}/10 on 5 mm rough, {n_of('C_policy_hh','ledge10')}/10 on a 10 mm ledge, then {n_of('C_policy_hh','ledge15')}/10 at 15 mm and {n_of('C_policy_hh','ledge20')}/10 at 20 mm. Pollen capped its training terrain at 15 mm; a blind proprioceptive policy trips on the first ledge past what it has felt. That is precisely the gap the cited CoRL 2022 paper closes with egocentric vision.</li>
<li><strong>Where the policy falls.</strong> Every fall on the 15 and 20 mm ledges happens at x = 0.13 to 0.21 m with the trunk within 0.11 m of the lane's centre line: the first riser, mid-lane, not a walk off the side. On the 10 mm rough terrain all ten runs fall at x = 0.39 m, the first 10 to 20 mm rise. On the 5 mm ramp all ten runs clear the first two 5 mm rises and fall at the third, around x = 0.58 m. The heading hold did not help: C+ is worse than C on the 10 mm ledge ({n_of('C_policy_hh','ledge10')} vs {n_of('C_policy','ledge10')} of 10), so the yaw command it adds while the robot is stepping up costs more than the drift it removes.</li>
<li><strong>A dead zone worth knowing before quoting a number.</strong> A 0.2 m/s command produces no walking at all (median {res[('C_policy_vx0.2','flat')]['travelledMedian']:.3f} m on flat, and a perfect 10 of 10 standing on every terrain because it never reaches one). Any comparison at that command measures standing, not locomotion.</li>
</ul>

<h2>What the LLM produced</h2>
<p>This is the literal deliverable the challenge asks for: joint targets at 50 Hz, written by the model. It is also what fails.</p>
{table_commands()}
<h3>The measured neutral pose the table rides on</h3>
<p>Mean servo targets over ticks 100 to 299 of the trained standing policy on the flat floor, three seeds. The LLM's gait is written as offsets from this column, because offsets from HOME fall over in under a second.</p>
{table_neutral()}
<h3>Tuning grids, in full</h3>
<p>Open loop (A):</p>
{table_tuning('open_loop', ['f','A','K','Rl'])}
<p>Balance law (B), on top of the best A gait:</p>
{table_tuning('feedback', ['kp','kr','kd'])}

<h2>Limitations, stated plainly</h2>
<ul>
<li><strong>Simulation only.</strong> No servo was harmed. Sim-to-real would only widen every gap shown here.</li>
<li><strong>A toy biped, not the robots in the cited papers.</strong> The challenge names quadruped and biped work at 100 Hz on A1 and Cassie. I have neither. The Microduck is a 25 cm toy whose servos cannot hold its own pose open loop, which makes the open-loop half of this test harsher than it would be on a stiff, well-damped quadruped. It does not change the shape of the answer, but it does change how far a hand-written table might get on a better-behaved robot.</li>
<li><strong>The LLM got a simulator in the loop.</strong> The 72- and 27-point grids are the model iterating against physics, which is more than "prompt an LLM" and still not enough. A fair reading is: prompting plus a hundred rollouts of tuning does not produce a walking controller.</li>
<li><strong>The trained baseline is Pollen's, not mine.</strong> It is the closest thing on hand to the cited recipe (PPO, proprioception only, 50 Hz, MuJoCo), not an RMA reimplementation; there is no adaptation module and no terrain curriculum beyond Pollen's 15 mm.</li>
<li><strong>One controller family per reading of the challenge.</strong> A cleverer open-loop gait exists somewhere. The claim is not that none exists; it is that an LLM prompted to write one, with a simulator to check against, did not find it, and that the trained policy did not need to look.</li>
<li><strong>Bench specifics.</strong> Step blocks are isolated from each other, the lane is 340 mm wide, and the terrain is a stack of overlapping 340 mm deep blocks; the profiles above are exactly what was laid. The fall criterion is a threshold on projected gravity, not a contact sensor.</li>
</ul>

<h2>What the LLM was actually useful for</h2>
<p>Everything in the post's last sentence. Over the same afternoon the model wrote the terrain generator, the kinematic sign probe (which joint direction lifts which foot), the episode harness, the perturbation protocol, the two controls, and the analysis on this page. It found the HOME-pose instability and the 0.2 m/s dead zone, both of which would have quietly corrupted a naive comparison. Earlier this month, in the same bench, it spent about 50,000 episodes searching for stair-climbing motions for this robot and its most valuable output was finding that the staircase itself was broken. Planning, instrumentation, and review: yes. The 50 Hz loop: no.</p>

<h2>Reproduce it</h2>
<pre>git clone https://github.com/craigm26/duckbench && cd duckbench/sim && npm install
cp -r ../../llm-legged-control/sim malik     # or use sim/malik in duckbench at {duckbench_sha[:7]}
node malik/probe.mjs      # joint sign conventions
node malik/diag.mjs       # the HOME-pose control and the policy's command sweep
node malik/diag2.mjs      # measures neutral.json, ledge limit
node malik/run.mjs        # tuning grids, evaluation, results.json, commands_open_loop.csv</pre>
<p>Node {R['node']}, onnxruntime-node {json.load(open(f'{DB}/sim/node_modules/onnxruntime-node/package.json'))['version']}, mujoco {json.load(open(f'{DB}/sim/node_modules/mujoco/package.json'))['version']}. Every episode is deterministic given its seed; the reported numbers are what <code>run.log</code> shows.</p>

<h2>Data</h2>
<ul>
<li><a href="data/results.json">results.json</a>: protocol, terrains, tuning grids, and every episode with its per-tick trunk trace (x, y, z, gravity z).</li>
<li><a href="data/commands_open_loop.csv">commands_open_loop.csv</a>: the LLM's 50 Hz command table, 300 rows.</li>
<li><a href="data/neutral.json">neutral.json</a>: the measured standing targets.</li>
<li><a href="data/run.log">run.log</a>: the run as it printed.</li>
<li><a href="sim/">sim/</a>: lib.mjs (plant, controllers, episode), run.mjs, probe.mjs, diag.mjs, diag2.mjs.</li>
<li>Plant and policies: <a href="https://github.com/craigm26/duckbench">craigm26/duckbench</a> at <code>{duckbench_sha[:7]}</code>, files <code>sim/scene.mjb</code>, <code>sim/alpha_walking.onnx</code>, <code>sim/BEST_alpha_stand.onnx</code> (sha256 {sha(f'{DB}/sim/BEST_alpha_stand.onnx')}…).</li>
</ul>

<h2>References</h2>
<ol>
<li>Ashish Kumar, Zipeng Fu, Deepak Pathak, Jitendra Malik. <em>RMA: Rapid Motor Adaptation for Legged Robots.</em> RSS 2021. <a href="https://ashish-kmr.github.io/rma-legged-robots/">project page</a>, <a href="https://arxiv.org/abs/2107.04034">arXiv:2107.04034</a>.</li>
<li>Ananye Agarwal, Ashish Kumar, Jitendra Malik, Deepak Pathak. <em>Legged Locomotion in Challenging Terrains using Egocentric Vision.</em> CoRL 2022, best systems paper. <a href="https://vision-locomotion.github.io/">project page</a>, <a href="https://arxiv.org/abs/2211.07638">arXiv:2211.07638</a>.</li>
<li>Ashish Kumar, Zhongyu Li, Jun Zeng, Deepak Pathak, Koushil Sreenath, Jitendra Malik. <em>Adapting Rapid Motor Adaptation for Bipedal Robots.</em> IROS 2022. <a href="https://ashish-kmr.github.io/a-rma/">project page</a>, <a href="https://arxiv.org/abs/2205.15299">arXiv:2205.15299</a>.</li>
<li>Pollen Robotics. <em>microduck_rl</em>: RL training environments for Microduck (mjlab, PPO, Apache-2.0). <a href="https://github.com/pollen-robotics/microduck_rl">github.com/pollen-robotics/microduck_rl</a>; the 15 mm step cap and the "~1-2 cm" foot lift are in <code>src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py</code>. Runtime: <a href="https://github.com/pollen-robotics/microduck">github.com/pollen-robotics/microduck</a>.</li>
<li>Emanuel Todorov, Tom Erez, Yuval Tassa. <em>MuJoCo: A physics engine for model-based control.</em> IROS 2012. <a href="https://mujoco.org">mujoco.org</a>.</li>
<li>Craig Merry. <em>duckbench</em>: the Microduck bench this ran in. <a href="https://github.com/craigm26/duckbench">github.com/craigm26/duckbench</a>.</li>
<li>The post this answers: @JitendraMalikCV on X, 7 September 2026, 9:03 PM.</li>
</ol>
</main>
</body>
</html>
'''
open(f'{OUT}/index.html', 'w').write(page)
print('wrote index.html', len(page), 'bytes')
