"use client";
import { ErrorState } from "@/components/ui";
export default function Error({ reset }: { reset: () => void }) {
  return (
    <ErrorState
      message="The page could not be loaded. Your saved data is unchanged."
      retry={reset}
    />
  );
}
