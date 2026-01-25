import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Header } from "./components/Header";
import { AuthModal } from "./components/AuthModal";
import { AuthProvider } from "./contexts/AuthContext";
import { RecipeList } from "./components/RecipeList";
import { AddFromUrlPage } from "./components/AddFromUrlPage";
import { AddFromUploadPage } from "./components/AddFromUploadPage";
import { AddManualPage } from "./components/AddManualPage";
import { SavedRecipeView } from "./components/SavedRecipeView";
import { AddRecipeDropdown } from "./components/AddRecipeDropdown";
import { useRequireAuth } from "./hooks/useRequireAuth";

function HomePage() {
  const { isAuthorized } = useRequireAuth();

  // Unauthenticated users see the URL clip page directly
  if (!isAuthorized) {
    return <AddFromUrlPage />;
  }

  // Authenticated users see their recipe collection
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-brown-dark">My Recipes</h2>
          <p className="text-brown-medium">Your saved recipes</p>
        </div>
        <AddRecipeDropdown variant="plus" />
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
            <Route path="/add/url" element={<AddFromUrlPage />} />
            <Route path="/add/upload" element={<AddFromUploadPage />} />
            <Route path="/add/manual" element={<AddManualPage />} />
            <Route path="/recipes/:id" element={<SavedRecipeView />} />
            {/* Redirect old /clip route to new /add/url */}
            <Route path="/clip" element={<Navigate to="/add/url" replace />} />
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
