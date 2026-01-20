import { useState, FormEvent } from "react";
import { useAuthContext } from "../hooks/useAuthContext";
import { ErrorMessage } from "./ErrorMessage";

type AuthStep = "input" | "check-email";

export function AuthForm() {
  const [step, setStep] = useState<AuthStep>("input");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { signInWithMagicLink } = useAuthContext();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error: authError } = await signInWithMagicLink(email);
      if (authError) {
        setError(authError.message || "Failed to send magic link");
      } else {
        setStep("check-email");
      }
    } catch {
      setError("Failed to send magic link");
    } finally {
      setLoading(false);
    }
  };

  // Check Email Step
  if (step === "check-email") {
    return (
      <div className="text-center">
        <div className="mb-4 text-4xl">📧</div>
        <h2 className="text-2xl font-bold mb-4">Check your email</h2>
        <p className="text-brown-medium mb-6">
          We've sent a magic link to <strong>{email}</strong>
        </p>
        <p className="text-sm text-gray-500 mb-6">
          Click the link in the email to sign in. You can close this page.
        </p>
        <button
          onClick={() => setStep("input")}
          className="text-sm text-coral hover:underline"
        >
          Use a different email
        </button>
      </div>
    );
  }

  // Input Step
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 text-center">Sign In</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-brown-medium mb-1">
            Email address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-coral"
            required
            disabled={loading}
          />
        </div>

        {error && <ErrorMessage message={error} />}

        <button
          type="submit"
          disabled={loading}
          className="w-full px-6 py-2 bg-coral text-white font-medium rounded-lg hover:bg-coral-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Sending..." : "Send magic link"}
        </button>

        <p className="text-xs text-gray-500 text-center">
          We'll email you a magic link for a password-free sign in
        </p>
      </form>

      <p className="mt-6 text-xs text-center text-gray-500">
        By continuing, you agree to our Terms of Service and Privacy Policy
      </p>
    </div>
  );
}
