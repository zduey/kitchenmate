interface LoadingSpinnerProps {
  message?: string;
}

export function LoadingSpinner({ message = "Extracting recipe..." }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-coral"></div>
      <span className="ml-3 text-brown-medium">{message}</span>
    </div>
  );
}
