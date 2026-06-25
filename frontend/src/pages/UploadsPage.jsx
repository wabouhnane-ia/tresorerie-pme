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
import { useTranslation } from "@/i18n/LanguageProvider";

export default function UploadsPage() {
  const navigate = useNavigate();
  const [uploads, setUploads] = useState([]);
  const [treasuryProfile, setTreasuryProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedUpload, setSelectedUpload] = useState(null);
  const { t, formatDate } = useTranslation();

  function getStatusBadge(upload) {
    if (upload.duplicate_detected || upload.processing_status === "duplicate_data") {
      return <Badge variant="secondary">{t("upload.errors.duplicate")}</Badge>;
    } else if (upload.status === "failed" || upload.processing_status === "failed") {
      return <Badge variant="destructive">{t("upload.errors.failed")}</Badge>;
    } else if (upload.processing_status === "processing") {
      return <Badge variant="outline">{t("upload.processing")}</Badge>;
    } else if (upload.processing_status === "completed_with_errors") {
      return <Badge variant="outline">{t("upload.errors.failed")}</Badge>;
    } else if (upload.total_company_uploads === 1) {
      return <Badge variant="default">{t("upload.historyUpdated")}</Badge>;
    } else {
      return <Badge variant="default">{t("upload.intelligenceUpdated")}</Badge>;
    }
  }

  function getUploadType(upload) {
    if (upload.total_company_uploads === 1) {
      return t("uploadsPage.typeInitialHistory");
    }
    if (upload.classification === "DUPLICATE_UPLOAD") {
      return t("upload.errors.duplicate");
    }
    if (upload.classification === "PARTIAL_OVERLAP") {
      return t("uploadsPage.typePartialUpdate");
    }
    return t("uploadsPage.typeMonthlyUpdate");
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
      parts.push(t("uploadsPage.historyEnriched", { count: upload.records_inserted }));
    }
    if (treasuryProfile?.profile?.historical_months) {
      parts.push(t("uploadsPage.treasuryMemoryNowCovers", { count: Math.round(treasuryProfile.profile.historical_months) }));
    }
    if (treasuryProfile?.profile?.forecasting_enabled) {
      parts.push(t("uploadsPage.forecastsAutomaticallyUpdated"));
    }
    return parts.length > 0 ? parts.join(" ") : t("upload.success");
  }

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
        <h1 className="text-3xl font-bold text-foreground mb-2">{t("uploadsPage.title")}</h1>
        <p className="text-muted-foreground">{t("uploadsPage.subtitle")}</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">{t("treasuryMemory.historyAvailable")}</p>
                <p className="text-2xl font-bold">
                  {treasuryProfile?.profile?.historical_months ? `${Math.round(treasuryProfile.profile.historical_months)} ${t("common.months")}` : `0 ${t("common.months")}`}
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
                <p className="text-sm text-muted-foreground">{t("uploadsPage.colFile")}</p>
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
                <p className="text-sm text-muted-foreground">{t("treasuryMemory.observations")}</p>
                <p className="text-2xl font-bold">
                  {treasuryProfile?.profile?.historical_months ? `${Math.round(treasuryProfile.profile.historical_months * 30)} ${t("common.days")}` : `0 ${t("common.days")}`}
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
                <p className="text-sm text-muted-foreground">{t("treasuryMemory.lastUpdate")}</p>
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
            <h2 className="text-xl font-semibold text-foreground mb-2">{t("uploadsPage.emptyTitle")}</h2>
            <p className="text-muted-foreground mb-6">{t("uploadsPage.emptyBody")}</p>
            <Button onClick={() => navigate("/")}>
              {t("uploadsPage.goDashboard")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("uploadsPage.colFile")}</TableHead>
                  <TableHead>{t("uploadsPage.colDate")}</TableHead>
                  <TableHead>{t("uploadsPage.colPeriod")}</TableHead>
                  <TableHead>{t("uploadsPage.colRecords")}</TableHead>
                  <TableHead>{t("uploadsPage.colType")}</TableHead>
                  <TableHead>{t("uploadsPage.colStatus")}</TableHead>
                  <TableHead className="text-right">{t("uploadsPage.colActions")}</TableHead>
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
                      {upload.date_range?.min_date && upload.date_range?.max_date ? `${formatDate(upload.date_range.min_date)} → ${formatDate(upload.date_range.max_date)}` : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {upload.records_inserted > 0
                        ? `${upload.records_inserted} ${t("uploadsPage.rowsLabel")}`
                        : upload.rows_processed != null
                        ? `${upload.rows_processed} ${t("uploadsPage.rowsLabel")}`
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
                        {t("uploadsPage.viewDetails")}
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
            <SheetTitle>{t("uploadsPage.modalTitle")}</SheetTitle>
            <SheetClose />
          </SheetHeader>

          {selectedUpload && (
            <div className="mt-6 space-y-6">
              {/* SECTION 1: File Info */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{t("uploadsPage.fileInfo")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.name")}</span>
                    <span className="font-medium truncate max-w-[60%]">{selectedUpload.original_filename}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.colDate")}:</span>
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
                    <span className="text-muted-foreground">{t("uploadsPage.colType")}:</span>
                    <span className="font-medium">{getUploadType(selectedUpload)}</span>
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">{t("uploadsPage.colStatus")}:</span>
                    {getStatusBadge(selectedUpload)}
                  </div>
                </CardContent>
              </Card>

              {/* SECTION 2: Processing */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{t("uploadsPage.processing")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.colPeriod")}:</span>
                    <span className="font-medium">
                      {selectedUpload.date_range?.min_date && selectedUpload.date_range?.max_date ? `${formatDate(selectedUpload.date_range.min_date)} → ${formatDate(selectedUpload.date_range.max_date)}` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.rowsProcessed")}</span>
                    <span className="font-medium">{formatNumber(selectedUpload.rows_processed)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.rowsInserted")}</span>
                    <span className="font-medium">{formatNumber(selectedUpload.records_inserted)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.rowsUpdated")}</span>
                    <span className="font-medium">{formatNumber(selectedUpload.records_updated)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.duplicatesSkipped")}</span>
                    <span className="font-medium">{formatNumber(selectedUpload.records_skipped)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* SECTION 3: Treasury Memory */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{t("treasuryMemory.title")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("treasuryMemory.historyAvailable")}:</span>
                    <span className="font-medium">
                      {treasuryProfile?.profile?.historical_months ? `${Math.round(treasuryProfile.profile.historical_months)} ${t("common.months")}` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("treasuryMemory.observations")}:</span>
                    <span className="font-medium">
                      {treasuryProfile?.profile?.historical_months ? `${Math.round(treasuryProfile.profile.historical_months * 30)} ${t("common.days")}` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">{t("treasuryMemory.intelligenceLevel")}:</span>
                    {getQualityBadge(selectedUpload.data_maturity)}
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">{t("forecast.forecasts")}:</span>
                    <Badge variant={treasuryProfile?.profile?.forecasting_enabled ? "default" : "outline"}>
                      {treasuryProfile?.profile?.forecasting_enabled ? t("uploadsPage.yes") : t("uploadsPage.no")}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t("uploadsPage.lastKnownDate")}</span>
                    <span className="font-medium">—</span>
                  </div>
                </CardContent>
              </Card>

              {/* SECTION 4: Business Impact */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{t("uploadsPage.businessImpact")}</CardTitle>
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
