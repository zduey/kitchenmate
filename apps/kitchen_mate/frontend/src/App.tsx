import { useState, useEffect } from "react";
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

function SearchInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [localValue, setLocalValue] = useState(value);

  // Sync local value when URL value changes
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleSearch = () => {
    onChange(localValue);
  };

  const handleClear = () => {
    setLocalValue("");
    onChange("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="flex gap-2">
      <div className="relative flex-1">
        <input
          type="text"
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search recipes..."
          className="w-full pl-3 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
        />
        {localValue && (
          <button
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            title="Clear search"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      <button
        onClick={handleSearch}
        className="px-3 py-2 bg-coral text-white rounded-lg hover:bg-coral-dark transition-colors"
        title="Search"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </button>
    </div>
  );
}

function HomePage() {
  const { isAuthorized } = useRequireAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const viewMode = (searchParams.get("view") || "grid") as "grid" | "tags";
  const tagFilter = searchParams.get("tag");
  const searchQuery = searchParams.get("q") || "";

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
    newParams.delete("q"); // Clear search when selecting a tag
    setSearchParams(newParams);
  };

  const handleSearchChange = (query: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (query) {
      newParams.set("q", query);
      newParams.delete("view"); // Switch to grid view when searching
      newParams.delete("tag"); // Clear tag filter when searching
    } else {
      newParams.delete("q");
    }
    setSearchParams(newParams);
  };

  // Unauthenticated users see the clip page directly
  if (!isAuthorized) {
    return <ClipRecipePage />;
  }

  // Get subtitle text
  const getSubtitle = () => {
    if (searchQuery) return `Search results for "${searchQuery}"`;
    if (tagFilter === "__untagged__") return "Untagged recipes";
    if (tagFilter) return `Recipes tagged "${formatTagForDisplay(tagFilter)}"`;
    return "Your saved recipes";
  };

  // Authenticated users see their recipe collection
  return (
    <div>
      <div className="flex items-center gap-6 mb-6">
        <div className="shrink-0">
          <h2 className="text-xl font-semibold text-brown-dark">My Recipes</h2>
          <p className="text-brown-medium">{getSubtitle()}</p>
        </div>
        <div className="flex-1 max-w-md mx-auto">
          <SearchInput value={searchQuery} onChange={handleSearchChange} />
        </div>
        <div className="flex items-center gap-6 shrink-0">
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

      {(tagFilter || searchQuery) && (
        <button
          onClick={() => {
            const newParams = new URLSearchParams(searchParams);
            newParams.delete("tag");
            newParams.delete("q");
            setSearchParams(newParams);
          }}
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
        searchQuery={searchQuery}
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
