import axios from "axios";
import { getStoredLanguage } from "../i18n/i18n";

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

// Redirige vers /login si token expiré
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default API;
