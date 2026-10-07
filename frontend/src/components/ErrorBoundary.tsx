import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught component error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0f0f11] text-zinc-100 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 mb-4">
            <AlertTriangle className="w-6 h-6 text-zinc-400" />
          </div>
          <h2 className="text-base font-medium text-zinc-100 mb-2">Interface Recovery</h2>
          <p className="text-xs text-zinc-500 max-w-md mb-6 font-mono">
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-zinc-100 hover:bg-white text-zinc-900 rounded-xl text-xs font-mono font-medium flex items-center gap-2 transition-all shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Dashboard</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
