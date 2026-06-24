import { Component } from "react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Error caught by ErrorBoundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback();
      }
      
      return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6 bg-background text-foreground">
          <h1 className="text-2xl font-bold mb-4">Oups ! Quelque chose s'est mal passé</h1>
          <p className="text-muted-foreground mb-4">Veuillez rafraîchir la page pour réessayer.</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Rafraîchir
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
