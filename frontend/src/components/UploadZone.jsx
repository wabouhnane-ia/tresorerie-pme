import { useState, useCallback, useRef } from "react";
import API from "../services/api";
import { useTranslation } from "../i18n/LanguageProvider";
import { Upload, CheckCircle2, Calendar, FileSpreadsheet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Alert, AlertTitle, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";

const ERROR_CODE_KEYS = {
  DUPLICATE_DATASET: "upload.errors.duplicate",
  INSUFFICIENT_HISTORY: "upload.errors.insufficientHistory",
  MISSING_REQUIRED_COLUMNS: "upload.errors.missingColumns",
  CONTINUITY_GAP: "upload.errors.continuityGap",
  CONTINUITY_OVERLAP: "upload.errors.continuityOverlap",
  QUOTA_EXCEEDED: "upload.errors.quotaExceeded",
};

export default function UploadZone({ onUploadSuccess, disabled, disabledMessage, treasuryProfile }) {
  const { formatDate, language, t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [errorDetails, setErrorDetails] = useState(null);
  const [successData, setSuccessData] = useState(null);
  const fileInputRef = useRef(null);

  const getErrorTitle = (code) => {
    const key = ERROR_CODE_KEYS[code];
    return key ? t(key) : t("upload.errors.failed");
  };

  const getErrorMessage = (e) => {
    if (typeof e === "string") return e;

    if (e?.response?.data) {
      const data = e.response.data;
      const detail = data.detail;

      if (typeof detail === "object" && detail !== null && !Array.isArray(detail)) {
        if (detail.message) return detail.message;
      }
      if (data.message) return data.message;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return detail.map((d) => d.msg || d.message).join(", ");
      }
      if (data.error) return data.error;
    }

    return t("upload.genericError");
  };

  const getErrorDetails = (e) => {
    if (e?.response?.data) {
      const data = e.response.data;
      const detail =
        typeof data.detail === "object" && data.detail !== null && !Array.isArray(data.detail)
          ? data.detail
          : data;

      return {
        errorCode: detail.error_code || detail.errorCode || "UNKNOWN",
        errorType: detail.error_type || "general",
        message: getErrorMessage(e),
        additionalInfo: {
          missingColumns: detail.missing_columns,
          requiredColumns: detail.required_columns,
          detectedMonths: detail.detected_months,
          requiredMonths: detail.required_months,
          gapDays: detail.gap_days,
          overlapDays: detail.overlap_days,
        },
      };
    }

    return {
      errorCode: "UNKNOWN",
      errorType: "general",
      message: getErrorMessage(e),
      additionalInfo: {},
    };
  };

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFiles = async (files) => {
    const file = files[0];
    if (!file) return;

    setError(null);
    setSuccessData(null);
    setUploading(true);
    setProgress(10);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("locale", language);
      setProgress(30);

      const response = await API.post("/upload/financial-data", formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total > 0) {
            const percentCompleted = Math.round((progressEvent.loaded * 50) / progressEvent.total);
            setProgress(30 + percentCompleted);
          }
        },
      });

      setProgress(90);

      const uploadData = response.data;

      if (uploadData.success === false || uploadData.duplicate_detected || uploadData.duplicate) {
        const code = uploadData.error_code || (uploadData.duplicate ? "DUPLICATE_DATASET" : "UNKNOWN");
        setError(uploadData.message || t("upload.errors.failed"));
        setErrorDetails({
          errorCode: code,
          errorType: uploadData.error_type || "general",
          message: uploadData.message,
          additionalInfo: {},
        });
        return;
      }

      const onboardingStatus = uploadData.onboarding_status;
      const forecastingEnabled = uploadData.forecasting_enabled;
      const historicalMonths = uploadData.historical_months || 0;

      setProgress(100);

      const successText = onboardingStatus === "INSUFFICIENT_HISTORY" || !forecastingEnabled
        ? t("upload.historyUpdated", { months: historicalMonths })
        : t("upload.intelligenceUpdated");

      setSuccessData({
        filename: file.name,
        rowsProcessed: uploadData.rows_processed,
        dateRange: uploadData.date_range,
        message: successText,
        classification: uploadData.classification,
        recordsAppended: uploadData.records_inserted || uploadData.records_appended,
        recordsSkipped: uploadData.records_skipped,
        totalRecords: uploadData.total_records,
        historicalGrowth: uploadData.historical_growth,
        forecastUpdated: uploadData.forecast_retrained
      });

      if (onUploadSuccess) {
        setTimeout(() => onUploadSuccess(uploadData), 2000);
      }
    } catch (err) {
      console.error("Upload error:", err);
      setError(getErrorMessage(err));
      setErrorDetails(getErrorDetails(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) handleFiles(files);
    },
    [t]
  );

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) handleFiles(files);
  };

  const reset = () => {
    setError(null);
    setErrorDetails(null);
    setSuccessData(null);
    setUploading(false);
    setProgress(0);
  };

  if (disabled) {
    return (
      <Card className="w-full">
        <CardContent className="pt-6 text-center">
          <div className="text-muted-foreground mb-4">
            <Upload className="w-16 h-16 mx-auto opacity-50" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">{t("upload.disabled")}</h3>
          <p className="text-muted-foreground">{disabledMessage}</p>
        </CardContent>
      </Card>
    );
  }

  if (successData) {
    return (
      <Card className="w-full border-border">
        <CardHeader>
          <div className="text-center">
            <Badge variant="default" className="mb-4">Success</Badge>
            <CardTitle className="text-lg">{t("upload.success")}</CardTitle>
            <CardDescription>{successData.message}</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {/* Phase 4: Smart Fusion */}
          {treasuryProfile && (
            <div className="mb-6">
              <Alert className="border-green-500 bg-green-50 dark:bg-green-950/30">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <AlertTitle className="text-green-700 dark:text-green-300">Mise à jour incrémentielle détectée</AlertTitle>
                <AlertDescription className="text-green-600 dark:text-green-400">
                  Les nouvelles données ont été fusionnées avec l'historique existant.
                </AlertDescription>
              </Alert>
            </div>
          )}
          
          {/* Phase 3: Incremental Update Summary */}
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Nom du fichier</p>
                <p className="font-medium truncate">{successData.filename}</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Nouvelles lignes</p>
                <p className="font-medium">{successData.recordsAppended || 0}</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Lignes mises à jour</p>
                <p className="font-medium">{successData.recordsUpdated || 0}</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Doublons ignorés</p>
                <p className="font-medium">{successData.recordsSkipped || 0}</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Historique total</p>
                <p className="font-medium">{successData.totalRecords || "—"} jours</p>
              </div>
            </div>

            <Separator />

            <div className="flex items-center justify-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-success" />
              <p className="font-medium">
                {successData.forecastUpdated ? "Prévisions mises à jour" : "Prévisions non mises à jour (historique insuffisant)"}
              </p>
            </div>

            <div className="flex justify-center">
              <Button onClick={reset}>
                {t("upload.importAnother")}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 w-full">
      {/* Data Requirements Card - Phase 2 */}
      <Card className="w-full border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5" />
            {treasuryProfile ? "Mémoire de trésorerie active" : "Première configuration de votre mémoire de trésorerie"}
          </CardTitle>
          <CardDescription>
            {treasuryProfile 
              ? `${t("treasuryMemory.historyAvailable")}: ${Math.round(treasuryProfile.historical_months)} ${t("common.months")}. ${t("treasuryMemory.lastUpdate")}: ${formatDate(treasuryProfile.latest_data_date, {day: "2-digit", month: "2-digit", year: "numeric"})}.`
              : "Minimum requis: 24 mois. Recommandé: 36 mois."
            }
          </CardDescription>
        </CardHeader>
        {!treasuryProfile && (
        <CardContent className="space-y-6">
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-success" />
              Colonnes obligatoires
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Date</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Solde de trésorerie</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Encaissements</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Décaissements</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Encaissements planifiés</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Encaissements en retard</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Décaissements planifiés</span>
              </div>
              <div className="p-3 bg-muted rounded-lg flex items-center gap-2">
                <Badge variant="default" className="shrink-0">✓</Badge>
                <span>Décaissements en retard</span>
              </div>
            </div>
          </div>

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <h4 className="text-sm font-semibold text-foreground">Historique minimum</h4>
              </div>
              <p className="text-muted-foreground">24 mois</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <h4 className="text-sm font-semibold text-foreground">Historique recommandé</h4>
              </div>
              <p className="text-muted-foreground">36 mois</p>
            </div>
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3">Formats pris en charge</h4>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">CSV</Badge>
              <Badge variant="secondary">Excel (.xlsx, .xls)</Badge>
            </div>
          </div>
        </CardContent>
        )}
      </Card>

      {/* Upload Card */}
      <Card className="w-full border-border">
        <CardHeader>
          <CardTitle>Importer vos données financières</CardTitle>
          <CardDescription>Téléchargez un fichier Excel ou CSV.</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            className={`cursor-pointer p-12 rounded-lg border-2 border-dashed transition-all duration-300 flex flex-col items-center justify-center ${
              isDragging
                ? "border-primary bg-primary/10"
                : error
                  ? "border-destructive bg-destructive/10"
                  : "border-muted-foreground/25 hover:border-primary hover:bg-accent"
            }`}
          >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".csv,.xlsx,.xls,.pdf"
            className="hidden"
          />

          {uploading ? (
            <div className="text-center w-full">
              <Upload className="w-12 h-12 mx-auto mb-4 text-primary animate-pulse" />
              <h3 className="text-lg font-semibold text-foreground mb-2">{t("upload.processing")}</h3>
              <p className="text-muted-foreground mb-6">{t("upload.processingHint")}</p>
              <div className="w-full max-w-md mx-auto mb-4">
                <Progress value={progress} />
              </div>
              <div className="flex gap-2 justify-center flex-wrap">
                <Badge variant="secondary">Parsing</Badge>
                <Badge variant="secondary">Mapping</Badge>
                <Badge variant="secondary">Validation</Badge>
                <Badge variant="secondary">Forecast</Badge>
              </div>
            </div>
          ) : error ? (
            <div className="text-center w-full">
              <Alert variant="destructive" className="mb-4">
                <AlertTitle>{getErrorTitle(errorDetails?.errorCode)}</AlertTitle>
                <AlertDescription className="whitespace-pre-line">{error}</AlertDescription>
              </Alert>

              {errorDetails?.additionalInfo?.missingColumns && (
                <div className="text-left w-full max-w-md mx-auto bg-muted p-3 rounded-lg mb-4">
                  <p className="font-semibold mb-2 text-sm">{t("upload.missingColumns")}</p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground">
                    {errorDetails.additionalInfo.missingColumns.map((col, idx) => (
                      <li key={idx}>{col}</li>
                    ))}
                  </ul>
                </div>
              )}

              {errorDetails?.additionalInfo?.detectedMonths !== undefined &&
                errorDetails?.additionalInfo?.requiredMonths && (
                  <div className="text-left w-full max-w-md mx-auto bg-muted p-3 rounded-lg mb-4">
                    <p className="text-sm">
                      {t("upload.detectedHistory")} <strong>{errorDetails.additionalInfo.detectedMonths}</strong>
                    </p>
                    <p className="text-sm">
                      {t("upload.requiredMinimum")} <strong>{errorDetails.additionalInfo.requiredMonths}</strong>
                    </p>
                  </div>
                )}

              {errorDetails?.additionalInfo?.gapDays > 0 && (
                <div className="text-left w-full max-w-md mx-auto bg-muted p-3 rounded-lg mb-4">
                  <p className="text-sm">
                    {t("upload.gapDetected")} <strong>{t("upload.days", { count: errorDetails.additionalInfo.gapDays })}</strong>
                  </p>
                </div>
              )}

              {errorDetails?.additionalInfo?.overlapDays > 0 && (
                <div className="text-left w-full max-w-md mx-auto bg-muted p-3 rounded-lg mb-4">
                  <p className="text-sm">
                    {t("upload.overlapDetected")} <strong>{t("upload.days", { count: errorDetails.additionalInfo.overlapDays })}</strong>
                  </p>
                </div>
              )}

              <Button
                variant="destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  reset();
                }}
              >
                {t("common.retry")}
              </Button>
            </div>
          ) : (
            <div className="text-center">
              <Upload className="w-12 h-12 mx-auto mb-4 text-primary" />
              <h3 className="text-lg font-semibold text-foreground mb-2">{t("upload.dropTitle")}</h3>
              <p className="text-muted-foreground mb-4">{t("upload.dropHint")}</p>
              <div className="flex justify-center">
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  {t("upload.browse")}
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
    </div>
  );
}
