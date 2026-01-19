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

  return (
    <div>
      {/* Page header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">My Recipes</h2>
          <p className="text-gray-600">
            Your collection of saved recipes
          </p>
        </div>
        <Link
          to="/add"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <svg
            className="h-5 w-5 mr-2"
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
          Add Recipe
        </Link>
      </div>

      {/* Recipe list or sign-in prompt */}
      {isAuthorized ? (
        <RecipeList />
      ) : (
        <div className="py-12 text-center">
          <div className="text-gray-400 mb-4">
            <svg
              className="h-16 w-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Sign in to view your recipes
          </h3>
          <p className="text-gray-600 mb-6">
            Create an account or sign in to start building your recipe collection.
          </p>
          <Link
            to="/add"
            className="text-blue-600 hover:text-blue-800"
          >
            Or clip a recipe without signing in
          </Link>
        </div>
      )}
    </div>
  );
}

function AppContent() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header onSignInClick={() => setIsAuthModalOpen(true)} />

        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
        />

        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/add" element={<ClipRecipePage />} />
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
