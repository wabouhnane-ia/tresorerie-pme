import { useState } from "react";
import API from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Separator } from "../components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Skeleton } from "../components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "../components/ui/alert";
import { FileText, TrendingUp, AlertTriangle, Zap, Download, CheckCircle2, Globe } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger, SheetFooter, SheetClose } from "../components/ui/sheet";
import { Select } from "../components/ui/select";

const reportTypes = [
  {
    id: "executive-pdf",
    title: "Rapport Exécutif PDF",
    description: "Synthèse stratégique de la situation financière.",
    icon: FileText,
    color: "default",
  },
  {
    id: "forecast-report",
    title: "Forecast Report",
    description: "Prévisions de trésorerie 30/90 jours.",
    icon: TrendingUp,
    color: "secondary",
  },
  {
    id: "risk-report",
    title: "Risk Report",
    description: "Analyse des risques financiers.",
    icon: AlertTriangle,
    color: "outline",
  },
  {
    id: "treasury-summary",
    title: "Treasury Summary",
    description: "Résumé mensuel de la trésorerie.",
    icon: Zap,
    color: "default",
  },
];

const mockReportHistory = [
  {
    id: 1,
    date: new Date(Date.now() - 86400000),
    type: "Rapport Exécutif PDF",
    period: "01/05/2026 - 31/05/2026",
    status: "completed",
    size: "2.4 MB",
  },
  {
    id: 2,
    date: new Date(Date.now() - 172800000),
    type: "Forecast Report",
    period: "01/06/2026 - 30/06/2026",
    status: "completed",
    size: "1.1 MB",
  },
  {
    id: 3,
    date: new Date(Date.now() - 259200000),
    type: "Risk Report",
    period: "01/05/2026 - 15/05/2026",
    status: "completed",
    size: "850 KB",
  },
];

const languageOptions = [
  { value: "fr", label: "Français", flag: "🇫🇷" },
  { value: "en", label: "English", flag: "🇬🇧" },
  { value: "ar", label: "العربية", flag: "🇲🇦" },
];

export default function ReportsPage() {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState("fr");
  const [showLanguageSheetOpen, setShowLanguageSheetOpen] = useState(false);

  const handleGenerateReport = async (language) => {
    setShowLanguageSheetOpen(false);
    setGenerating(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await API.get("/dashboard/report", {
        params: { language },
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      const prefix = { fr: "rapport-tresorerie-executif", en: "executive-treasury-report", ar: "report" }[language] || "rapport-tresorerie-executif";
      link.setAttribute(
        "download",
        `${prefix}-${new Date().toISOString().split("T")[0]}.pdf`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to generate report:", err);
      setError("Échec de la génération du rapport. Veuillez réessayer.");
    } finally {
      setGenerating(false);
    }
  };

  const getStatusBadge = (status) => {
    const configs = {
      completed: { variant: "default", label: "Prêt" },
      generating: { variant: "secondary", label: "En cours" },
      error: { variant: "destructive", label: "Erreur" },
    };
    const config = configs[status] || configs.completed;
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleDateString("fr-FR");
  };

  return (
    <div className="max-w-6xl mx-auto py-8">
      {/* Executive Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Rapport Exécutif</h1>
        <p className="text-muted-foreground">Rapport de conseil - santé financière, risques, décisions et plan d'action</p>
        {!loading && (
          <div className="mt-4 flex flex-wrap gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">Dernier rapport:</span>
              <span>{mockReportHistory.length > 0 ? formatDate(mockReportHistory[0].date) : "—"}</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">Statut:</span>
              {mockReportHistory.length > 0 ? getStatusBadge(mockReportHistory[0].status) : "—"}
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">Période analysée:</span>
              <span>{mockReportHistory.length > 0 ? mockReportHistory[0].period : "—"}</span>
            </div>
          </div>
        )}
      </div>

      {/* Success/Error Alerts */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Erreur</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="mb-6">
          <Download className="h-4 w-4" />
          <AlertTitle>Succès</AlertTitle>
          <AlertDescription>Le rapport a été téléchargé avec succès.</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Executive Report Card + Library */}
        <div className="lg:col-span-2 space-y-6">
          {/* Executive Report Card */}
          <Card>
            <CardHeader>
              <CardTitle>Treasury Intelligence - Version Exécutive</CardTitle>
              <CardDescription>Rapport PDF de niveau conseil : synthèse exécutive, santé financière, résilience, horizon de trésorerie, alertes, risques, décisions et plan d'action — prêt pour CEO, banque ou investisseur.</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-4">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="p-4 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">Dernière génération</p>
                      <p className="font-medium">
                        {mockReportHistory.length > 0 ? formatDate(mockReportHistory[0].date) : "—"}
                      </p>
                    </div>
                    <div className="p-4 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">Taille du rapport</p>
                      <p className="font-medium">
                        {mockReportHistory.length > 0 ? mockReportHistory[0].size : "—"}
                      </p>
                    </div>
                    <div className="p-4 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">Période</p>
                      <p className="font-medium">
                        {mockReportHistory.length > 0 ? mockReportHistory[0].period : "—"}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <Sheet open={showLanguageSheetOpen} onOpenChange={setShowLanguageSheetOpen}>
                      <SheetTrigger render={<Button disabled={generating}>
                        {generating ? (
                          <>
                            <Skeleton className="h-4 w-4 rounded-full mr-2 animate-pulse" />
                            Génération en cours…
                          </>
                        ) : (
                          <>
                            <Globe className="h-4 w-4 mr-2" />
                            Télécharger le rapport
                          </>
                        )}
                      </Button>} />
                      <SheetContent className="w-full max-w-md">
                        <SheetHeader>
                          <SheetTitle>Choisissez la langue du rapport</SheetTitle>
                          <SheetDescription>Sélectionnez la langue dans laquelle vous souhaitez générer le rapport exécutif.</SheetDescription>
                        </SheetHeader>
                        <div className="py-6 space-y-4">
                          {languageOptions.map((lang) => (
                            <button
                              key={lang.value}
                              onClick={() => setSelectedLanguage(lang.value)}
                              className={`w-full flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
                                selectedLanguage === lang.value ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-2xl">{lang.flag}</span>
                                <span className="font-medium">{lang.label}</span>
                              </div>
                              {selectedLanguage === lang.value && (
                                <CheckCircle2 className="h-5 w-5 text-primary" />
                              )}
                            </button>
                          ))}
                        </div>
                        <SheetFooter>
                          <Button variant="outline" onClick={() => setShowLanguageSheetOpen(false)}>Annuler</Button>
                          <Button onClick={() => handleGenerateReport(selectedLanguage)} disabled={generating}>
                            {generating ? "Génération en cours…" : "Générer et télécharger"}
                          </Button>
                        </SheetFooter>
                      </SheetContent>
                    </Sheet>

                    <Button variant="outline" disabled={mockReportHistory.length === 0}>
                      <Download className="h-4 w-4 mr-2" />
                      Télécharger
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Report Library */}
          <Card>
            <CardHeader>
              <CardTitle>Bibliothèque de rapports</CardTitle>
              <CardDescription>Tous les rapports disponibles.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {reportTypes.map((report) => (
                  <Card key={report.id} className="border border-muted-foreground/20">
                    <CardContent className="pt-6">
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                          <report.icon className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-medium text-foreground">{report.title}</h3>
                          <p className="text-sm text-muted-foreground">{report.description}</p>
                          <div className="mt-4">
                            <Badge variant={report.color}>Disponible</Badge>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Preview + History */}
        <div className="space-y-6">
          {/* Latest Report Preview */}
          <Card>
            <CardHeader>
              <CardTitle>Résumé du dernier rapport</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-4">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Separator className="my-4" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ) : mockReportHistory.length > 0 ? (
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-sm text-muted-foreground">Synthèse Exécutive</h4>
                    <p className="text-foreground mt-1 text-sm">
                      La trésorerie est stable avec un solde positif, mais une tendance à la baisse
                      requiert une attention particulière.
                    </p>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="font-medium text-sm text-muted-foreground">Principaux Risques</h4>
                    <ul className="list-disc list-inside mt-1 text-sm text-foreground">
                      <li>Risque de liquidité à 60 jours</li>
                      <li>Flux sortants trop élevés</li>
                    </ul>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="font-medium text-sm text-muted-foreground">Décision Recommandée</h4>
                    <p className="text-foreground mt-1 text-sm">
                      Optimiser les paiements et renforcer les rentrées de fonds.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Aucun rapport disponible</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Report History */}
          <Card>
            <CardHeader>
              <CardTitle>Historique des rapports</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-10 w-10 rounded-full" />
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : mockReportHistory.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockReportHistory.map((report) => (
                      <TableRow key={report.id}>
                        <TableCell className="text-sm">{formatDate(report.date)}</TableCell>
                        <TableCell className="text-sm">{report.type}</TableCell>
                        <TableCell>{getStatusBadge(report.status)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm">
                            <Download className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="p-12 text-center text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Aucun rapport disponible</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
