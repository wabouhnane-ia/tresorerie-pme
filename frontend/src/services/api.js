import axios from "axios";
import { getStoredLanguage } from "../i18n/i18n";

// Simple in-memory cache
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
});

// Injecte automatiquement le token JWT et la locale française dans chaque requête
API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  const language = getStoredLanguage();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers["X-Locale"] = language;
  config.headers["Accept-Language"] = language;
  return config;
});

// Add caching for GET requests
API.interceptors.request.use((config) => {
  // Only cache GET requests
  if (config.method !== "get") {
    return config;
  }

  const cacheKey = `${config.url}__${JSON.stringify(config.params || {})}`;
  const cached = cache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    // Return cached response as a resolved promise
    return {
      ...config,
      adapter: () => Promise.resolve(cached.response),
    };
  }

  return config;
});

// Cache responses
API.interceptors.response.use(
  (response) => {
    if (response.config.method === "get") {
      const cacheKey = `${response.config.url}__${JSON.stringify(response.config.params || {})}`;
      cache.set(cacheKey, {
        response,
        timestamp: Date.now(),
      });
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Function to clear the cache manually (e.g., after an upload)
export const clearAPICache = () => {
  cache.clear();
};

export default API;
