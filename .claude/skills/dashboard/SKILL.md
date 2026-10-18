---
name: dashboard
description: Start the local job-hunt dashboard (http://127.0.0.1:8765) and open it. Use for /dashboard, "abre el dashboard", "show my applications".
---

# /dashboard

1. Check whether it's already running: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/`.
2. If it isn't (anything but `200`), start it in the background with the Bash tool
   (`run_in_background: true`): `python3 tracker/dashboard.py`. Add `--port <n>` if 8765
   is taken by something else.
3. Give the user the URL. If Claude in Chrome is available, open it in a new tab.

The dashboard reads the database live; refresh the page to see new data. The only thing
it changes is marking a to-do as done.
