import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useNavigate } from "react-router-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { useTranslation } from "@/i18n/LanguageProvider";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({
    email: "",
    password: "",
    firstName: "",
    lastName: "",
  });
  const [error, setError] = useState(null);
  const { t } = useTranslation();

  const getErrorMessage = (e) => {
    if (typeof e === "string") return e;
    const detail = e?.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
    return t('auth.genericError');
  };

  const handleSubmit = async () => {
    setError(null);
    try {
      if (mode === "login") {
        await login(form.email, form.password);
        navigate("/", { replace: true });
      } else {
        const { authService } = await import("../services/authService");
        await authService.register(form.email, form.password, form.firstName, form.lastName);
        await login(form.email, form.password);
        navigate("/", { replace: true });
      }
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-b from-muted/30 to-background px-4">
      <div className="absolute right-6 top-6">
        <ThemeToggle />
      </div>
      
      <Card className="w-full max-w-md border-border shadow-xl shadow-foreground/5">
        <CardHeader className="space-y-2 pb-8 text-center">
          <div className="flex justify-center mb-2">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Lock className="h-6 w-6 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">
            {t('app.name')}
          </CardTitle>
          <CardDescription className="text-base">
            {mode === "login" ? t('auth.loginTitle') : t('auth.registerTitle')}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-5">
          {mode === "register" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label htmlFor="firstName" className="text-sm font-medium text-foreground">
                  {t('auth.firstName')}
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="firstName"
                    placeholder={t('auth.firstName')}
                    value={form.firstName}
                    onChange={set("firstName")}
                    className="pl-10"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label htmlFor="lastName" className="text-sm font-medium text-foreground">
                  {t('auth.lastName')}
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="lastName"
                    placeholder={t('auth.lastName')}
                    value={form.lastName}
                    onChange={set("lastName")}
                    className="pl-10"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium text-foreground">
              {t('auth.email')}
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="email"
                placeholder={t('auth.email')}
                type="email"
                value={form.email}
                onChange={set("email")}
                className="pl-10"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                {t('auth.password')}
              </label>
              {mode === "login" && (
                <button type="button" className="text-xs text-primary hover:underline font-medium">
                  {t('auth.password')}
                </button>
              )}
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="password"
                placeholder="••••••••"
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={set("password")}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                className="pl-10 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="text-sm border-destructive/30 bg-destructive/5">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button type="button" onClick={handleSubmit} className="w-full">
            {mode === "login" ? t('auth.login') : t('auth.register')}
          </Button>

          <p className="text-center text-sm text-muted-foreground pt-2">
            {mode === "login" ? t('auth.noAccount') : t('auth.hasAccount')}{" "}
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="font-semibold text-primary hover:underline transition-colors"
            >
              {mode === "login" ? t('auth.signUp') : t('auth.signIn')}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
