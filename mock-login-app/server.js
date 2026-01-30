const express = require('express');
const cookieParser = require('cookie-parser');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());

// In-memory session store (for demo purposes)
const sessions = new Map();

// Test credentials
const TEST_USER = 'testuser';
const TEST_PASS = 'testpass123';

// Generate session ID
function generateSessionId() {
  return crypto.randomBytes(32).toString('hex');
}

// HTML templates
const loginPage = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mock Login - Browser Session Research</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 0;
      color: #fff;
    }
    .container {
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      padding: 40px;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    h1 {
      margin: 0 0 8px 0;
      font-size: 24px;
      color: #63D297;
    }
    .subtitle {
      color: #aaa;
      margin-bottom: 24px;
      font-size: 14px;
    }
    .form-group {
      margin-bottom: 16px;
    }
    label {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
      color: #ccc;
    }
    input {
      width: 100%;
      padding: 12px;
      border: 1px solid rgba(255,255,255,0.2);
      border-radius: 8px;
      background: rgba(255,255,255,0.1);
      color: #fff;
      font-size: 16px;
      box-sizing: border-box;
    }
    input:focus {
      outline: none;
      border-color: #63D297;
    }
    button {
      width: 100%;
      padding: 14px;
      border: none;
      border-radius: 8px;
      background: #63D297;
      color: #1a1a2e;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      margin-top: 8px;
    }
    button:hover {
      background: #4db87d;
    }
    .error {
      background: rgba(255,100,100,0.2);
      color: #ff6b6b;
      padding: 12px;
      border-radius: 8px;
      margin-bottom: 16px;
      font-size: 14px;
    }
    .hint {
      margin-top: 20px;
      padding: 12px;
      background: rgba(99,210,151,0.1);
      border-radius: 8px;
      font-size: 13px;
      color: #63D297;
    }
    code {
      background: rgba(0,0,0,0.3);
      padding: 2px 6px;
      border-radius: 4px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Mock Login</h1>
    <p class="subtitle">Browser Session Research Test Page</p>

    {{ERROR}}

    <form action="/login" method="POST">
      <div class="form-group">
        <label for="username">Username</label>
        <input type="text" id="username" name="username" placeholder="Enter username" required autocomplete="username">
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" placeholder="Enter password" required autocomplete="current-password">
      </div>
      <button type="submit">Sign In</button>
    </form>

    <div class="hint">
      <strong>Test credentials:</strong><br>
      Username: <code>testuser</code><br>
      Password: <code>testpass123</code>
    </div>
  </div>
</body>
</html>
`;

const protectedPage = (username, sessionId) => `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Protected Area - Mock Login</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 0;
      color: #fff;
    }
    .container {
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      padding: 40px;
      width: 100%;
      max-width: 500px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    h1 {
      margin: 0 0 8px 0;
      font-size: 24px;
      color: #63D297;
    }
    .success {
      background: rgba(99,210,151,0.2);
      color: #63D297;
      padding: 16px;
      border-radius: 8px;
      margin: 16px 0;
    }
    .session-info {
      background: rgba(0,0,0,0.3);
      padding: 16px;
      border-radius: 8px;
      margin: 16px 0;
      font-family: monospace;
      font-size: 12px;
      word-break: break-all;
    }
    .session-info h3 {
      margin: 0 0 8px 0;
      color: #aaa;
      font-size: 12px;
      text-transform: uppercase;
    }
    a {
      color: #63D297;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    button {
      padding: 12px 24px;
      border: none;
      border-radius: 8px;
      background: #ff6b6b;
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      margin-top: 16px;
    }
    button:hover {
      background: #ee5a5a;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Protected Area</h1>

    <div class="success">
      You are logged in as <strong>${username}</strong>
    </div>

    <div class="session-info">
      <h3>Session Cookie</h3>
      session_id=${sessionId}
    </div>

    <div class="session-info">
      <h3>LocalStorage Token</h3>
      <span id="ls-token">Loading...</span>
    </div>

    <p>This page demonstrates a successful authenticated session. The session can be:</p>
    <ul>
      <li>Captured via Playwright's <code>context.storage_state()</code></li>
      <li>Exported manually via DevTools or browser extensions</li>
      <li>Injected into new browser contexts</li>
    </ul>

    <form action="/logout" method="POST">
      <button type="submit">Logout</button>
    </form>
  </div>

  <script>
    // Set localStorage token on login
    const token = 'auth_token_' + '${sessionId}'.substring(0, 16);
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user', '${username}');
    localStorage.setItem('login_time', new Date().toISOString());

    // Display token
    document.getElementById('ls-token').textContent = token;
  </script>
</body>
</html>
`;

// Routes
app.get('/', (req, res) => {
  const sessionId = req.cookies.session_id;

  if (sessionId && sessions.has(sessionId)) {
    return res.redirect('/protected');
  }

  res.send(loginPage.replace('{{ERROR}}', ''));
});

app.post('/login', (req, res) => {
  const { username, password } = req.body;

  if (username === TEST_USER && password === TEST_PASS) {
    const sessionId = generateSessionId();
    sessions.set(sessionId, { username, createdAt: new Date() });

    // Set session cookie (httpOnly for security, but still capturable by Playwright)
    res.cookie('session_id', sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 24 * 60 * 60 * 1000 // 24 hours
    });

    // Also set a non-httpOnly cookie for easier inspection
    res.cookie('user', username, {
      httpOnly: false,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 24 * 60 * 60 * 1000
    });

    return res.redirect('/protected');
  }

  res.send(loginPage.replace('{{ERROR}}', '<div class="error">Invalid username or password</div>'));
});

app.get('/protected', (req, res) => {
  const sessionId = req.cookies.session_id;

  if (!sessionId || !sessions.has(sessionId)) {
    return res.redirect('/');
  }

  const session = sessions.get(sessionId);
  res.send(protectedPage(session.username, sessionId));
});

app.post('/logout', (req, res) => {
  const sessionId = req.cookies.session_id;

  if (sessionId) {
    sessions.delete(sessionId);
  }

  res.clearCookie('session_id');
  res.clearCookie('user');
  res.redirect('/');
});

// API endpoints for programmatic testing
app.get('/api/session', (req, res) => {
  const sessionId = req.cookies.session_id;

  if (!sessionId || !sessions.has(sessionId)) {
    return res.status(401).json({ authenticated: false });
  }

  const session = sessions.get(sessionId);
  res.json({
    authenticated: true,
    username: session.username,
    createdAt: session.createdAt
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'mock-login-app' });
});

app.listen(PORT, () => {
  console.log(`Mock Login App running on port ${PORT}`);
  console.log(`Test credentials: ${TEST_USER} / ${TEST_PASS}`);
});
