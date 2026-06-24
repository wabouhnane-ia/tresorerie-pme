"""
SCRIPT DE VALIDATION DES CORRECTIONS
=====================================

Ce script valide que toutes les corrections ont été correctement appliquées
aux 4 fichiers modifiés.

Exécution : python validate_corrections.py
"""

import sys
from pathlib import Path

# Couleurs pour terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def check_file(filepath: str, checks: list[tuple[str, str]]) -> tuple[int, int]:
    """
    Vérifie qu'un fichier contient les corrections attendues.
    
    Args:
        filepath: Chemin du fichier à vérifier
        checks: Liste de tuples (description, string_à_chercher)
    
    Returns:
        (nombre_succès, nombre_total)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"{RED}✗ Erreur lecture {filepath}: {e}{RESET}")
        return 0, len(checks)
    
    successes = 0
    failures = 0
    
    print(f"\n📁 {Path(filepath).name}")
    print("=" * 60)
    
    for description, search_string in checks:
        if search_string in content:
            print(f"{GREEN}✓{RESET} {description}")
            successes += 1
        else:
            print(f"{RED}✗{RESET} {description}")
            failures += 1
    
    return successes, len(checks)


def main():
    """Valide toutes les corrections."""
    
    print("=" * 60)
    print("🔍 VALIDATION DES CORRECTIONS")
    print("=" * 60)
    
    total_success = 0
    total_checks = 0
    
    # ========================================
    # FICHIER 1 : prophet_model.py
    # ========================================
    
    checks_prophet = [
        ("Regressors vidés", 'self.regressors = []'),
        ("Weekly seasonality désactivée", 'weekly_seasonality=False'),
        ("Changepoint prior scale réduit", 'changepoint_prior_scale=0.05'),
        ("Préparation sans boucle regressors", '# CORRECTION : pas de boucle regressors (liste vide)'),
        ("Moroccan holidays configurés", 'add_country_holidays(country_name="MA")'),
    ]
    
    s, t = check_file("app/forecasting/prophet_model.py", checks_prophet)
    total_success += s
    total_checks += t
    
    # ========================================
    # FICHIER 2 : data_preparation.py
    # ========================================
    
    checks_data_prep = [
        ("Import RobustScaler", 'from sklearn.preprocessing import RobustScaler'),
        ("Instanciation RobustScaler", 'self.scaler = RobustScaler()'),
        ("Feature tb_lag_1 présente", '"tb_lag_1"'),
        ("Feature tb_rolling_7 présente", '"tb_rolling_7"'),
        ("Feature is_payment_day présente", '"is_payment_day"'),
        ("Feature tb_rolling_std_7 présente", '"tb_rolling_std_7"'),
        ("Feature day_sin présente", '"day_sin"'),
        ("Feature month_sin présente", '"month_sin"'),
        ("Feature weekday_sin présente", '"weekday_sin"'),
        ("Méthode add_features() existe", 'def add_features(self, df: pd.DataFrame) -> pd.DataFrame:'),
        ("Lags créés dans add_features()", 'df["tb_lag_1"] = df["treasury_balance"].shift(1)'),
        ("Rolling créés dans add_features()", 'df["tb_rolling_7"] = df["treasury_balance"].rolling(7).mean()'),
        ("Flag paiements créé", 'df["is_payment_day"]'),
        ("Dropna pour NaN lags/rolling", 'df = df.dropna().reset_index(drop=True)'),
    ]
    
    s, t = check_file("app/lstm/data_preparation.py", checks_data_prep)
    total_success += s
    total_checks += t
    
    # ========================================
    # FICHIER 3 : lstm_model.py
    # ========================================
    
    checks_lstm = [
        ("Unités LSTM par défaut à [64, 32]", 'self.lstm_units = lstm_units or [64, 32]'),
        ("Dropout par défaut à 0.2", 'self.dropout = dropout'),
    ]
    
    s, t = check_file("app/models/lstm_model.py", checks_lstm)
    total_success += s
    total_checks += t
    
    # ========================================
    # FICHIER 4 : forecast_db_service.py
    # ========================================
    
    checks_forecast_service = [
        ("Import EarlyStopping", 'from tensorflow.keras.callbacks import EarlyStopping'),
        ("Appel add_features()", 'feature_df = prep.add_features(df.copy())'),
        ("Appel select_features() après", 'feature_df = prep.select_features(feature_df)'),
        ("EarlyStopping créé", 'early_stop = EarlyStopping('),
        ("Monitor val_loss", 'monitor="val_loss"'),
        ("Patience 10", 'patience=10'),
        ("Restore best weights", 'restore_best_weights=True'),
        ("Epochs augmenté à 100", 'epochs=100'),
        ("Batch size réduit à 16", 'batch_size=16'),
        ("Validation split 0.1", 'validation_split=0.1'),
        ("Validation non mélangée (shuffle=False)", 'shuffle=False'),
        ("Callbacks passés à fit", 'callbacks=[early_stop]'),
        ("Index tb_lag_1", 'idx_lag_1 = prep.features.index("tb_lag_1")'),
        ("Index tb_rolling_7", 'idx_rm_7 = prep.features.index("tb_rolling_7")'),
        ("Index tb_rolling_std_7", 'idx_rstd_7 = prep.features.index("tb_rolling_std_7")'),
        ("Sélection basée sur MASE", 'Selected {best_model} by lowest MASE'),
        ("Base de données best_mase", '"best_mase": best_mase'),
    ]
    
    s, t = check_file("app/services/forecast_db_service.py", checks_forecast_service)
    total_success += s
    total_checks += t
    
    # ========================================
    # RÉSUMÉ
    # ========================================
    
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    
    percentage = (total_success / total_checks * 100) if total_checks > 0 else 0
    
    print(f"Total vérifications réussies : {total_success}/{total_checks} ({percentage:.1f}%)")
    
    if total_success == total_checks:
        print(f"\n{GREEN}✅ TOUTES LES CORRECTIONS SONT PRÉSENTES{RESET}")
        print("\n🚀 Prochaines étapes :")
        print("   1. Redémarrer le backend")
        print("   2. Lancer un forecast sur une entreprise test")
        print("   3. Vérifier les métriques dans forecast_runs")
        return 0
    else:
        print(f"\n{RED}❌ CERTAINES CORRECTIONS SONT MANQUANTES{RESET}")
        print(f"\n{total_checks - total_success} vérification(s) ont échoué.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
