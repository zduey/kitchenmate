import { useState, useRef } from "react";
import { Recipe } from "../types/recipe";

interface CookModeProps {
  recipe: Recipe;
  onClose: () => void;
}

export function CookMode({ recipe, onClose }: CookModeProps) {
  const [activeTab, setActiveTab] = useState<"ingredients" | "instructions">("ingredients");
  const [checkedIngredients, setCheckedIngredients] = useState<Set<number>>(new Set());
  const [currentStep, setCurrentStep] = useState(0);

  const touchStartX = useRef<number | null>(null);

  const totalSteps = recipe.instructions.length;
  const checkedCount = checkedIngredients.size;

  const toggleIngredient = (index: number) => {
    setCheckedIngredients((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const goNext = () => setCurrentStep((s) => Math.min(s + 1, totalSteps - 1));
  const goPrev = () => setCurrentStep((s) => Math.max(s - 1, 0));

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const delta = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(delta) > 50) {
      if (delta > 0) goNext();
      else goPrev();
    }
    touchStartX.current = null;
  };

  return (
    <div className="fixed inset-0 z-50 bg-cream flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 shrink-0">
        <button
          onClick={onClose}
          className="p-2 -ml-2 text-brown-medium hover:text-coral rounded-lg"
          aria-label="Exit cook mode"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <h1 className="font-serif text-lg font-semibold text-brown-dark truncate flex-1">
          {recipe.title}
        </h1>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 shrink-0">
        <button
          onClick={() => setActiveTab("ingredients")}
          className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "ingredients"
              ? "border-coral text-coral"
              : "border-transparent text-brown-medium hover:text-brown-dark"
          }`}
        >
          Ingredients
          {checkedCount > 0 && (
            <span className="ml-2 px-1.5 py-0.5 bg-coral bg-opacity-10 text-coral text-xs rounded-full">
              {checkedCount}/{recipe.ingredients.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("instructions")}
          className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "instructions"
              ? "border-coral text-coral"
              : "border-transparent text-brown-medium hover:text-brown-dark"
          }`}
        >
          Instructions
        </button>
      </div>

      {/* Content */}
      {activeTab === "ingredients" ? (
        <div className="flex-1 overflow-y-auto">
          <ul className="px-4 py-3 divide-y divide-gray-100">
            {recipe.ingredients.map((ingredient, index) => {
              const checked = checkedIngredients.has(index);
              const text = ingredient.display_text || ingredient.name;
              return (
                <li key={index}>
                  <button
                    onClick={() => toggleIngredient(index)}
                    className="w-full flex items-center gap-3 py-3 text-left"
                  >
                    <span
                      className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                        checked
                          ? "bg-coral border-coral"
                          : "border-gray-300"
                      }`}
                    >
                      {checked && (
                        <svg className="h-3.5 w-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </span>
                    <span
                      className={`text-base leading-snug transition-colors ${
                        checked ? "line-through text-brown-medium opacity-50" : "text-brown-dark"
                      }`}
                    >
                      {text}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {/* Progress footer */}
          <div className="px-4 py-3 text-center text-sm text-brown-medium border-t border-gray-100">
            {checkedCount === recipe.ingredients.length && checkedCount > 0
              ? "All ingredients gathered!"
              : `${checkedCount} of ${recipe.ingredients.length} gathered`}
          </div>
        </div>
      ) : (
        <div
          className="flex-1 flex flex-col"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          {/* Progress indicator */}
          <div className="flex flex-col items-center gap-2 pt-5 px-4 shrink-0">
            <p className="text-sm text-brown-medium">
              Step {currentStep + 1} of {totalSteps}
            </p>
            <div className="flex gap-1.5">
              {recipe.instructions.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentStep(i)}
                  aria-label={`Go to step ${i + 1}`}
                  className={`rounded-full transition-all ${
                    i === currentStep
                      ? "w-4 h-2.5 bg-coral"
                      : i < currentStep
                      ? "w-2.5 h-2.5 bg-coral opacity-40"
                      : "w-2.5 h-2.5 bg-gray-300"
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Step text */}
          <div className="flex-1 flex items-center justify-center px-6 py-8">
            <p className="font-serif text-xl sm:text-2xl text-brown-dark leading-relaxed text-left">
              {recipe.instructions[currentStep]}
            </p>
          </div>

          {/* Navigation */}
          <div className="flex gap-3 px-4 pb-6 shrink-0">
            <button
              onClick={goPrev}
              disabled={currentStep === 0}
              className="flex-1 py-3.5 rounded-xl border border-gray-300 text-brown-medium font-medium disabled:opacity-30 hover:bg-gray-50 active:bg-gray-100 transition-colors"
            >
              ← Prev
            </button>
            {currentStep < totalSteps - 1 ? (
              <button
                onClick={goNext}
                className="flex-1 py-3.5 rounded-xl bg-coral text-white font-medium hover:bg-coral-dark active:opacity-90 transition-colors"
              >
                Next →
              </button>
            ) : (
              <button
                onClick={onClose}
                className="flex-1 py-3.5 rounded-xl bg-coral text-white font-medium hover:bg-coral-dark active:opacity-90 transition-colors"
              >
                Done
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
