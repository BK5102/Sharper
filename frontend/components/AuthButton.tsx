"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase-browser";
import type { User } from "@supabase/supabase-js";

interface Props {
  onAuthChange?: (signedIn: boolean) => void;
}

export function AuthButton({ onAuthChange }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [loaded, setLoaded] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user);
      onAuthChange?.(Boolean(data.user));
      setLoaded(true);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      onAuthChange?.(Boolean(session?.user));
    });
    return () => subscription.unsubscribe();
  }, [onAuthChange]);

  if (!loaded) {
    return <div className="h-8 w-20 rounded-md bg-zinc-100 dark:bg-zinc-800 animate-pulse" />;
  }

  if (user) {
    return (
      <button
        onClick={async () => {
          const supabase = createClient();
          await supabase.auth.signOut();
          router.push("/");
          router.refresh();
        }}
        className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors duration-150"
      >
        Sign out
      </button>
    );
  }

  return (
    <button
      onClick={() => router.push("/auth")}
      className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors duration-150"
    >
      Sign in
    </button>
  );
}
