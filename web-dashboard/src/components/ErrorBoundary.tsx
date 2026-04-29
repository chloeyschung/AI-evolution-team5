import { Component, ReactNode } from 'react';
import styles from './ErrorBoundary.module.css';

interface Props {
  children: ReactNode;
  onError?: (error: Error) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  // Global error handler
  errorHandler = (err: Error) => {
    this.setState({ hasError: true, error: err });
    if (this.props.onError) {
      this.props.onError(err);
    }
  };

  componentDidMount() {
    window.addEventListener('error', (event) => {
      this.errorHandler(event.error);
    });
    window.addEventListener('unhandledrejection', (event) => {
      this.errorHandler(event.reason as Error);
    });
  }

  componentWillUnmount() {
    window.removeEventListener('error', this.errorHandler as any);
    window.removeEventListener('unhandledrejection', this.errorHandler as any);
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  retry = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.errorBoundary}>
          <div className={styles.errorContainer}>
            <div className={styles.errorIcon}>⚠️</div>
            <h1>Something went wrong</h1>
            <p className={styles.errorMessage}>
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button onClick={this.retry} className={styles.retryBtn}>
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
