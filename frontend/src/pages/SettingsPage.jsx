import { useState, useRef } from "react";
import { useTranslation } from "@/i18n/LanguageProvider";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageSelector } from "@/components/LanguageSelector";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction } from "@/components/ui/alert-dialog";
import SubscriptionCard from "@/components/SubscriptionCard";
import {
  User,
  Palette,
  Bell,
  CreditCard,
  ShieldCheck,
  Trash2,
  Eye,
  EyeOff,
  CheckCircle2,
  Smartphone,
  Monitor,
  Sun,
  Moon,
  ChevronRight,
  Mail,
  MessageSquare,
  SmartphoneIcon,
  Download,
  XCircle,
  Camera,
  QrCode,
  Settings,
  AlertTriangle,
  RefreshCw
} from "lucide-react";

const LABELS = {
  "settings.title": "Paramètres",
  "settings.description": "Gérez votre compte et vos préférences",
  "settings.profile": "Profil",
  "settings.security": "Sécurité",
  "settings.appearance": "Apparence",
  "settings.notifications": "Notifications",
  "settings.subscription": "Abonnement",
  "settings.danger": "Zone de danger",
  "settings.profile.title": "Informations personnelles",
  "settings.profile.description": "Modifiez vos informations de profil",
  "settings.profile.firstName": "Prénom",
  "settings.profile.lastName": "Nom",
  "settings.profile.email": "Adresse e-mail",
  "settings.profile.memberSince": "Membre depuis",
  "settings.profile.save": "Enregistrer",
  "settings.profile.editPhoto": "Modifier la photo",
  "settings.security.title": "Sécurité du compte",
  "settings.security.description": "Gérez votre sécurité et vos accès",
  "settings.security.changePassword": "Changer le mot de passe",
  "settings.security.currentPassword": "Mot de passe actuel",
  "settings.security.newPassword": "Nouveau mot de passe",
  "settings.security.confirmPassword": "Confirmer le mot de passe",
  "settings.security.passwordStrength": "Force du mot de passe",
  "settings.security.weak": "Faible",
  "settings.security.medium": "Moyen",
  "settings.security.strong": "Fort",
  "settings.security.activeSessions": "Sessions actives",
  "settings.security.revoke": "Révoquer",
  "settings.security.twoFactor": "Authentification à deux facteurs",
  "settings.security.configure": "Configurer",
  "settings.security.enabled": "Activé",
  "settings.security.disabled": "Désactivé",
  "settings.appearance.title": "Apparence",
  "settings.appearance.description": "Personnalisez l'interface",
  "settings.appearance.theme": "Thème",
  "settings.appearance.themeLight": "Clair",
  "settings.appearance.themeDark": "Sombre",
  "settings.appearance.themeSystem": "Système",
  "settings.appearance.language": "Langue",
  "settings.appearance.density": "Densité",
  "settings.appearance.densityCompact": "Compacte",
  "settings.appearance.densityComfortable": "Confortable",
  "settings.appearance.densitySpacious": "Spacieuse",
  "settings.notifications.title": "Notifications",
  "settings.notifications.description": "Contrôlez comment vous recevez les alertes",
  "settings.notifications.critical": "Alertes critiques de trésorerie",
  "settings.notifications.criticalDesc": "Ne peut pas être désactivé",
  "settings.notifications.email": "Alertes e-mail",
  "settings.notifications.emailDesc": "Recevez les alertes importantes par e-mail",
  "settings.notifications.weekly": "Résumé hebdomadaire",
  "settings.notifications.weeklyDesc": "Rapport hebdomadaire par e-mail",
  "settings.notifications.push": "Notifications navigateur",
  "settings.notifications.pushDesc": "Notifications push dans le navigateur",
  "settings.notifications.sms": "Alertes SMS",
  "settings.notifications.smsDesc": "Recevez les alertes par SMS",
  "settings.notifications.phone": "Numéro de téléphone",
  "settings.notifications.test": "Tester les notifications",
  "settings.notifications.testSuccess": "Notification de test envoyée avec succès !",
  "settings.subscription.title": "Gestion de l'abonnement",
  "settings.subscription.description": "Votre abonnement et facturation",
  "settings.subscription.plan": "Plan actuel",
  "settings.subscription.renewal": "Renouvellement le",
  "settings.subscription.price": "/mois",
  "settings.subscription.usage": "Utilisation du mois",
  "settings.subscription.changePlan": "Changer de plan",
  "settings.subscription.manageBilling": "Gérer la facturation",
  "settings.subscription.invoices": "Factures",
  "settings.subscription.invoicesDate": "Date",
  "settings.subscription.invoicesAmount": "Montant",
  "settings.subscription.invoicesStatus": "Statut",
  "settings.subscription.invoicesPaid": "Payé",
  "settings.subscription.download": "Télécharger",
  "settings.plan.starter": "Starter",
  "settings.plan.pro": "Pro",
  "settings.plan.enterprise": "Entreprise",
  "settings.danger.title": "Zone de danger",
  "settings.danger.description": "Actions irréversibles",
  "settings.danger.export": "Exporter mes données",
  "settings.danger.deactivate": "Désactiver le compte",
  "settings.danger.delete": "Supprimer le compte",
  "settings.danger.exportSuccess": "Exportation en cours...",
  "settings.danger.deactivateConfirm": "DÉSACTIVER",
  "settings.danger.deleteConfirm": "SUPPRIMER",
  "settings.danger.deactivateWarning": "Êtes-vous sûr de vouloir désactiver votre compte ?",
  "settings.danger.deleteWarning": "Cette action est irréversible. Toutes vos données seront définitivement supprimées.",
  "settings.danger.lostData": "Ce qui sera perdu :",
  "settings.danger.lostData1": "Toutes vos transactions et rapports",
  "settings.danger.lostData2": "Votre historique de trésorerie",
  "settings.danger.lostData3": "Vos paramètres et préférences",
  "settings.twoFactor.title": "Configurer l'authentification à deux facteurs",
  "settings.twoFactor.description": "Scannez le QR code ou entrez le code manuellement",
  "settings.twoFactor.code": "Code de vérification",
  "settings.plan.title": "Changer de plan",
  "settings.plan.description": "Choisissez le plan qui vous convient le mieux",
  "settings.plan.monthly": "/mois",
  "settings.plan.feature1": "100 transactions",
  "settings.plan.feature2": "Rapports mensuels",
  "settings.plan.feature3": "Support par e-mail",
  "settings.plan.feature4": "500 transactions",
  "settings.plan.feature5": "Rapports hebdomadaires",
  "settings.plan.feature6": "Support prioritaire",
  "settings.plan.feature7": "Transactions illimitées",
  "settings.plan.feature8": "Rapports personnalisés",
  "settings.plan.feature9": "Support dédié",
};

// Helper to get consistent avatar color from name
const stringToColor = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = [
    "hsl(220 70% 50%)", "hsl(250 70% 50%)", "hsl(280 70% 50%)", "hsl(310 70% 50%)",
    "hsl(340 70% 50%)", "hsl(10 70% 50%)", "hsl(40 70% 50%)", "hsl(70 70% 50%)",
    "hsl(100 70% 50%)", "hsl(130 70% 50%)", "hsl(160 70% 50%)", "hsl(190 70% 50%)"
  ];
  return colors[Math.abs(hash) % colors.length];
};

// Helper to format date as "Mai 2024"
const formatMemberSince = (dateStr) => {
  const date = dateStr ? new Date(dateStr) : new Date("2024-05-01");
  return date.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
};

// Helper to calculate password strength
const getPasswordStrength = (password) => {
  let strength = 0;
  if (password.length >= 8) strength++;
  if (password.length >= 12) strength++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^a-zA-Z0-9]/.test(password)) strength++;

  if (strength <= 2) return { value: 20, label: LABELS["settings.security.weak"], color: "bg-red-500" };
  if (strength <= 3) return { value: 50, label: LABELS["settings.security.medium"], color: "bg-yellow-500" };
  return { value: 100, label: LABELS["settings.security.strong"], color: "bg-green-500" };
};

const sections = [
  { id: "profile", label: LABELS["settings.profile"], icon: User },
  { id: "security", label: LABELS["settings.security"], icon: ShieldCheck },
  { id: "appearance", label: LABELS["settings.appearance"], icon: Palette },
  { id: "notifications", label: LABELS["settings.notifications"], icon: Bell },
  { id: "subscription", label: LABELS["settings.subscription"], icon: CreditCard },
  { id: "danger", label: LABELS["settings.danger"], icon: Trash2 },
];

export default function SettingsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [activeSection, setActiveSection] = useState("profile");
  const [formData, setFormData] = useState({
    firstName: user?.first_name || "",
    lastName: user?.last_name || "",
    email: user?.email || "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showTestToast, setShowTestToast] = useState(false);
  const [showExportFeedback, setShowExportFeedback] = useState(false);
  const [passwords, setPasswords] = useState({ current: "", new: "", confirm: "" });
  const [showPassword, setShowPassword] = useState({ current: false, new: false, confirm: false });
  const [notificationPrefs, setNotificationPrefs] = useState({
    critical: true,
    email: true,
    weekly: false,
    push: false,
    sms: false,
  });
  const [smsPhone, setSmsPhone] = useState("");
  const [density, setDensity] = useState("comfortable");
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [openTwoFactorDialog, setOpenTwoFactorDialog] = useState(false);
  const [openPlanDialog, setOpenPlanDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("pro");
  const [openDeactivateDialog, setOpenDeactivateDialog] = useState(false);
  const [deactivateConfirmText, setDeactivateConfirmText] = useState("");
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const sectionRefs = useRef({});

  const safe = (key) => t(key) === key ? (LABELS[key] ?? key) : t(key);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleTestNotification = () => {
    setShowTestToast(true);
    setTimeout(() => setShowTestToast(false), 3000);
  };

  const handleExportData = () => {
    setShowExportFeedback(true);
    setTimeout(() => setShowExportFeedback(false), 3000);
  };

  const getInitials = () => {
    const initials = [
      (formData.firstName || user?.first_name || "")[0],
      (formData.lastName || user?.last_name || "")[0],
    ].filter(Boolean).join("").toUpperCase();
    return initials || "U";
  };

  const passwordStrength = getPasswordStrength(passwords.new);
  const canSubmitPassword = passwords.new === passwords.confirm && passwordStrength.value >= 50;

  const activeSessions = [
    { id: 1, device: "MacBook Pro", location: "Paris, France", lastSeen: "Il y a 5 minutes", current: true },
    { id: 2, device: "iPhone 15 Pro", location: "Lyon, France", lastSeen: "Il y a 2 jours", current: false },
    { id: 3, device: "Safari sur iPad", location: "Marseille, France", lastSeen: "Il y a 1 semaine", current: false },
  ];

  const invoices = [
    { id: 1, date: "01/06/2024", amount: "49,00 €", status: "payé" },
    { id: 2, date: "01/05/2024", amount: "49,00 €", status: "payé" },
    { id: 3, date: "01/04/2024", amount: "49,00 €", status: "payé" },
  ];

  const plans = [
    { id: "starter", name: safe("settings.plan.starter"), price: "19", features: [safe("settings.plan.feature1"), safe("settings.plan.feature2"), safe("settings.plan.feature3")] },
    { id: "pro", name: safe("settings.plan.pro"), price: "49", features: [safe("settings.plan.feature4"), safe("settings.plan.feature5"), safe("settings.plan.feature6")] },
    { id: "enterprise", name: safe("settings.plan.enterprise"), price: "149", features: [safe("settings.plan.feature7"), safe("settings.plan.feature8"), safe("settings.plan.feature9")] },
  ];

  const fullName = `${formData.firstName || user?.first_name || ""} ${formData.lastName || user?.last_name || ""}`.trim();

  return (
    <div className="flex flex-col lg:flex-row min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block w-56 border-r border-border h-screen sticky top-0 pt-8 px-4">
        <div className="space-y-2">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  activeSection === section.id
                    ? "bg-primary/10 text-primary font-semibold border-l-2 border-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {section.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Mobile Tabs */}
      <div className="lg:hidden p-4 border-b border-border">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-colors whitespace-nowrap ${
                  activeSection === section.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                <Icon className="h-4 w-4" />
                {section.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 p-4 lg:p-8">
        {showTestToast && (
          <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 z-50">
            <CheckCircle2 className="h-4 w-4" />
            {safe("settings.notifications.testSuccess")}
          </div>
        )}

        {/* Profile Section */}
        {activeSection === "profile" && (
          <div className="max-w-2xl mx-auto space-y-6">
            <Card className="rounded-2xl border border-border bg-card shadow-sm p-6">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-lg font-semibold">{safe("settings.profile.title")}</CardTitle>
                <CardDescription>{safe("settings.profile.description")}</CardDescription>
              </CardHeader>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-6">
                <div className="relative group">
                  <Avatar className="h-24 w-24">
                    <AvatarFallback
                      className="text-2xl font-semibold"
                      style={{ backgroundColor: stringToColor(fullName || "user") }}
                    >
                      {getInitials()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="absolute inset-0 bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="flex flex-col items-center text-white text-xs gap-1">
                      <Camera className="h-5 w-5" />
                      {safe("settings.profile.editPhoto")}
                    </div>
                  </div>
                </div>
              </div>
              <form onSubmit={handleSaveProfile} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">{safe("settings.profile.firstName")}</Label>
                    <Input
                      id="firstName"
                      name="firstName"
                      value={formData.firstName}
                      onChange={handleInputChange}
                      placeholder="Jean"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">{safe("settings.profile.lastName")}</Label>
                    <Input
                      id="lastName"
                      name="lastName"
                      value={formData.lastName}
                      onChange={handleInputChange}
                      placeholder="Dupont"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">{safe("settings.profile.email")}</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="jean.dupont@exemple.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memberSince">{safe("settings.profile.memberSince")}</Label>
                  <Input
                    id="memberSince"
                    value={formatMemberSince(user?.created_at)}
                    disabled
                    className="bg-muted"
                  />
                </div>
                <div className="pt-2 flex items-center gap-3">
                  <Button type="submit" disabled={saving}>
                    {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
                    {safe("settings.profile.save")}
                  </Button>
                  {saved && (
                    <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                      <CheckCircle2 className="h-4 w-4" />
                      Enregistré
                    </div>
                  )}
                </div>
              </form>
            </Card>
          </div>
        )}

        {/* Security Section */}
        {activeSection === "security" && (
          <div className="max-w-2xl mx-auto space-y-6">
            <Card className="rounded-2xl border border-border bg-card shadow-sm p-6">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-lg font-semibold">{safe("settings.security.title")}</CardTitle>
                <CardDescription>{safe("settings.security.description")}</CardDescription>
              </CardHeader>

              {/* Change Password */}
              <div className="space-y-4">
                <h4 className="font-medium">{safe("settings.security.changePassword")}</h4>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="currentPassword">{safe("settings.security.currentPassword")}</Label>
                    <div className="relative">
                      <Input
                        id="currentPassword"
                        type={showPassword.current ? "text" : "password"}
                        value={passwords.current}
                        onChange={(e) => setPasswords(prev => ({ ...prev, current: e.target.value }))}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(prev => ({ ...prev, current: !prev.current }))}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showPassword.current ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="newPassword">{safe("settings.security.newPassword")}</Label>
                    <div className="relative">
                      <Input
                        id="newPassword"
                        type={showPassword.new ? "text" : "password"}
                        value={passwords.new}
                        onChange={(e) => setPasswords(prev => ({ ...prev, new: e.target.value }))}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(prev => ({ ...prev, new: !prev.new }))}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showPassword.new ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">{safe("settings.security.confirmPassword")}</Label>
                    <div className="relative">
                      <Input
                        id="confirmPassword"
                        type={showPassword.confirm ? "text" : "password"}
                        value={passwords.confirm}
                        onChange={(e) => setPasswords(prev => ({ ...prev, confirm: e.target.value }))}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(prev => ({ ...prev, confirm: !prev.confirm }))}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showPassword.confirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  {passwords.new && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <Label className="text-xs">{safe("settings.security.passwordStrength")}</Label>
                        <span className={`text-xs ${
                          passwordStrength.value === 100 ? "text-green-600" :
                          passwordStrength.value >= 50 ? "text-yellow-600" :
                          "text-red-600"
                        }`}>{passwordStrength.label}</span>
                      </div>
                      <Progress value={passwordStrength.value} className="h-1" />
                    </div>
                  )}
                  <Button type="button" disabled={!canSubmitPassword} onClick={() => {
                    setPasswords({ current: "", new: "", confirm: "" });
                  }}>
                    {safe("settings.profile.save")}
                  </Button>
                </div>
              </div>

              <Separator className="my-6" />

              {/* Active Sessions */}
              <div className="space-y-4">
                <h4 className="font-medium">{safe("settings.security.activeSessions")}</h4>
                <div className="space-y-3">
                  {activeSessions.map((session) => (
                    <div key={session.id} className="flex items-center justify-between p-3 border border-border rounded-lg">
                      <div className="flex items-start gap-3">
                        <Smartphone className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{session.device}</span>
                            {session.current && <Badge variant="default">Actuel</Badge>}
                          </div>
                          <p className="text-sm text-muted-foreground">{session.location}</p>
                          <p className="text-xs text-muted-foreground">{session.lastSeen}</p>
                        </div>
                      </div>
                      {!session.current && (
                        <Button variant="outline" size="sm">{safe("settings.security.revoke")}</Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <Separator className="my-6" />

              {/* Two Factor */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">{safe("settings.security.twoFactor")}</h4>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={twoFactorEnabled ? "default" : "outline"}>
                      {twoFactorEnabled ? safe("settings.security.enabled") : safe("settings.security.disabled")}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Switch
                    checked={twoFactorEnabled}
                    onCheckedChange={setTwoFactorEnabled}
                  />
                  {!twoFactorEnabled && (
                    <Button variant="outline" onClick={() => setOpenTwoFactorDialog(true)}>
                      {safe("settings.security.configure")}
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Appearance Section */}
        {activeSection === "appearance" && (
          <div className="max-w-2xl mx-auto space-y-6">
            <Card className="rounded-2xl border border-border bg-card shadow-sm p-6">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-lg font-semibold">{safe("settings.appearance.title")}</CardTitle>
                <CardDescription>{safe("settings.appearance.description")}</CardDescription>
              </CardHeader>

              {/* Theme */}
              <div className="space-y-4 mb-6">
                <h4 className="font-medium">{safe("settings.appearance.theme")}</h4>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: "light", icon: Sun, label: safe("settings.appearance.themeLight") },
                    { id: "dark", icon: Moon, label: safe("settings.appearance.themeDark") },
                    { id: "system", icon: Monitor, label: safe("settings.appearance.themeSystem") },
                  ].map((t) => {
                    const Icon = t.icon;
                    return (
                      <button
                        key={t.id}
                        onClick={() => setTheme(t.id)}
                        className={`p-4 rounded-lg border-2 transition-all text-center ${
                          theme === t.id
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        <Icon className="h-6 w-6 mx-auto mb-2 text-muted-foreground" />
                        <span className="text-sm">{t.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <Separator className="my-6" />

              {/* Language */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h4 className="font-medium">{safe("settings.appearance.language")}</h4>
                </div>
                <LanguageSelector />
              </div>

              <Separator className="my-6" />

              {/* Density */}
              <div className="space-y-4">
                <h4 className="font-medium">{safe("settings.appearance.density")}</h4>
                <div className="inline-flex rounded-md border border-input bg-background">
                  {[
                    { id: "compact", label: safe("settings.appearance.densityCompact") },
                    { id: "comfortable", label: safe("settings.appearance.densityComfortable") },
                    { id: "spacious", label: safe("settings.appearance.densitySpacious") },
                  ].map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setDensity(d.id)}
                      className={`px-4 py-2 text-sm transition-colors ${
                        density === d.id
                          ? "bg-primary text-primary-foreground rounded-md"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Notifications Section */}
        {activeSection === "notifications" && (
          <div className="max-w-2xl mx-auto space-y-6">
            <Card className="rounded-2xl border border-border bg-card shadow-sm p-6">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-lg font-semibold">{safe("settings.notifications.title")}</CardTitle>
                <CardDescription>{safe("settings.notifications.description")}</CardDescription>
              </CardHeader>

              <div className="space-y-4">
                {/* Critical Alerts */}
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
                    <div>
                      <h4 className="font-medium">{safe("settings.notifications.critical")}</h4>
                      <p className="text-sm text-muted-foreground">{safe("settings.notifications.criticalDesc")}</p>
                    </div>
                  </div>
                  <Switch checked={true} disabled />
                </div>

                <Separator />

                {/* Email */}
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-start gap-3">
                    <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h4 className="font-medium">{safe("settings.notifications.email")}</h4>
                      <p className="text-sm text-muted-foreground">{safe("settings.notifications.emailDesc")}</p>
                    </div>
                  </div>
                  <Switch
                    checked={notificationPrefs.email}
                    onCheckedChange={(checked) => setNotificationPrefs(prev => ({ ...prev, email: checked }))}
                  />
                </div>

                <Separator />

                {/* Weekly Report */}
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-start gap-3">
                    <MessageSquare className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h4 className="font-medium">{safe("settings.notifications.weekly")}</h4>
                      <p className="text-sm text-muted-foreground">{safe("settings.notifications.weeklyDesc")}</p>
                    </div>
                  </div>
                  <Switch
                    checked={notificationPrefs.weekly}
                    onCheckedChange={(checked) => setNotificationPrefs(prev => ({ ...prev, weekly: checked }))}
                  />
                </div>

                <Separator />

                {/* Push Notifications */}
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-start gap-3">
                    <Bell className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h4 className="font-medium">{safe("settings.notifications.push")}</h4>
                      <p className="text-sm text-muted-foreground">{safe("settings.notifications.pushDesc")}</p>
                    </div>
                  </div>
                  <Switch
                    checked={notificationPrefs.push}
                    onCheckedChange={(checked) => setNotificationPrefs(prev => ({ ...prev, push: checked }))}
                  />
                </div>

                <Separator />

                {/* SMS */}
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-start gap-3">
                    <SmartphoneIcon className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h4 className="font-medium">{safe("settings.notifications.sms")}</h4>
                      <p className="text-sm text-muted-foreground">{safe("settings.notifications.smsDesc")}</p>
                    </div>
                  </div>
                  <Switch
                    checked={notificationPrefs.sms}
                    onCheckedChange={(checked) => setNotificationPrefs(prev => ({ ...prev, sms: checked }))}
                  />
                </div>
                {notificationPrefs.sms && (
                  <div className="pl-8">
                    <Label htmlFor="smsPhone">{safe("settings.notifications.phone")}</Label>
                    <Input
                      id="smsPhone"
                      value={smsPhone}
                      onChange={(e) => setSmsPhone(e.target.value)}
                      placeholder="+33 6 12 34 56 78"
                    />
                  </div>
                )}
              </div>

              <div className="mt-8">
                <Button onClick={handleTestNotification}>
                  {safe("settings.notifications.test")}
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* Subscription Section */}
        {activeSection === "subscription" && (
          <div className="max-w-3xl mx-auto space-y-6">
            <Card className="rounded-2xl border border-border bg-card shadow-sm p-6">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-lg font-semibold">{safe("settings.subscription.title")}</CardTitle>
                <CardDescription>{safe("settings.subscription.description")}</CardDescription>
              </CardHeader>

              {/* Current Plan */}
              <div className="flex items-start justify-between mb-6 p-4 bg-muted/50 rounded-lg border border-border">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold">{safe("settings.plan.pro")}</h4>
                    <Badge variant="default">Pro</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{safe("settings.subscription.renewal")} 01/07/2024</p>
                  <p className="text-2xl font-bold mt-2">49 € <span className="text-sm font-normal text-muted-foreground">{safe("settings.subscription.price")}</span></p>
                </div>
              </div>

              {/* Usage */}
              <div className="space-y-2 mb-6">
                <div className="flex justify-between text-sm">
                  <span>{safe("settings.subscription.usage")}</span>
                  <span className="font-medium">12 / 50 transactions</span>
                </div>
                <Progress value={24} className="h-2" />
              </div>

              {/* Features */}
              <ul className="space-y-2 mb-6">
                {plans.find(p => p.id === "pro")?.features.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    {feature}
                  </li>
                ))}
              </ul>

              <div className="flex flex-wrap gap-3 mb-8">
                <Button onClick={() => setOpenPlanDialog(true)}>
                  {safe("settings.subscription.changePlan")}
                </Button>
                <Button variant="outline" asChild>
                  <a href="#">{safe("settings.subscription.manageBilling")}</a>
                </Button>
              </div>

              <Separator />

              {/* Invoices */}
              <div className="mt-6">
                <h4 className="font-medium mb-4">{safe("settings.subscription.invoices")}</h4>
                <div className="space-y-3">
                  {invoices.map((invoice) => (
                    <div key={invoice.id} className="flex items-center justify-between p-3 border border-border rounded-lg">
                      <div>
                        <p className="font-medium">{invoice.date}</p>
                        <p className="text-sm text-muted-foreground">{invoice.amount}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="outline">{invoice.status}</Badge>
                        <Button variant="ghost" size="icon-sm">
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Danger Zone */}
        {activeSection === "danger" && (
          <div className="max-w-2xl mx-auto space-y-6">
            <Card className="rounded-2xl border border-destructive/30 bg-destructive/5 shadow-sm p-6">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-lg font-semibold text-destructive">{safe("settings.danger.title")}</CardTitle>
                <CardDescription>{safe("settings.danger.description")}</CardDescription>
              </CardHeader>

              <div className="space-y-4">
                {/* Export Data */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{safe("settings.danger.export")}</h4>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleExportData}
                  >
                    {showExportFeedback ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        {safe("settings.danger.exportSuccess")}
                      </>
                    ) : (
                      safe("settings.danger.export")
                    )}
                  </Button>
                </div>

                <Separator />

                {/* Deactivate Account */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{safe("settings.danger.deactivate")}</h4>
                  </div>
                  <AlertDialog open={openDeactivateDialog} onOpenChange={setOpenDeactivateDialog}>
                    <AlertDialogTrigger asChild>
                      <Button variant="outline" className="border-destructive text-destructive hover:bg-destructive/10 hover:text-destructive">
                        {safe("settings.danger.deactivate")}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>{safe("settings.danger.deactivate")}</AlertDialogTitle>
                        <AlertDialogDescription>{safe("settings.danger.deactivateWarning")}</AlertDialogDescription>
                      </AlertDialogHeader>
                      <div className="space-y-2 my-4">
                        <Label>Tapez "{safe("settings.danger.deactivateConfirm")}" pour confirmer</Label>
                        <Input
                          value={deactivateConfirmText}
                          onChange={(e) => setDeactivateConfirmText(e.target.value)}
                          placeholder={safe("settings.danger.deactivateConfirm")}
                        />
                      </div>
                      <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setDeactivateConfirmText("")}>
                          Annuler
                        </AlertDialogCancel>
                        <AlertDialogAction
                          disabled={deactivateConfirmText !== safe("settings.danger.deactivateConfirm")}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          {safe("settings.danger.deactivate")}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>

                <Separator />

                {/* Delete Account */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{safe("settings.danger.delete")}</h4>
                  </div>
                  <AlertDialog open={openDeleteDialog} onOpenChange={setOpenDeleteDialog}>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive">
                        {safe("settings.danger.delete")}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle className="text-destructive">{safe("settings.danger.delete")}</AlertDialogTitle>
                        <AlertDialogDescription>{safe("settings.danger.deleteWarning")}</AlertDialogDescription>
                      </AlertDialogHeader>
                      <div className="space-y-4 my-4">
                        <div>
                          <p className="text-sm font-medium mb-2">{safe("settings.danger.lostData")}</p>
                          <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                            <li>{safe("settings.danger.lostData1")}</li>
                            <li>{safe("settings.danger.lostData2")}</li>
                            <li>{safe("settings.danger.lostData3")}</li>
                          </ul>
                        </div>
                        <div className="space-y-2">
                          <Label>Tapez "{safe("settings.danger.deleteConfirm")}" pour confirmer</Label>
                          <Input
                            value={deleteConfirmText}
                            onChange={(e) => setDeleteConfirmText(e.target.value)}
                            placeholder={safe("settings.danger.deleteConfirm")}
                          />
                        </div>
                      </div>
                      <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setDeleteConfirmText("")}>
                          Annuler
                        </AlertDialogCancel>
                        <AlertDialogAction
                          disabled={deleteConfirmText !== safe("settings.danger.deleteConfirm")}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          {safe("settings.danger.delete")}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            </Card>
          </div>
        )}
      </main>

      {/* Two Factor Dialog */}
      <Dialog open={openTwoFactorDialog} onOpenChange={setOpenTwoFactorDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{safe("settings.twoFactor.title")}</DialogTitle>
            <DialogDescription>{safe("settings.twoFactor.description")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 my-2">
            <div className="border border-border rounded-lg p-8 flex items-center justify-center bg-muted/30">
              <div className="text-center">
                <QrCode className="h-32 w-32 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">QR Code (exemple)</p>
              </div>
            </div>
            <div className="space-y-2">
              <Label>{safe("settings.twoFactor.code")}</Label>
              <Input maxLength={6} placeholder="000000" />
            </div>
          </div>
          <DialogFooter>
            <DialogClose onClick={() => setOpenTwoFactorDialog(false)}>Annuler</DialogClose>
            <Button onClick={() => { setOpenTwoFactorDialog(false); setTwoFactorEnabled(true); }}>
              Activer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Plan Dialog */}
      <Dialog open={openPlanDialog} onOpenChange={setOpenPlanDialog}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{safe("settings.plan.title")}</DialogTitle>
            <DialogDescription>{safe("settings.plan.description")}</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-4">
            {plans.map((plan) => (
              <div
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  selectedPlan === plan.id
                    ? "border-primary bg-primary/5 ring-2 ring-primary"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="mb-2">
                  <h4 className="font-semibold text-lg">{plan.name}</h4>
                  <p className="text-2xl font-bold">{plan.price} € <span className="text-sm font-normal text-muted-foreground">{safe("settings.plan.monthly")}</span></p>
                </div>
                <Separator className="my-4" />
                <ul className="space-y-2">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <DialogFooter>
            <DialogClose onClick={() => setOpenPlanDialog(false)}>Annuler</DialogClose>
            <Button>Changer de plan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
