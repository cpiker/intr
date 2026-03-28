#!/usr/bin/env python3
#
# done.py -- Completed task archive, grouped by calendar week
#
# CGI script for Apache. Read-only, no authentication required.

# AI Disclosure:
#    This code was generated in cooperation with Claude, which is an Artificial 
#    Intelligence service provided by Anthropic. Though design and development was
#    orchestrated by a human, reviewed by a human and tested by a human, most of 
#    the actual code was composed by an AI.
#   
#    It is completely reasonable to forbid AI generated software in some contexts.
#    Please check the contribution guidelines of any projects you participate in.
#    If the project has a rule against AI generated software then DO NOT INCLUDE
#    THIS FILE, in whole or in part, in your patches or pull requests.

import json
import os
import html
from datetime import datetime, timezone, timedelta


# ########################################################################### #
# configuration #

# current state of insanity
TASKS_FILE = os.environ.get('INTR_TASKS_FILE', '/var/www/taskdata/tasks.json')

# Memorial for adventures of yore
DONE_DIR   = os.environ.get('INTR_DONE_DIR',   '/var/www/taskdata')

# Extern names of scripts. Needed for cross links
#
#   ScriptAlias /some/url/path/tasks            "/var/www/cgi-bin/tasks.py"
#   ScriptAlias /some/url/path/intr-auth/tasks  "/var/www/cgi-bin/tasks.py"
#
#   ScriptAlias /some/url/path/done            "/var/www/cgi-bin/done.py"
#   ScriptAlias /some/url/path/intr-auth/done  "/var/www/cgi-bin/done.py"
#
#  So in the case above TASK_PATH_TOK would be "tasks" and the done token
#  would be "done".  I prefer to use 'intr' and 'handled', so that's what's
#  in the readme.

TASKS_SCRIPT_NAME = 'intr'
DONE_SCRIPT_NAME = 'handled'

# ########################################################################### #
# Label color palette                                                          #
#                                                                              #
# Keep this in sync with the copy in tasks.py.                                #
# Each entry: 'name': ('#background', '#foreground')                          #

LABEL_COLORS = {
	'amber':    ('#fdf3dc', '#7a5c10'),
	'rose':     ('#fde8e8', '#8b2020'),
	'sage':     ('#e6f2e6', '#2a5c2a'),
	'sky':      ('#dff0fb', '#1a527a'),
	'lavender': ('#ede8f8', '#4a2d8a'),
	'mint':     ('#dff5ef', '#185c40'),
	'steel':    ('#e4eaf2', '#2a3d5c'),
	'lilac':    ('#f5e8f5', '#6a1a6a'),
	'sand':     ('#f2eedf', '#4a3d10'),
	'peach':    ('#fdeede', '#7a3a10'),
}

LABEL_COLOR_DEFAULT = 'amber'

# ########################################################################### #
# helpers #

def h(s):
	return html.escape(str(s) if s else '', quote=True)

def label_badge(label, color=None):
	"""Render a colored label badge span, or empty string if no label."""
	if not label:
		return ''
	bg, fg = LABEL_COLORS.get(color or LABEL_COLOR_DEFAULT, LABEL_COLORS[LABEL_COLOR_DEFAULT])
	return (
		f'<span class="label-badge" '
		f'style="background:{bg};color:{fg};">{h(label)}</span>'
	)

def load_done(year):
	path = os.path.join(DONE_DIR, f'done_{year}.json')
	if not os.path.exists(path):
		return []
	with open(path, 'r') as f:
		return json.load(f)

def available_years():
	years = []
	if not os.path.exists(DONE_DIR):
		return years
	for fname in os.listdir(DONE_DIR):
		if fname.startswith('done_') and fname.endswith('.json'):
			try:
				years.append(int(fname[5:9]))
			except ValueError:
				pass
	return sorted(years, reverse=True)

def week_label(dt):
	# "Week 12  Mar 17 - Mar 23" style label
	monday = dt - timedelta(days=dt.weekday())
	sunday = monday + timedelta(days=6)
	wnum   = dt.isocalendar()[1]
	return f"Week {wnum} &mdash; {monday.strftime('%b %d')} &ndash; {sunday.strftime('%b %d')}"

def week_key(dt):
	# ISO year+week as sortable integer, descending
	iso = dt.isocalendar()
	return iso[0] * 100 + iso[1]

def duration_str(created_iso, completed_iso):
	try:
		c1 = datetime.fromisoformat(created_iso)
		c2 = datetime.fromisoformat(completed_iso)
		if c1.tzinfo is None: c1 = c1.replace(tzinfo=timezone.utc)
		if c2.tzinfo is None: c2 = c2.replace(tzinfo=timezone.utc)
		delta = c2 - c1
		days = delta.days
		if days == 0:
			hours = delta.seconds // 3600
			return f"{hours}h" if hours else "<1h"
		elif days < 14:
			return f"{days}d"
		elif days < 60:
			return f"{days // 7}w"
		else:
			return f"{days // 30}mo"
	except Exception:
		return "?"

def seconds_to_str(secs):
	# Human-readable duration from a raw second count.
	if secs < 60:
		return "<1m"
	elif secs < 3600:
		return f"{secs // 60}m"
	days = secs // 86400
	if days == 0:
		return f"{secs // 3600}h"
	elif days < 14:
		return f"{days}d"
	elif days < 60:
		return f"{days // 7}w"
	else:
		return f"{days // 30}mo"

# ########################################################################### #

BANNER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 800 140">
  <defs>
    <marker id="sa" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#C9A84C"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>

  <g transform="translate(80,0)">

  <!-- ── SIGNAL LINE — all dim, no highlight ── -->
  <line x1="0"   y1="105" x2="500" y2="105"
        stroke="#C9A84C" stroke-width="1.3" opacity="0.4"/>
  <line x1="0" y1="105" x2="25" y2="105"
        stroke="#C9A84C" stroke-width="1" opacity="0.15"
        stroke-dasharray="3 5"/>
  <line x1="500" y1="105" x2="500" y2="78"
        stroke="#C9A84C" stroke-width="1.3" opacity="0.4" stroke-linecap="round"/>
  <line x1="500" y1="78" x2="548" y2="78"
        stroke="#C9A84C" stroke-width="1.3" opacity="0.4" stroke-linecap="round"/>

  <!-- ── CHIP ── -->
  <g transform="translate(598,60) skewY(-9) translate(-598,-60)">
    <rect x="574" y="12" width="48" height="96" rx="3"
          fill="#111" stroke="#383838" stroke-width="1"/>
    <path d="M590 12 Q598 9 606 12" fill="none" stroke="#444" stroke-width="1"/>
    <circle cx="579" cy="18" r="1.2" fill="#555"/>
    <g stroke="#4a4a4a" stroke-width="1" stroke-linecap="round" fill="none">
      <polyline points="574,16.0  564,16.0  562,20"/>
      <polyline points="574,20.5  564,20.5  562,24.5"/>
      <polyline points="574,25.0  564,25.0  562,29"/>
      <polyline points="574,29.5  564,29.5  562,33.5"/>
      <polyline points="574,34.0  564,34.0  562,38"/>
      <polyline points="574,38.5  564,38.5  562,42.5"/>
      <polyline points="574,43.0  564,43.0  562,47"/>
      <polyline points="574,47.5  564,47.5  562,51.5"/>
      <polyline points="574,52.0  564,52.0  562,56"/>
      <polyline points="574,56.5  564,56.5  562,60.5"/>
      <polyline points="574,61.0  564,61.0  562,65"/>
      <polyline points="574,65.5  564,65.5  562,69.5"/>
      <polyline points="574,70.0  564,70.0  562,74"/>
      <polyline points="574,74.5  564,74.5  562,78.5"/>
      <polyline points="574,79.0  564,79.0  562,83"/>
      <polyline points="574,83.5  564,83.5  562,87.5"/>
      <polyline points="574,88.0  564,88.0  562,92"/>
      <polyline points="574,97.0  564,97.0  562,101"/>
      <polyline points="574,101.5 564,101.5 562,105.5"/>
    </g>
    <!-- pin 18: dim -->
    <polyline points="574,92.5 548,92.5 548,78"
              fill="none" stroke="#C9A84C" stroke-width="1.3"
              opacity="0.4" stroke-linecap="round" stroke-linejoin="round"/>
    <g stroke="#4a4a4a" stroke-width="1" stroke-linecap="round" fill="none">
      <polyline points="622,16.0  632,16.0  634,20"/>
      <polyline points="622,20.5  632,20.5  634,24.5"/>
      <polyline points="622,25.0  632,25.0  634,29"/>
      <polyline points="622,29.5  632,29.5  634,33.5"/>
      <polyline points="622,34.0  632,34.0  634,38"/>
      <polyline points="622,38.5  632,38.5  634,42.5"/>
      <polyline points="622,43.0  632,43.0  634,47"/>
      <polyline points="622,47.5  632,47.5  634,51.5"/>
      <polyline points="622,52.0  632,52.0  634,56"/>
      <polyline points="622,56.5  632,56.5  634,60.5"/>
      <polyline points="622,61.0  632,61.0  634,65"/>
      <polyline points="622,65.5  632,65.5  634,69.5"/>
      <polyline points="622,70.0  632,70.0  634,74"/>
      <polyline points="622,74.5  632,74.5  634,78.5"/>
      <polyline points="622,79.0  632,79.0  634,83"/>
      <polyline points="622,83.5  632,83.5  634,87.5"/>
      <polyline points="622,88.0  632,88.0  634,92"/>
      <polyline points="622,92.5  632,92.5  634,96.5"/>
      <polyline points="622,97.0  632,97.0  634,101"/>
      <polyline points="622,101.5 632,101.5 634,105.5"/>
    </g>
  </g>

  <!-- ── STICK FIGURES — walking left, gentle leftward lean ── -->

  <!-- Figure 0 x=30 -->
  <g stroke="#111" stroke-width="1.5" stroke-linecap="round" fill="none">
    <circle cx="30" cy="88" r="4.5" fill="#111" stroke="none"/>
    <line x1="29" y1="92.5" x2="32" y2="102"/>
    <line x1="30" y1="96"   x2="24" y2="99"/>
    <line x1="30" y1="96"   x2="35" y2="93"/>
    <line x1="32" y1="102"  x2="26" y2="111"/>
    <line x1="32" y1="102"  x2="36" y2="111"/>
  </g>

  <!-- Figure 1 x=75 -->
  <g stroke="#111" stroke-width="1.5" stroke-linecap="round" fill="none">
    <circle cx="75" cy="88" r="4.5" fill="#111" stroke="none"/>
    <line x1="74" y1="92.5" x2="77" y2="102"/>
    <line x1="75" y1="96"   x2="69" y2="93"/>
    <line x1="75" y1="96"   x2="80" y2="99"/>
    <line x1="77" y1="102"  x2="71" y2="111"/>
    <line x1="77" y1="102"  x2="81" y2="111"/>
  </g>

  <!-- Figure 2 x=120 -->
  <g stroke="#111" stroke-width="1.5" stroke-linecap="round" fill="none">
    <circle cx="120" cy="88" r="4.5" fill="#111" stroke="none"/>
    <line x1="119" y1="92.5" x2="122" y2="102"/>
    <line x1="120" y1="96"   x2="114" y2="99"/>
    <line x1="120" y1="96"   x2="125" y2="93"/>
    <line x1="122" y1="102"  x2="116" y2="111"/>
    <line x1="122" y1="102"  x2="126" y2="111"/>
  </g>

  <!-- Figure 3 x=170 -->
  <g stroke="#111" stroke-width="1.5" stroke-linecap="round" fill="none">
    <circle cx="170" cy="88" r="4.5" fill="#111" stroke="none"/>
    <line x1="169" y1="92.5" x2="172" y2="102"/>
    <line x1="170" y1="96"   x2="164" y2="93"/>
    <line x1="170" y1="96"   x2="175" y2="99"/>
    <line x1="172" y1="102"  x2="166" y2="111"/>
    <line x1="172" y1="102"  x2="176" y2="111"/>
  </g>

  <!-- Figure 4 x=225: tossing, leans right into throw -->
  <g stroke="#111" stroke-width="1.5" stroke-linecap="round" fill="none">
    <circle cx="225" cy="88" r="4.5" fill="#111" stroke="none"/>
    <line x1="226" y1="92.5" x2="223" y2="102"/>
    <line x1="225" y1="96"   x2="219" y2="93"/>
    <line x1="225" y1="96"   x2="233" y2="89"/>
    <line x1="223" y1="102"  x2="217" y2="111"/>
    <line x1="223" y1="102"  x2="228" y2="111"/>
  </g>
  <!-- paper wad + arc -->
  <circle cx="241" cy="82" r="2" fill="#111"/>
  <path d="M234 89 Q238 79 241 82"
        fill="none" stroke="#111" stroke-width="0.8"
        stroke-dasharray="2 2" opacity="0.5"/>

  <!-- ── LABELS ── -->
  <text x="14" y="30"
        font-family="monospace,'Courier New',Courier"
        font-size="26" font-weight="bold" fill="#C9A84C"
        opacity="0.9">INTR</text>
  <text x="14" y="50"
        font-family="monospace,'Courier New',Courier"
        font-size="8.5" fill="#777"
        letter-spacing="8">interrupt request pending</text>

</svg>'''

CSS = """
body {
	font-family: monospace;
	font-size: 14px;
	margin: 0;
	padding: 0;
	background: #f4f4f4;
	color: #111;
}
#page {
	max-width: min(1400px, 95vw);
	margin: 0 auto;
	padding: 12px 16px;
}
h1 { font-size: 16px; margin: 0 0 12px; font-weight: bold; }
h2 { font-size: 13px; margin: 16px 0 4px; color: #444; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
a { color: #00e; }
a:visited { color: #551a8b; }
/* Banner */
#banner {
	width: 100%;
	display: block;
	margin-bottom: 8px;
	border-bottom: 1px solid #ccc;
}

#nav a { margin-right: 12px; }
table {
	width: 100%;
	border-collapse: collapse;
	margin-bottom: 6px;
}
th {
	text-align: left;
	font-size: 12px;
	border-bottom: 1px solid #aaa;
	padding: 3px 6px;
	background: #e8e8e8;
}
td {
	padding: 4px 6px;
	border-bottom: 1px solid #eee;
	vertical-align: top;
	font-size: 13px;
}
tr:hover td { background: #f0f0f0; }
.taskname { font-weight: bold; }
.date-col { white-space: nowrap; color: #555; width: 8em; }
.age-col  { white-space: nowrap; color: #777; width: 5em; }
.week-count { font-size: 11px; color: #888; float: right; font-weight: normal; }
#year-select { font-size: 13px; margin-bottom: 12px; }

/* Label badge — colors applied via inline style; only structure here */
.label-badge {
	display: inline-block;
	font-size: 10px;
	padding: 1px 5px;
	border-radius: 2px;
	margin-left: 4px;
	vertical-align: middle;
	white-space: nowrap;
}

/* Abandoned task indicator */
.abandoned-badge {
	display: inline-block;
	font-size: 10px;
	padding: 1px 5px;
	background: #eee;
	color: #888;
	border-radius: 2px;
	margin-left: 4px;
	vertical-align: middle;
}
tr.abandoned td { color: #aaa; }
tr.abandoned .taskname { font-weight: normal; }
"""

# ########################################################################### #

def main():

	#print("\r\n\r")

	qs = os.environ.get('QUERY_STRING', '')
	params = {}
	for part in qs.split('&'):
		if '=' in part:
			k, v = part.split('=', 1)
			params[k] = v

	current_year = datetime.now().year
	years = available_years()
	if not years:
		years = [current_year]

	try:
		selected_year = int(params.get('year', current_year))
	except ValueError:
		selected_year = current_year

	entries = load_done(selected_year)

	# Group by ISO week, descending.
	weeks = {}
	for entry in entries:
		try:
			dt = datetime.fromisoformat(entry['completed_at'])
			if dt.tzinfo is None:
				dt = dt.replace(tzinfo=timezone.utc)
		except Exception:
			continue
		key = week_key(dt)
		if key not in weeks:
			weeks[key] = {'label': week_label(dt), 'tasks': []}
		weeks[key]['tasks'].append((dt, entry))

	# Sort weeks newest first, tasks within week newest first.
	sorted_weeks = sorted(weeks.items(), key=lambda x: x[0], reverse=True)

	done_script  = os.environ.get('SCRIPT_NAME')
	tasks_script = done_script.replace(DONE_SCRIPT_NAME, TASKS_SCRIPT_NAME, 1)

	print("Content-Type: text/html; charset=utf-8\r\n\r")
	print(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>INTR &mdash; done {selected_year}</title>
<style>{CSS}</style>
</head>
<body>
<div id="page">
<div id="banner">{BANNER_SVG}</div>
<div id="nav">
  <a href="{h(tasks_script)}">Tasks</a>
  <a href="{h(done_script)}">Done</a>
</div>
<h1>Completed tasks &mdash; {selected_year}</h1>
""")

	# Year selector
	if len(years) > 1:
		print('<div id="year-select">Year: ')
		for y in years:
			if y == selected_year:
				print(f'<b>{y}</b> ')
			else:
				print(f'<a href="{h(done_script)}?year={y}">{y}</a> ')
		print('</div>')

	if not sorted_weeks:
		print('<p style="color:#888;">No completed tasks for this year.</p>')
	else:
		total = sum(len(w['tasks']) for _, w in sorted_weeks)
		print(f'<p style="font-size:12px;color:#666;">{total} tasks completed</p>')
		for key, week in sorted_weeks:
			count = len(week['tasks'])
			print(f'<h2>{week["label"]} <span class="week-count">{count} task{"s" if count != 1 else ""}</span></h2>')
			print('<table>')
			print('<tr><th>Task</th><th>Completed</th><th>In stack</th><th>Active</th></tr>')
			# Newest first within week
			for dt, entry in sorted(week['tasks'], key=lambda x: x[0], reverse=True):
				name       = entry.get('name', '(unnamed)')
				task_label = entry.get('label', '')
				abandoned  = entry.get('abandoned', False)
				comp_str   = dt.strftime('%a %b %d')
				age        = duration_str(entry.get('created_at',''), entry.get('completed_at',''))
				active_secs = entry.get('time_active', 0)
				active_str  = seconds_to_str(active_secs) if active_secs else '&mdash;'
				row_class  = ' class="abandoned"' if abandoned else ''
				print(f'<tr{row_class}>')
				# Name cell: label badge + name + abandoned marker
				abandoned_badge = '<span class="abandoned-badge">NOP</span>' if abandoned else ''
				print(f'<td class="taskname">{label_badge(task_label, entry.get("label_color",""))}{h(name)}{abandoned_badge}</td>')
				print(f'<td class="date-col">{h(comp_str)}</td>')
				print(f'<td class="age-col">{h(age)}</td>')
				print(f'<td class="age-col">{active_str}</td>')
				print(f'</tr>')
			print('</table>')

	print(f'<p style="font-size:10px;color:#bbb;margin-top:16px;">done.py</p>')
	print('</div></body></html>')

main()
