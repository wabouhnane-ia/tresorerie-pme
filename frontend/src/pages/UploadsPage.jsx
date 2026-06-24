import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from "../components/ui/sheet";
import { Skeleton } from "../components/ui/skeleton";
import { FileText, Calendar, Database, Clock } from "lucide-react";

function formatDate(dateStr, options = {}) {
  if (!dateStr) return "—";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "—";
    if (options.dateStyle) {
      return date.toLocaleDateString("fr-FR", options);
    } else {
      return date.toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
    }
  } catch (e) {
    return "—";
  }
}

function formatDateRange(dateRange) {
  if (!dateRange || !dateRange.min_date || !dateRange.max_date) return "—";
  const format = (dateStr) => {
    try {
      return formatDate(dateStr);
    } catch {
      return "—";
    }
  };
  return `${format(dateRange.min_date)} → ${format(dateRange.max_date)}`;
}

function getStatusBadge(upload) {
  if (upload.duplicate_detected || upload.processing_status === "duplicate_data") {
    return <Badge variant="secondary">Doublon</Badge>;
  } else if (upload.status === "failed" || upload.processing_status === "failed") {
    return <Badge variant="destructive">Erreur</Badge>;
  } else if (upload.processing_status === "processing") {
    return <Badge variant="outline">Analyse…</Badge>;
  } else if (upload.processing_status === "completed_with_errors") {
    return <Badge variant="outline">Complété (erreurs)</Badge>;
  } else if (upload.total_company_uploads === 1) {
    return <Badge variant="default">Historique créé</Badge>;
  } else {
    return <Badge variant="default">Fusionné</Badge>;
  }
}

function getUploadType(upload) {
  if (upload.total_company_uploads === 1) {
    return "Historique initial";
  }
  if (upload.classification === "DUPLICATE_UPLOAD") {
    return "Duplicata";
  }
  if (upload.classification === "PARTIAL_OVERLAP") {
    return "Mise à jour partielle";
  }
  return "Mise à jour mensuelle";
}

function formatNumber(num) {
  if (num == null) return "—";
  return num.toString();
}

function getQualityBadge(dataMaturity) {
  const variantMap = {
    "EXCELLENT": "default",
    "BON": "default",
    "MOYEN": "secondary",
    "FAIBLE": "outline",
  };
  return <Badge variant={variantMap[dataMaturity] || "outline"}>{dataMaturity || "—"}</Badge>;
}

function getBusinessImpact(upload, treasuryProfile) {
  const parts = [];
  if (upload.records_inserted > 0) {
    parts.push(`Historique enrichi avec ${upload.records_inserted} nouvelles observations.`);
  }
  if (treasuryProfile?.profile?.historical_months) {
    parts.push(`La mémoire de trésorerie couvre désormais ${Math.round(treasuryProfile.profile.historical_months)} mois.`);
  }
  if (treasuryProfile?.profile?.forecasting_enabled) {
    parts.push("Prévisions automatiquement mises à jour.");
  }
  return parts.length > 0 ? parts.join(" ") : "Import complété.";
}

export default function UploadsPage() {
  const navigate = useNavigate();
  const [uploads, setUploads] = useState([]);
  const [treasuryProfile, setTreasuryProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedUpload, setSelectedUpload] = useState(null);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [uploadsRes, profileRes] = await Promise.all([
        API.get("/upload/list"),
        API.get("/upload/treasury-profile").catch(() => null),
      ]);
      setUploads(uploadsRes.data);
      if (profileRes?.data) {
        setTreasuryProfile(profileRes.data);
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  const closeSheet = () => {
    setSelectedUpload(null);
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <div className="space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-96" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <Skeleton className="h-4 w-32 mb-2" />
                  <Skeleton className="h-8 w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="h-12 w-12 rounded-full" />
                    <div className="space-y-2 flex-1">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Fichiers importés</h1>
        <p className="text-muted-foreground">Historique des uploads et mémoire de trésorerie</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Historique disponible</p>
                <p className="text-2xl font-bold">
                  {treasuryProfile?.profile?.historical_months ? Math.round(treasuryProfile.profile.historical_months) : 0} mois
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Fichiers importés</p>
                <p className="text-2xl font-bold">{uploads.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Observations</p>
                <p className="text-2xl font-bold">
                  {treasuryProfile?.profile?.historical_months ? Math.round(treasuryProfile.profile.historical_months * 30) : 0} jours
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Dernière mise à jour</p>
                <p className="text-2xl font-bold">
                  {uploads[0]?.created_at
                    ? formatDate(uploads[0].created_at)
                    : "—"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {uploads.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center">
            <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-xl font-semibold text-foreground mb-2">Aucun fichier importé</h2>
            <p className="text-muted-foreground mb-6">Importez vos données de trésorerie pour commencer.</p>
            <Button onClick={() => navigate("/")}>
              Aller au tableau de bord
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fichier</TableHead>
                  <TableHead>Date import</TableHead>
                  <TableHead>Période détectée</TableHead>
                  <TableHead>Lignes importées</TableHead>
                  <TableHead>Type d'upload</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Détails</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {uploads.map((upload) => (
                  <TableRow key={upload._id} onClick={() => setSelectedUpload(upload)} className="cursor-pointer">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex-shrink-0 w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                          <FileText className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <div className="font-medium text-foreground">{upload.original_filename}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {upload.created_at
                        ? formatDate(upload.created_at, {
                            dateStyle: "medium",
                            timeStyle: "short",
                          })
                        : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateRange(upload.date_range)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {upload.records_inserted > 0
                        ? `${upload.records_inserted} lignes`
                        : upload.rows_processed != null
                        ? `${upload.rows_processed} lignes`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {getUploadType(upload)}
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(upload)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost">
                        Voir détails
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Sheet open={!!selectedUpload} onOpenChange={closeSheet}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Détails de l'import</SheetTitle>
            <SheetClose />
          </SheetHeader>

          {selectedUpload && (
            <div className="mt-6 space-y-6">
              {/* SECTION 1: File Info */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Informations du fichier</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Nom:</span>
                    <span className="font-medium truncate max-w-[60%]">{selectedUpload.original_filename}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Date d'import:</span>
                    <span className="font-medium">
                      {selectedUpload.created_at
                        ? formatDate(selectedUpload.created_at, {
                            dateStyle: "medium",
                            timeStyle: "short",
                          })
                        : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Type d'upload:</span>
                    <span className="font-medium">{getUploadType(selectedUpload)}</span>
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">Statut:</span>
                    {getStatusBadge(selectedUpload)}
                  </div>
                </CardContent>
              </Card>

              {/* SECTION 2: Processing */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Traitement</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Période:</span>
                    <span className="font-medium">{formatDateRange(selectedUpload.date_range)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Lignes traitées:</span>
                    <span className="font-medium">{formatNumber(selectedUpload.rows_processed)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Lignes insérées:</span>
                    <span className="font-medium">{formatNumber(selectedUpload.records_inserted)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Lignes mises à jour:</span>
                    <span className="font-medium">{formatNumber(selectedUpload.records_updated)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Doublons ignorés:</span>
                    <span className="font-medium">{formatNumber(selectedUpload.records_skipped)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* SECTION 3: Treasury Memory */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Mémoire de trésorerie</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Historique disponible:</span>
                    <span className="font-medium">
                      {treasuryProfile?.profile?.historical_months ? Math.round(treasuryProfile.profile.historical_months) : "—"} mois
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Observations totales:</span>
                    <span className="font-medium">
                      {treasuryProfile?.profile?.historical_months ? `${Math.round(treasuryProfile.profile.historical_months * 30)} jours` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">Qualité des données:</span>
                    {getQualityBadge(selectedUpload.data_maturity)}
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">Prévisions activées:</span>
                    <Badge variant={treasuryProfile?.profile?.forecasting_enabled ? "default" : "outline"}>
                      {treasuryProfile?.profile?.forecasting_enabled ? "Oui" : "Non"}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Dernière date connue:</span>
                    <span className="font-medium">—</span>
                  </div>
                </CardContent>
              </Card>

              {/* SECTION 4: Business Impact */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Impact métier</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-foreground">{getBusinessImpact(selectedUpload, treasuryProfile)}</p>
                </CardContent>
              </Card>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
