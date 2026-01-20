import { useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Header } from "./components/Header";
import { AuthModal } from "./components/AuthModal";
import { AuthProvider } from "./contexts/AuthContext";
import { RecipeList } from "./components/RecipeList";
import { ClipRecipePage } from "./components/ClipRecipePage";
import { SavedRecipeView } from "./components/SavedRecipeView";
import { useRequireAuth } from "./hooks/useRequireAuth";

function HomePage() {
  const { isAuthorized } = useRequireAuth();

  // Unauthenticated users see the clip page directly
  if (!isAuthorized) {
    return <ClipRecipePage />;
  }

  // Authenticated users see their recipe collection
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-brown-dark">My Recipes</h2>
          <p className="text-brown-medium">Your saved recipes</p>
        </div>
        <Link
          to="/clip"
          className="w-10 h-10 flex items-center justify-center bg-coral text-white rounded-full hover:bg-coral-dark transition-colors"
          title="Add a recipe"
        >
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </Link>
      </div>

      <RecipeList />
    </div>
  );
}

function AppContent() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-cream">
        <Header onSignInClick={() => setIsAuthModalOpen(true)} />

        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
        />

        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/clip" element={<ClipRecipePage />} />
            <Route path="/recipes/:id" element={<SavedRecipeView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
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
