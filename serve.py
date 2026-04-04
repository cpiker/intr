#!/usr/bin/env python3
#
# serve.py -- Standalone HTTP server for INTR (development / laptop use only)
#
# Requires python3.7 or higher.
#
# NOT intended for production or network-accessible deployment.
#
# For production use, just deploy:
#
#     tasks 
#     done 
#
# as CGI endpoint scripts under Apache httpd with appropriate auth
# and TLS configuration (see the readme).
#
# Usage:
#   python3 serve.py [port]        (default port: 8088)
#
# Authentication is disabled in standalone mode -- all actions are
# permitted without credentials.
#
# Data files are stored in the same directory as serve.py by default.
# The server only accepts connections from localhost.
#
# Requires Python 3.x stdlib only, *no* third-party packages, *no* need
# for a venv.

import http.server
import os
import subprocess
import sys
import urllib.parse

# ########################################################################### #
# configuration #

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8088

# These route names must match TASKS_SCRIPT_NAME and DONE_SCRIPT_NAME in
# tasks and done respectively.  If you change them there, change them
# here too.
TASKS_ROUTE = 'tasks'
DONE_ROUTE  = 'done'

# ########################################################################### #

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Map friendly route name -> script file path on disk.
ROUTES = {
	TASKS_ROUTE: os.path.join(SCRIPT_DIR, 'tasks'),
	DONE_ROUTE:  os.path.join(SCRIPT_DIR, 'done'),
}


class INTRHandler(http.server.BaseHTTPRequestHandler):
	"""Minimal HTTP handler.  Matches the request path to a script,
	builds a CGI-spec environment by hand, runs the script as a
	subprocess, and pipes stdout straight back to the client.

	No magic.  No framework.  Just os.environ and a pipe."""

	def _resolve(self):
		"""Return (friendly_name, script_path, query_string) for the
		current request, or (None, None, None) if not a known route."""
		parts = self.path.split('?', 1)
		path  = parts[0].lstrip('/')
		qs    = parts[1] if len(parts) > 1 else ''
		for friendly, script in ROUTES.items():
			if path == friendly:
				return friendly, script, qs
		return None, None, None

	def _run_cgi(self, friendly, script, qs, body=b''):
		"""Build a CGI environment, run the script, send output to client."""

		# --- CGI environment ---
		# These are the variables Apache would set.  We build them by hand
		# so we know exactly what the script sees -- no surprises.
		env = {
			# Process environment passthrough (PATH, HOME, etc.)
			**os.environ,

			# CGI spec variables
			'GATEWAY_INTERFACE': 'CGI/1.1',
			'SERVER_SOFTWARE':   'INTR-serve/1.0',
			'SERVER_NAME':       'localhost',
			'SERVER_PORT':       str(PORT),
			'SERVER_PROTOCOL':   'HTTP/1.1',
			'REQUEST_METHOD':    self.command,
			'SCRIPT_NAME':       f'/{friendly}',
			'PATH_INFO':         '',
			'QUERY_STRING':      qs,
			'CONTENT_TYPE':      self.headers.get('Content-Type', ''),
			'CONTENT_LENGTH':    str(len(body)),
			'HTTP_HOST':         f'localhost:{PORT}',

			# Auth: fake REMOTE_USER so is_authenticated() passes.
			# Apache sets this after validating HTTP Basic Auth credentials;
			# standalone mode skips auth entirely.
			'REMOTE_USER':       'local',
			'REMOTE_ADDR':       '127.0.0.1',

			# Data file locations.  tasks and done read these via
			# os.environ.get() with hardcoded paths as fallback defaults.
			'INTR_TASKS_FILE':   os.path.join(SCRIPT_DIR, 'tasks.json'),
			'INTR_DONE_DIR':     SCRIPT_DIR,
		}

		# --- Run script ---
		proc = subprocess.run(
			[sys.executable, script],
			input=body,
			capture_output=True,
			env=env,
			cwd=SCRIPT_DIR,
		)

		output = proc.stdout

		# --- Parse CGI headers from script output ---
		# CGI output is "Header: value\r\n...\r\n\r\nbody".
		# Split on the blank line to separate headers from body.
		if b'\r\n\r\n' in output:
			raw_headers, body_out = output.split(b'\r\n\r\n', 1)
		elif b'\n\n' in output:
			raw_headers, body_out = output.split(b'\n\n', 1)
		else:
			# Malformed output -- send as-is with a 500
			self.send_response(500)
			self.end_headers()
			self.wfile.write(output)
			return

		# Parse status and headers from the CGI header block.
		status  = 200
		headers = []
		for line in raw_headers.decode('utf-8', errors='replace').splitlines():
			if line.lower().startswith('status:'):
				try:
					status = int(line.split(':', 1)[1].strip().split()[0])
				except (ValueError, IndexError):
					pass
			elif ':' in line:
				headers.append(line.split(':', 1))

		# --- Send response ---
		self.send_response(status)
		for name, value in headers:
			self.send_header(name.strip(), value.strip())
		self.end_headers()
		self.wfile.write(body_out)

		# Log stderr from the script if any (script errors, etc.)
		if proc.stderr:
			sys.stderr.write(proc.stderr.decode('utf-8', errors='replace'))

	def do_GET(self):
		friendly, script, qs = self._resolve()
		if not friendly:
			self.send_response(404)
			self.end_headers()
			self.wfile.write(b'Not found')
			return
		self._run_cgi(friendly, script, qs)

	def do_POST(self):
		friendly, script, qs = self._resolve()
		if not friendly:
			self.send_response(404)
			self.end_headers()
			self.wfile.write(b'Not found')
			return
		length = int(self.headers.get('Content-Length', 0))
		body   = self.rfile.read(length)
		self._run_cgi(friendly, script, qs, body)

	def log_message(self, fmt, *args):
		# Suppress access log noise; only show error responses.
		if args and len(args) >= 2 and str(args[1]).startswith(('4', '5')):
			super().log_message(fmt, *args)


# Bind to localhost only -- not accessible from the network.
with http.server.HTTPServer(('127.0.0.1', PORT), INTRHandler) as httpd:
	print(f'INTR running at http://localhost:{PORT}/{TASKS_ROUTE}')
	print(f'           done: http://localhost:{PORT}/{DONE_ROUTE}')
	print('Ctrl-C to stop.')
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('\nStopped.')
