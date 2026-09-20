"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
export function useResource<T>(path: string | null) {
  const [state, setState] = useState<{
    path: string | null;
    data?: T;
    error?: string;
  }>({ path: null });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!path) return;
    let active = true;
    api<T>(path)
      .then((data) => {
        if (active) setState({ path, data });
      })
      .catch((e: Error) => {
        if (active) setState({ path, error: e.message });
      });
    return () => {
      active = false;
    };
  }, [path, revision]);
  return {
    data: state.path === path ? state.data : undefined,
    error: state.path === path ? state.error : undefined,
    reload: () => setRevision((r) => r + 1),
  };
}
