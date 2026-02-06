import './LoadingSpinner.css';

/**
 * Reusable loading spinner component.
 *
 * @param {string} size - 'sm' | 'md' | 'lg' (default: 'md')
 * @param {string} message - Optional loading message
 * @param {boolean} fullScreen - If true, centers in viewport (default: false)
 * @param {boolean} inline - If true, displays inline (default: false)
 */
export default function LoadingSpinner({
  size = 'md',
  message,
  fullScreen = false,
  inline = false
}) {
  const spinnerClass = `loading-spinner loading-spinner--${size}`;

  if (inline) {
    return (
      <span className="loading-inline">
        <span className={spinnerClass}></span>
        {message && <span className="loading-message-inline">{message}</span>}
      </span>
    );
  }

  if (fullScreen) {
    return (
      <div className="loading-screen">
        <div className={spinnerClass}></div>
        {message && <p className="loading-message">{message}</p>}
      </div>
    );
  }

  return (
    <div className="loading-container">
      <div className={spinnerClass}></div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
}
