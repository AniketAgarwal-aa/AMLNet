import React from 'react';

export function Loading({ message = 'Loading intelligence data…' }) {
  return (
    <div className="loading-box" role="status">
      <div className="spinner" />
      <span>{message}</span>
    </div>
  );
}

export function ErrorBanner({ error, retry }) {
  return (
    <div className="error-banner" role="alert">
      <div>
        <strong>Error: </strong>
        <span>{error?.message || error || 'Unable to complete request.'}</span>
      </div>
      {retry && <button className="secondary" onClick={retry}>Retry</button>}
    </div>
  );
}
