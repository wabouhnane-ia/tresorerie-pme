import { useState, createContext, useContext, useSyncExternalStore } from "react";
import { authService } from "../services/authService";

// Create a simple store to avoid hydration mismatch
function createAuthStore() {
  let listeners = new Set();
  let currentUser = (() => {
    if (typeof window === "undefined") return null;
    return authService.getUser();
  })();
  let currentIsAuth = (() => {
    if (typeof window === "undefined") return false;
    return authService.isAuthenticated();
  })();

  return {
    getUser: () => currentUser,
    getIsAuth: () => currentIsAuth,
    setUser: (user) => {
      currentUser = user;
      listeners.forEach((l) => l());
    },
    setIsAuth: (isAuth) => {
      currentIsAuth = isAuth;
      listeners.forEach((l) => l());
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

const authStore = createAuthStore();

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const user = useSyncExternalStore(authStore.subscribe, authStore.getUser, () => null);
  const isAuth = useSyncExternalStore(authStore.subscribe, authStore.getIsAuth, () => false);
  const [loading, setLoading] = useState(false);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const data = await authService.login(email, password);
      authStore.setUser(data.user);
      authStore.setIsAuth(true);
      return data;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    authStore.setUser(null);
    authStore.setIsAuth(false);
  };

  const createCompany = async (name, sector, city) => {
    const data = await authService.createCompany(name, sector, city);
    // Recharge le user depuis /auth/me pour avoir le company_id à jour
    const me = await authService.getMe();
    authStore.setUser(me);
    if (typeof window !== "undefined") {
      localStorage.setItem("user", JSON.stringify(me));
    }
    return data;
  };

  return (
    <AuthContext.Provider value={{
      user, isAuth, loading,
      login, logout, createCompany
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}