"""
Renders a realistic-looking broker login page entirely locally, for brokers
where no real API key is configured. This lets the full OAuth-redirect UX
(browser redirect -> login -> redirect back with a token -> token exchange)
be demoed end-to-end without needing real broker credentials or risking a
live account. Real brokers are never contacted; the "login" just mints a
fake token and calls our own callback endpoint directly from the page.
"""

BROKER_THEME = {
    "zerodha": {"name": "Zerodha Kite", "color": "#387ed1", "field": "request_token"},
    "fyers": {"name": "Fyers", "color": "#f05a28", "field": "auth_code"},
    "upstox": {"name": "Upstox", "color": "#5c2d91", "field": "auth_code"},
}


def render_login_page(broker: str, user_id: str) -> str:
    theme = BROKER_THEME.get(broker, {"name": broker.title(), "color": "#444", "field": "auth_code"})
    token_field = theme["field"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Log in to {theme['name']}</title>
<style>
  body {{
    margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .card {{
    background: #fff; border-radius: 10px; padding: 36px 40px; width: 340px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  }}
  .brand {{ color: {theme['color']}; font-weight: 700; font-size: 1.3rem; margin-bottom: 4px; }}
  .sim-note {{
    font-size: 0.72rem; color: #a05a00; background: #fff6e5; border: 1px solid #f0d8a0;
    border-radius: 6px; padding: 6px 10px; margin-bottom: 18px;
  }}
  label {{ display: block; font-size: 0.78rem; color: #555; margin-bottom: 4px; }}
  input {{
    width: 100%; padding: 9px 10px; margin-bottom: 14px; border: 1px solid #ccc;
    border-radius: 6px; font-size: 0.9rem; box-sizing: border-box;
  }}
  button {{
    width: 100%; padding: 10px; background: {theme['color']}; color: #fff; border: none;
    border-radius: 6px; font-weight: 600; font-size: 0.9rem; cursor: pointer;
  }}
  button:disabled {{ opacity: 0.6; }}
  .status {{ font-size: 0.78rem; color: #888; margin-top: 10px; text-align: center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="brand">{theme['name']}</div>
    <div class="sim-note">Simulated login &mdash; no real {theme['name']} account is contacted. For demo purposes only.</div>
    <form id="loginForm">
      <label>User ID / Client Code</label>
      <input id="username" value="{user_id}" required>
      <label>Password</label>
      <input id="password" type="password" placeholder="any value works" required>
      <button type="submit" id="submitBtn">Log in</button>
      <div class="status" id="status"></div>
    </form>
  </div>
<script>
  document.getElementById('loginForm').addEventListener('submit', async (e) => {{
    e.preventDefault();
    const btn = document.getElementById('submitBtn');
    const status = document.getElementById('status');
    btn.disabled = true;
    status.textContent = 'Redirecting to {theme["name"]}...';

    const token = 'SIM-{broker.upper()}-' + Math.random().toString(36).slice(2, 10).toUpperCase();

    try {{
      const res = await fetch('/auth/{broker}/callback?user_id={user_id}', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ {token_field!r}: token }}),
      }});
      if (!res.ok) throw new Error(await res.text());
      status.textContent = 'Connected. Returning to app...';
      setTimeout(() => {{ window.location.href = '/ui/?connected={broker}'; }}, 600);
    }} catch (err) {{
      status.textContent = 'Login failed: ' + err.message;
      btn.disabled = false;
    }}
  }});
</script>
</body>
</html>"""
