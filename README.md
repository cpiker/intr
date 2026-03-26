![People pushing INTR high](img/intr-banner-fade.svg)

# INTR

A single-user task tracker for people with more work than time.  Named after
the interrupt request pin on the Intel 8088 — because *something* is always
driving that pin high.

The queue is priority-ordered top to bottom, but tasks don't have to be
handled in priority order.  You grab whatever makes sense to work on, and
the top slot shows what you're currently doing.  Finished tasks move to a
yearly done archive.  Co-workers can see your queue without logging in.
Only you can change anything.

![Task page screenshot](img/screenshot.png)

## Requirements

- Apache 2.4 with `mod_cgi` and `mod_rewrite`
- Python 3 (stdlib only — no third-party packages)
- A machine on a trusted internal network

## Configuration

The site is driven by two python files that are symlinked (or just copied)
into your CGI area.

```
tasks.py            Main task queue (CGI script)
done.py             Completed task archive (CGI script)
```

There are no external configuration files.  

To configure for your site, adjust path and URL constants in `tasks.py` and `done.py`.
Set them to what ever you like, but the values entered here must be consistent with
the ScriptAlias lines in your Apache config

```python
TASKS_SCRIPT_NAME = 'intr'    # External end-point name from apache config below
DONE_SCRIPT_NAME = 'handled'  # External end-point name from apache config below
TASKS_FILE = '/var/www/taskdata/tasks.json'
DONE_DIR   = '/var/www/taskdata'
```

All task data are contained in JSON files. This not the most efficent but
easier then setting up an external RDBMS.  Pick a directory that you prefer
that's **not** under the web root, for example `/var/www/taskdata`.  In that
case the layout will look similar to the following after data are entered.

```
/var/www/taskdata/
    tasks.json          Current queue — auto-created on first write
    done_2026.json      Completed tasks for the year — auto-created
    done_2025.json      Previous years accumulate here automatically
    ...
```

At year-end, `done_YYYY.json` stays in place and a new file is created for
the incoming year.  The done page auto-detects all `done_*.json` files in the
data directory and shows a year selector when more than one is present.
Nothing needs to be done manually.

You don't have to configure the location of the banners. They are embedded 
as strings in the python code. They're only provided standalone for ease
of updates. Updating the images will do nothing on it's own, you'll have
re-insert them into the CGI scripts to see any changes.


## Installation

I'm assuming you're using Apache2 for hosting services at your site.  To setup
**INTER** run though the following steps.

### 1. Enable Apache modules

```bash
sudo a2enmod cgi rewrite
sudo systemctl restart apache2
```

### 2. Make scripts executable and symlink into place

```bash
chmod 755 /path/to/tasks.py /path/to/done.py
ln -s /path/to/tasks.py /var/www/cgi-bin/tasks.py   # or just copy them in
ln -s /path/to/done.py  /var/www/cgi-bin/done.py
```

`/var/www/cgi-bin/` is the script directory used in the example Apache config
below.  Adjust to taste.  

### 3. Create the data directory

```bash
sudo mkdir -p /var/www/taskdata
sudo chown www-data:www-data /var/www/taskdata
sudo chmod 750 /var/www/taskdata
```

### 4. Apache VirtualHost config

GETs are served freely.  POSTs are silently rewritten to an auth-protected
location.  Both aliases point at the same script directory so the same files
handle both.  The `LocationMatch` block scopes the rewrite to only these two
scripts — other CGI on the server is unaffected.

Add the following, or similar inside your `<VirtualHost>` block.
There's a million ways to configure Apache.  This is just an example.

```apache
    # Setup for the task tracker, Apache directive processing order noted.
    #
    # 1. URL is mapped to a filesystem path via ScriptAlias
    # 2. LocationMatch fires on the URL, POSTs get rewritten to "/intr-auth/$1"
    # 3. ScriptAlias maps the rewritten URL to the same filesystem path
    # 4. Location "/intr-auth/" matches the rewritten URL, requires auth
    # 5. Directory applies ExecCGI and access controls to the filesystem path
    
    # 1: Which URLs triggers which scripts
    #  
    #    Make sure the corresponding TASKS_SCRIPT_NAME & DONE_SCRIPT_NAME
    #    values are set in tasks.py and done.py
    <IfModule alias_module>
        ScriptAlias /intr                "/var/www/cgi-me/tasks.py"
        ScriptAlias /handled             "/var/www/cgi-me/done.py"
        ScriptAlias /intr-auth/intr      "/var/www/cgi-me/tasks.py"
        ScriptAlias /intr-auth/handled   "/var/www/cgi-me/done.py"
    </IfModule>
    
    # 2: If any of the end-points listed above use the POST method,
    #    rewrite the URL and add a fictitious sub-directory.
    #
    #    Since the location is new, it's going to re-trigger the
    #    ScriptAlais lookup above.
    <LocationMatch "^/(intr|handled)$">
        RewriteEngine On
        RewriteCond %{REQUEST_METHOD} POST
        RewriteRule ^/(intr|handled)$ /intr-auth/$1 [PT,L]
    </LocationMatch>
    
    # 3 (4 if POST): Selective Authentication
    #
    # If our fictitious sub-directory is detected, require authentication
    <Location "/intr-auth/">
        AuthType Basic
        AuthName "Interrupt Request Pending"
        AuthUserFile /etc/apache2/taskstack.passwd
        Require valid-user
    </Location>


    # 4 (5 if POST): Access control 
    #
    #   Regardless of the URL or request method, apply these
    #   access controls to the on-disk assests
    <Directory "/var/www/cgi-me">
        Options ExecCGI FollowSymLinks
        AddHandler cgi-script .py
        Require ip 127.0.0.1 ::1
        Require host .uiowa.edu
    </Directory>
```
Adjust the `Require ip` and `Require host` lines to match the networks and
domains you want to allow read access from.

### 5. Create the password file

```bash
sudo htpasswd -c /etc/apache2/taskstack.passwd yourusername
sudo chown root:www-data /etc/apache2/taskstack.passwd
sudo chmod 640 /etc/apache2/taskstack.passwd
```

After this, `GET /cgi-bin/tasks.py` is open to anyone matching the `Require`
directives in the `Directory` block.  POST requests trigger a Basic Auth
challenge.  `REMOTE_USER` is set by Apache after a successful login and the
scripts check it before acting on any write operation.

## Usage

### Task queue (tasks.py)

| Action | Description |
|--------|-------------|
| Push new task | Add a task at the top (becomes current), at position #2, or at the bottom |
| Work on | Grab any queued task — it becomes current, old current returns to top of queue |
| ▲ / ▼ | Nudge a task up or down in the queue without touching the current task |
| Mark done | Completes the current task, logs it to `done_YYYY.json`, promotes the next queued task |
| Done (from queue) | Complete a queued task without grabbing it first |
| Drop | Delete a task permanently with no log entry |
| Edit | Edit the name or notes of any task inline |
| Set idle | Parks the current task back at the top of the queue, sets state to Idle (HLT) |

All write actions require HTTP Basic Auth.  Read access is open.

### Done archive (done.py)

Completed tasks grouped by ISO calendar week, newest week first.  Columns:
task name, date completed, time spent in the stack.

A year selector appears automatically when more than one year's data is
present.  No cron job or manual action is needed at year-end — the scripts
detect the current year and create a new file automatically.

## Network and security notes

To post data you'll need to provide a password over the internet. *Obviously*
you'll host this under HTTPS... right.  

Even with HTTPS enabled, INTR is designed for use on a **trusted internal network**.  
The scripts do not implement CSRF protection.  On an internal network behind
a firewall this is generally acceptable for a single-user tool, but check your
local web-service security guidelines before making assumptions.

![INTR services or device gave up](img/intr-banner-done-fade.svg)

**AI disclosure**
> This code was generated in cooperation with Claude, which is an Artificial 
> Intelligence service provided by Anthropic. Though design and development was
> orchestrated by a human, reviewed by a human and tested by a human, most of 
> the actual code was composed by an AI.
>
> It is completely reasonable to forbid AI generated software in some contexts.
> Please check the contribution guidelines of any projects you participate in.
> If the project has a rule against AI generated software then DO NOT INCLUDE
> THESE FILES, in whole or in part, in your patches or pull requests.

