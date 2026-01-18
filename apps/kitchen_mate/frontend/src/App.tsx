import { useState } from "react";
import { Recipe } from "./types/recipe";
import { clipRecipe, ClipError } from "./api/clip";
import { RecipeForm } from "./components/RecipeForm";
import { RecipeCard } from "./components/RecipeCard";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { ErrorMessage } from "./components/ErrorMessage";
import { Header } from "./components/Header";
import { AuthModal } from "./components/AuthModal";
import { AuthProvider } from "./contexts/AuthContext";

type AppState =
  | { status: "idle" }
  | { status: "loading"; url: string; forceLlm: boolean }
  | { status: "success"; url: string; recipe: Recipe }
  | { status: "error"; url: string; forceLlm: boolean; message: string };

function AppContent() {
  const [state, setState] = useState<AppState>({ status: "idle" });
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const handleSubmit = async (url: string, forceLlm: boolean) => {
    setState({ status: "loading", url, forceLlm });

    try {
      const recipe = await clipRecipe(url, forceLlm);
      setState({ status: "success", url, recipe });
    } catch (error) {
      const message =
        error instanceof ClipError
          ? error.message
          : "An unexpected error occurred";
      setState({ status: "error", url, forceLlm, message });
    }
  };

  const handleRetry = () => {
    if (state.status === "error") {
      handleSubmit(state.url, state.forceLlm);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onSignInClick={() => setIsAuthModalOpen(true)} />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-8">
          <RecipeForm
            onSubmit={handleSubmit}
            isLoading={state.status === "loading"}
          />
        </div>

        {state.status === "loading" && (
          <LoadingSpinner message="Extracting recipe..." />
        )}

        {state.status === "error" && (
          <ErrorMessage message={state.message} onRetry={handleRetry} />
        )}

        {state.status === "success" && <RecipeCard recipe={state.recipe} />}
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
