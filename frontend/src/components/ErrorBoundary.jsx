import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('UI Uncaught Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel" style={{ margin: '40px auto', maxWidth: 600 }}>
          <h2 style={{ color: '#ef4444', marginBottom: 10 }}>Workstation Interface Error</h2>
          <p style={{ color: '#96adcc', marginBottom: 20 }}>
            {this.state.error?.message || 'An unexpected rendering error occurred in this view.'}
          </p>
          <button onClick={() => window.location.reload()}>Reload Workstation</button>
        </div>
      );
    }
    return this.props.children;
  }
}
