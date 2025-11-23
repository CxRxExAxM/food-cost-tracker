import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

function Login() {
  const navigate = useNavigate();
  const { login, setup, setupRequired } = useAuth();

  const [isSetup, setIsSetup] = useState(false);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Auto-switch to setup mode if required
  useState(() => {
    if (setupRequired) {
      setIsSetup(true);
    }
  }, [setupRequired]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSetup || setupRequired) {
        await setup(email, username, password, fullName);
      } else {
        await login(email, password);
      }
      navigate('/');
    } catch (err) {
      console.error('Auth error:', err);
      setError(
        err.response?.data?.detail ||
        'Authentication failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Food Cost Tracker</h1>
          <p>{setupRequired || isSetup ? 'Create Admin Account' : 'Sign In'}</p>
        </div>

        {setupRequired && (
          <div className="setup-notice">
            Welcome! Create your admin account to get started.
          </div>
        )}

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="you@example.com"
            />
          </div>

          {(isSetup || setupRequired) && (
            <>
              <div className="form-group">
                <label htmlFor="username">Username</label>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="username"
                />
              </div>

              <div className="form-group">
                <label htmlFor="fullName">Full Name</label>
                <input
                  type="text"
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Smith"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="********"
            />
          </div>

          <button type="submit" className="btn-login" disabled={loading}>
            {loading
              ? 'Please wait...'
              : (isSetup || setupRequired)
                ? 'Create Account'
                : 'Sign In'}
          </button>
        </form>

        {!setupRequired && (
          <div className="login-footer">
            {isSetup ? (
              <button
                className="btn-toggle-mode"
                onClick={() => setIsSetup(false)}
              >
                Already have an account? Sign In
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

export default Login;
