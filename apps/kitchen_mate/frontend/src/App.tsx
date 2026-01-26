import { useState } from "react";
import { BrowserRouter, Routes, Route, Link, useSearchParams } from "react-router-dom";
import { Header } from "./components/Header";
import { AuthModal } from "./components/AuthModal";
import { AuthProvider } from "./contexts/AuthContext";
import { RecipeList } from "./components/RecipeList";
import { ClipRecipePage } from "./components/ClipRecipePage";
import { SavedRecipeView } from "./components/SavedRecipeView";
import { ViewModeToggle } from "./components/ViewModeToggle";
import { useRequireAuth } from "./hooks/useRequireAuth";
import { formatTagForDisplay } from "./utils/tags";

function HomePage() {
  const { isAuthorized } = useRequireAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const viewMode = (searchParams.get("view") || "grid") as "grid" | "tags";
  const tagFilter = searchParams.get("tag");

  const handleViewChange = (mode: "grid" | "tags") => {
    const newParams = new URLSearchParams(searchParams);
    if (mode === "grid") {
      newParams.delete("view");
    } else {
      newParams.set("view", mode);
    }
    newParams.delete("tag");
    setSearchParams(newParams);
  };

  const handleTagSelect = (tag: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (tag) {
      newParams.set("tag", tag);
      newParams.delete("view");
    } else {
      newParams.delete("tag");
    }
    setSearchParams(newParams);
  };

  // Unauthenticated users see the clip page directly
  if (!isAuthorized) {
    return <ClipRecipePage />;
  }

  // Get subtitle text
  const getSubtitle = () => {
    if (tagFilter === "__untagged__") return "Untagged recipes";
    if (tagFilter) return `Recipes tagged "${formatTagForDisplay(tagFilter)}"`;
    return "Your saved recipes";
  };

  // Authenticated users see their recipe collection
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-brown-dark">My Recipes</h2>
          <p className="text-brown-medium">{getSubtitle()}</p>
        </div>
        <div className="flex items-center gap-3">
          <ViewModeToggle mode={viewMode} onChange={handleViewChange} />
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
      </div>

      {tagFilter && (
        <button
          onClick={() => handleTagSelect(null)}
          className="mb-4 inline-flex items-center gap-1 text-sm text-coral hover:text-coral-dark"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to all recipes
        </button>
      )}

      <RecipeList
        viewMode={viewMode}
        tagFilter={tagFilter}
        onTagSelect={handleTagSelect}
      />
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
