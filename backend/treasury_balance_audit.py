"""
AUDIT COMPLET : Incohérence treasury_balance vs cumsum(net_cashflow)

Objectif : Diagnostiquer précisément pourquoi treasury_balance n'est pas cohérent
avec le cumul de net_cashflow pour la société 6a1444222a29a5532075de83

Résultats du diagnostic initial :
- corr(treasury_balance, cumsum(net_cashflow)) = 0.837
- écart constant ≈ 290 958 MAD sur de nombreuses dates
- suggère un problème de calcul métier ou d'agrégation

NE RIEN MODIFIER - RAPPORT DE DIAGNOSTIC UNIQUEMENT
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np
from bson import ObjectId

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.mongodb import database
from app.db import collections as c


class TreasuryBalanceAuditor:
    """Audit complet de la cohérence du treasury_balance"""
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.company_oid = ObjectId(company_id)
        self.results = {}
        
    def _print_section(self, title: str):
        """Afficher une section"""
        print("\n" + "=" * 100)
        print(f"## {title}")
        print("=" * 100)

    def _print_finding(self, label: str, value: Any, indent: int = 0):
        """Afficher un résultat d'audit"""
        prefix = "  " * indent + "📍 "
        if isinstance(value, (list, dict)):
            print(f"{prefix}{label}:")
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"  {prefix}  {k}: {v}")
            else:
                for item in value:
                    print(f"  {prefix}  {item}")
        else:
            print(f"{prefix}{label}: {value}")
    
    async def step1_locate_sources(self):
        """ÉTAPE 1 : LOCALISER LES SOURCES"""
        self._print_section("ÉTAPE 1 — LOCALISER LES SOURCES")
        
        print("\n🔍 Fichiers identifiés qui manipulent treasury_balance :\n")
        
        sources = {
            "Parsing & Ingestion": [
                "app/services/upload_parser.py - normalize_financial_dataframe()",
                "  → Ligne 297: out['treasury_balance'] = out['net_cashflow'].cumsum()",
                "  → CALCUL: Si treasury_balance absent du fichier, calcul par cumsum(net_cashflow)"
            ],
            "Insertion en BD": [
                "app/services/continuous_history_service.py - append_historical_data()",
                "  → Ligne 141: cash_inflow / cash_outflow extraits du CSV",
                "  → Ligne 143: net_cashflow = cash_inflow - cash_outflow (RECALCULÉ)",
                "  → Ligne 145: treasury_balance ajouté SI PRÉSENT dans le CSV"
            ],
            "Lecture depuis BD": [
                "app/services/forecast_db_service.py",
                "app/services/analytics_service.py",
                "  → Récupération directe depuis financial_records"
            ],
            "Modèles de prédiction": [
                "app/lstm/data_preparation.py",
                "app/forecasting/prophet_model.py",
                "  → Utilisent treasury_balance tel quel, aucun recalcul"
            ]
        }
        
        for category, files in sources.items():
            print(f"\n📂 {category}:")
            for file in files:
                print(f"   {file}")
        
        self.results['sources'] = sources

    async def step2_reconstruct_business_logic(self):
        """ÉTAPE 2 : RECONSTRUIRE LA LOGIQUE MÉTIER"""
        self._print_section("ÉTAPE 2 — RECONSTRUIRE LA LOGIQUE MÉTIER")
        
        print("\n📐 Calcul de net_cashflow :")
        print("  → Formule: net_cashflow = cash_inflow - cash_outflow")
        print("  → Localisation: continuous_history_service.py ligne 143")
        print("  → TOUJOURS recalculé à l'insertion, même si présent dans le CSV")
        
        print("\n📐 Calcul de treasury_balance :")
        print("  → CAS 1: Si treasury_balance PRÉSENT dans le CSV uploadé")
        print("     - Valeur importée TELLE QUELLE")
        print("     - Aucun recalcul, aucune validation")
        print("     - Ligne: upload_parser.py:285 - out[internal] = pd.to_numeric(...)")
        print("  → CAS 2: Si treasury_balance ABSENT du CSV")
        print("     - Calcul automatique: treasury_balance = cumsum(net_cashflow)")
        print("     - Ligne: upload_parser.py:297")
        
        print("\n⚠️  PROBLÈME POTENTIEL IDENTIFIÉ:")
        print("  → Si le CSV contient treasury_balance, il est importé sans validation")
        print("  → Aucune vérification de cohérence avec net_cashflow")
        print("  → L'écart constant de 290 958 MAD suggère:")
        print("     - Soit un solde initial incorrect")
        print("     - Soit un calcul erroné dans le CSV source")
        
        self.results['business_logic'] = {
            "net_cashflow_formula": "cash_inflow - cash_outflow",
            "treasury_balance_source": "Importé du CSV si présent, sinon cumsum(net_cashflow)",
            "validation": "AUCUNE validation de cohérence"
        }

    async def step3_test_coherence(self):
        """ÉTAPE 3 : TEST DE COHÉRENCE"""
        self._print_section("ÉTAPE 3 — TEST DE COHÉRENCE")
        
        print(f"\n🔬 Analyse pour la société: {self.company_id}\n")
        
        # Charger toutes les données
        cursor = database[c.FINANCIAL_RECORDS].find(
            {"company_id": self.company_oid}
        ).sort("date", 1)
        
        records = await cursor.to_list(length=None)
        
        if not records:
            print("❌ Aucun enregistrement trouvé pour cette société")
            return
        
        print(f"✅ {len(records)} enregistrements chargés")
        
        # Construire le DataFrame
        df = pd.DataFrame([
            {
                'date': r['date'],
                'cash_inflow': r.get('cash_inflow', 0),
                'cash_outflow': r.get('cash_outflow', 0),
                'net_cashflow': r.get('net_cashflow', 0),
                'treasury_balance': r.get('treasury_balance', 0),
                'upload_id': str(r.get('upload_id', ''))
            }
            for r in records
        ])
        
        df = df.sort_values('date').reset_index(drop=True)
        
        # Test 1: Vérifier que net_cashflow = cash_inflow - cash_outflow
        df['net_cashflow_calc'] = df['cash_inflow'] - df['cash_outflow']
        df['net_diff'] = abs(df['net_cashflow'] - df['net_cashflow_calc'])
        
        max_net_diff = df['net_diff'].max()
        print(f"\n📊 Vérification: net_cashflow = cash_inflow - cash_outflow")
        print(f"  → Écart max: {max_net_diff:.2f} MAD")
        
        if max_net_diff > 0.01:
            print(f"  ⚠️  INCOHÉRENCE DÉTECTÉE dans net_cashflow")
            worst = df.nlargest(5, 'net_diff')[['date', 'cash_inflow', 'cash_outflow', 'net_cashflow', 'net_cashflow_calc', 'net_diff']]
            print(worst.to_string(index=False))
        else:
            print(f"  ✅ net_cashflow cohérent")

        # Test 2: Reconstruire treasury_balance
        treasury_initial = df['treasury_balance'].iloc[0]
        df['treasury_rebuilt'] = treasury_initial + df['net_cashflow'].cumsum()
        
        # Ajuster pour démarrer du bon point
        df['treasury_rebuilt'] = df['treasury_rebuilt'] - df['net_cashflow'].iloc[0]
        
        df['treasury_diff'] = abs(df['treasury_balance'] - df['treasury_rebuilt'])
        
        # Statistiques de cohérence
        corr = df['treasury_balance'].corr(df['treasury_rebuilt'])
        mae = df['treasury_diff'].mean()
        rmse = np.sqrt((df['treasury_diff'] ** 2).mean())
        max_error = df['treasury_diff'].max()
        mean_error = df['treasury_diff'].mean()
        
        print(f"\n📊 Test de cohérence: treasury_balance vs cumsum(net_cashflow)")
        print(f"  → Solde initial: {treasury_initial:,.2f} MAD")
        print(f"  → Corrélation: {corr:.6f}")
        print(f"  → MAE (erreur abs moyenne): {mae:,.2f} MAD")
        print(f"  → RMSE: {rmse:,.2f} MAD")
        print(f"  → Erreur max: {max_error:,.2f} MAD")
        print(f"  → Erreur moyenne: {mean_error:,.2f} MAD")
        
        # Analyser l'écart constant
        is_constant = df['treasury_diff'].std() < 1.0
        if is_constant:
            constant_value = df['treasury_diff'].iloc[0]
            print(f"\n⚠️  ÉCART CONSTANT DÉTECTÉ: {constant_value:,.2f} MAD")
            print(f"  → Ceci suggère un problème de SOLDE INITIAL")
        
        # Afficher les 50 pires dates
        print(f"\n📋 TOP 50 pires dates (erreur absolue) :")
        worst_50 = df.nlargest(50, 'treasury_diff')[
            ['date', 'treasury_balance', 'treasury_rebuilt', 'treasury_diff', 'net_cashflow', 'upload_id']
        ]
        print(worst_50.to_string(index=False))
        
        self.results['coherence'] = {
            'treasury_initial': float(treasury_initial),
            'correlation': float(corr),
            'mae': float(mae),
            'rmse': float(rmse),
            'max_error': float(max_error),
            'mean_error': float(mean_error),
            'is_constant_error': is_constant,
            'constant_value': float(df['treasury_diff'].iloc[0]) if is_constant else None
        }
        
        self.df = df
        return df

    async def step4_detect_root_cause(self):
        """ÉTAPE 4 : DÉTECTER LA CAUSE RACINE"""
        self._print_section("ÉTAPE 4 — DÉTECTER LA CAUSE RACINE")
        
        if not hasattr(self, 'df'):
            print("❌ Données non chargées. Exécuter step3 d'abord.")
            return
        
        df = self.df
        
        print("\n🔍 Analyse des causes possibles:\n")
        
        # A) Solde initial non pris en compte
        coherence = self.results.get('coherence', {})
        is_constant = coherence.get('is_constant_error', False)
        constant_value = coherence.get('constant_value', 0)
        
        if is_constant:
            print("✅ CAUSE A: Solde initial non pris en compte")
            print(f"  → PROBABILITÉ: 🔴 TRÈS ÉLEVÉE")
            print(f"  → PREUVE: Écart constant de {constant_value:,.2f} MAD sur toutes les dates")
            print(f"  → EXPLICATION: Le CSV contient des valeurs de treasury_balance")
            print(f"     qui ne partent pas du même point de départ que cumsum(net_cashflow)")
            print(f"  → SOLUTION: Corriger le solde initial dans le CSV source")
        else:
            print("❌ CAUSE A: Solde initial - PEU PROBABLE")
            print(f"  → L'écart varie (std={df['treasury_diff'].std():.2f})")
        
        # B) Décalage temporel
        df_shifted = df.copy()
        df_shifted['treasury_balance_lag1'] = df_shifted['treasury_balance'].shift(1)
        df_shifted = df_shifted.dropna()
        
        if len(df_shifted) > 0:
            corr_lag1 = df_shifted['treasury_rebuilt'].corr(df_shifted['treasury_balance_lag1'])
            print(f"\n🔍 CAUSE B: Décalage temporel d'un jour")
            if corr_lag1 > 0.95:
                print(f"  → PROBABILITÉ: 🟡 MOYENNE")
                print(f"  → PREUVE: Corrélation avec lag=1 : {corr_lag1:.6f}")
            else:
                print(f"  → PROBABILITÉ: 🟢 FAIBLE")
                print(f"  → Corrélation avec lag=1 : {corr_lag1:.6f}")
        
        # C) Double comptabilisation
        duplicates = df.duplicated(subset=['date'], keep=False)
        dup_count = duplicates.sum()
        print(f"\n🔍 CAUSE C: Double comptabilisation")
        if dup_count > 0:
            print(f"  → PROBABILITÉ: 🔴 ÉLEVÉE")
            print(f"  → PREUVE: {dup_count} dates dupliquées détectées")
            dup_dates = df[duplicates]['date'].unique()
            print(f"  → Dates concernées: {len(dup_dates)}")
        else:
            print(f"  → PROBABILITÉ: 🟢 FAIBLE")
            print(f"  → Aucune duplication de date détectée")

        # D) Erreur d'agrégation quotidienne
        df['day'] = pd.to_datetime(df['date']).dt.date
        daily_counts = df.groupby('day').size()
        multiple_per_day = (daily_counts > 1).sum()
        
        print(f"\n🔍 CAUSE D: Erreur d'agrégation quotidienne")
        if multiple_per_day > 0:
            print(f"  → PROBABILITÉ: 🟡 MOYENNE")
            print(f"  → PREUVE: {multiple_per_day} jours avec plusieurs enregistrements")
        else:
            print(f"  → PROBABILITÉ: 🟢 FAIBLE")
            print(f"  → Un seul enregistrement par jour")
        
        # E) Vérifier les uploads
        unique_uploads = df['upload_id'].nunique()
        print(f"\n🔍 CAUSE E: Erreur lors des imports incrémentaux")
        print(f"  → Nombre d'uploads différents: {unique_uploads}")
        
        if unique_uploads > 1:
            print(f"  → PROBABILITÉ: 🟡 MOYENNE")
            print(f"  → Plusieurs uploads détectés - possible incohérence entre uploads")
            
            # Analyser l'erreur par upload
            upload_errors = df.groupby('upload_id').agg({
                'treasury_diff': ['mean', 'max', 'count']
            })
            print("\n  Erreur par upload_id:")
            print(upload_errors.to_string())
        else:
            print(f"  → PROBABILITÉ: 🟢 FAIBLE")
            print(f"  → Un seul upload")
        
        # F) Mélange de plusieurs comptes
        print(f"\n🔍 CAUSE F: Mélange de plusieurs comptes")
        print(f"  → PROBABILITÉ: 🔵 INCONNU")
        print(f"  → Nécessite vérification manuelle du CSV source")
        
        self.results['root_cause_analysis'] = {
            'constant_error': is_constant,
            'constant_value': float(constant_value) if is_constant else None,
            'duplicate_dates': int(dup_count),
            'multiple_records_per_day': int(multiple_per_day),
            'unique_uploads': int(unique_uploads)
        }

    async def step5_check_incremental_imports(self):
        """ÉTAPE 5 : IMPORTS INCRÉMENTAUX"""
        self._print_section("ÉTAPE 5 — IMPORTS INCRÉMENTAUX")
        
        if not hasattr(self, 'df'):
            print("❌ Données non chargées. Exécuter step3 d'abord.")
            return
        
        df = self.df
        
        print("\n📂 Analyse des uploads pour cette société:\n")
        
        # Récupérer tous les uploads
        uploads_cursor = database[c.UPLOADS].find(
            {"company_id": self.company_oid}
        ).sort("created_at", 1)
        
        uploads = await uploads_cursor.to_list(length=None)
        
        print(f"✅ {len(uploads)} uploads trouvés\n")
        
        for i, upload in enumerate(uploads, 1):
            upload_id = str(upload['_id'])
            created_at = upload.get('created_at', 'Unknown')
            filename = upload.get('original_filename', 'Unknown')
            status = upload.get('status', 'Unknown')
            records_inserted = upload.get('records_inserted', 0)
            classification = upload.get('classification', 'Unknown')
            
            print(f"\n📤 Upload #{i}")
            print(f"  ID: {upload_id}")
            print(f"  Fichier: {filename}")
            print(f"  Date: {created_at}")
            print(f"  Statut: {status}")
            print(f"  Classification: {classification}")
            print(f"  Records insérés: {records_inserted}")
            
            # Analyser les données de cet upload
            upload_records = df[df['upload_id'] == upload_id]
            if len(upload_records) > 0:
                min_date = upload_records['date'].min()
                max_date = upload_records['date'].max()
                avg_error = upload_records['treasury_diff'].mean()
                max_error = upload_records['treasury_diff'].max()
                
                print(f"  Période: {min_date} → {max_date}")
                print(f"  Erreur moyenne: {avg_error:,.2f} MAD")
                print(f"  Erreur max: {max_error:,.2f} MAD")
                
                # Vérifier si l'erreur a changé avec cet upload
                if i > 1:
                    prev_upload_id = str(uploads[i-2]['_id'])
                    prev_records = df[df['upload_id'] == prev_upload_id]
                    if len(prev_records) > 0:
                        prev_avg_error = prev_records['treasury_diff'].mean()
                        error_delta = avg_error - prev_avg_error
                        if abs(error_delta) > 1000:
                            print(f"  ⚠️  DÉRIVE DÉTECTÉE: Δ erreur = {error_delta:,.2f} MAD")
        
        print(f"\n📊 Analyse temporelle des erreurs:")
        print(f"  → Vérification si l'erreur augmente avec le temps")
        
        df_sorted = df.sort_values('date')
        df_sorted['record_index'] = range(len(df_sorted))
        corr_time_error = df_sorted['record_index'].corr(df_sorted['treasury_diff'])
        
        print(f"  → Corrélation (temps, erreur): {corr_time_error:.6f}")
        
        if abs(corr_time_error) > 0.5:
            print(f"  ⚠️  DÉRIVE TEMPORELLE DÉTECTÉE")
        else:
            print(f"  ✅ Pas de dérive temporelle significative")

    async def step6_final_report(self):
        """ÉTAPE 6 : RAPPORT FINAL"""
        self._print_section("ÉTAPE 6 — RAPPORT FINAL")
        
        coherence = self.results.get('coherence', {})
        root_cause = self.results.get('root_cause_analysis', {})
        
        print("\n" + "🎯" * 50)
        print("\n## DIAGNOSTIC FINAL\n")
        print("🎯" * 50)
        
        # 1. Cause racine la plus probable
        print("\n1️⃣  CAUSE RACINE LA PLUS PROBABLE:\n")
        
        is_constant = root_cause.get('constant_error', False)
        constant_value = root_cause.get('constant_value', 0)
        
        if is_constant:
            print("   🔴 SOLDE INITIAL INCORRECT DANS LE CSV SOURCE")
            print(f"\n   Détails:")
            print(f"   • L'écart est constant: {constant_value:,.2f} MAD sur toutes les dates")
            print(f"   • Le CSV importé contient des valeurs de treasury_balance")
            print(f"   • Ces valeurs ne partent pas du même solde initial que cumsum(net_cashflow)")
            print(f"\n   Hypothèse:")
            print(f"   • Le CSV a été généré avec un solde initial de: {coherence.get('treasury_initial', 0):,.2f} MAD")
            print(f"   • Mais le solde réel devrait être: {coherence.get('treasury_initial', 0) - constant_value:,.2f} MAD")
            print(f"   • Différence: {constant_value:,.2f} MAD")
        else:
            print("   🟡 INCOHÉRENCE VARIABLE - CAUSE MULTIPLE")
            print(f"\n   L'écart varie (std={self.df['treasury_diff'].std():.2f})")
            print(f"   Ceci suggère plusieurs problèmes possibles:")
            if root_cause.get('duplicate_dates', 0) > 0:
                print(f"   • Double comptabilisation détectée")
            if root_cause.get('multiple_records_per_day', 0) > 0:
                print(f"   • Agrégation quotidienne incorrecte")
            if root_cause.get('unique_uploads', 0) > 1:
                print(f"   • Incohérences entre plusieurs uploads")
        
        # 2. Niveau de confiance
        print("\n2️⃣  NIVEAU DE CONFIANCE:")
        
        corr = coherence.get('correlation', 0)
        
        if is_constant and corr > 0.8:
            confidence = "🟢 ÉLEVÉ"
            confidence_pct = 95
        elif is_constant:
            confidence = "🟡 MOYEN"
            confidence_pct = 75
        else:
            confidence = "🟠 FAIBLE À MOYEN"
            confidence_pct = 60
        
        print(f"\n   Confiance: {confidence} ({confidence_pct}%)")
        print(f"   • Corrélation: {corr:.4f}")
        print(f"   • Pattern d'erreur: {'Constant' if is_constant else 'Variable'}")

        # 3. Impact sur les métriques
        print("\n3️⃣  IMPACT SUR LES MÉTRIQUES:")
        
        mae = coherence.get('mae', 0)
        rmse = coherence.get('rmse', 0)
        
        print(f"\n   Impact actuel:")
        print(f"   • MAE: {mae:,.2f} MAD")
        print(f"   • RMSE: {rmse:,.2f} MAD")
        print(f"   • R² prédit: ~{corr**2:.4f}")
        
        print(f"\n   Conséquences:")
        print(f"   • Les modèles LSTM/Prophet apprennent sur une cible bruitée")
        print(f"   • La qualité des prédictions est artificiellement dégradée")
        print(f"   • Les recommandations métier sont basées sur des données incorrectes")
        
        if is_constant:
            print(f"\n   Impact après correction (estimation):")
            print(f"   • MAE: ~0 MAD (l'écart serait éliminé)")
            print(f"   • RMSE: réduction de ~{rmse:,.2f} MAD")
            print(f"   • R² potentiel: ~0.99+ (très forte corrélation)")
        
        # 4. Fichiers responsables
        print("\n4️⃣  FICHIERS RESPONSABLES:")
        print(f"\n   Ingestion:")
        print(f"   • upload_parser.py:285 - Importe treasury_balance SANS validation")
        print(f"   • upload_parser.py:297 - Calcule cumsum si absent")
        print(f"\n   Source du problème:")
        print(f"   • ❌ Le CSV source contient des valeurs treasury_balance incorrectes")
        print(f"   • ❌ Aucune validation de cohérence n'est effectuée à l'import")
        
        # 5. Fonctions responsables
        print("\n5️⃣  FONCTIONS RESPONSABLES:")
        print(f"\n   • normalize_financial_dataframe() dans upload_parser.py")
        print(f"     → Ligne 285: Accepte treasury_balance tel quel")
        print(f"     → AUCUNE validation de: treasury_balance == cumsum(net_cashflow)")
        print(f"\n   • append_historical_data() dans continuous_history_service.py")
        print(f"     → Ligne 145: Insère treasury_balance sans vérification")
        
        # 6. Exemple concret montrant le bug
        print("\n6️⃣  EXEMPLE CONCRET MONTRANT LE BUG:")
        
        if hasattr(self, 'df') and len(self.df) > 0:
            sample = self.df.iloc[0]
            print(f"\n   Date: {sample['date']}")
            print(f"   • treasury_balance (CSV): {sample['treasury_balance']:,.2f} MAD")
            print(f"   • treasury_rebuilt (cumsum): {sample['treasury_rebuilt']:,.2f} MAD")
            print(f"   • Écart: {sample['treasury_diff']:,.2f} MAD")
            print(f"   • net_cashflow: {sample['net_cashflow']:,.2f} MAD")
            
            if is_constant:
                print(f"\n   Scénario probable:")
                print(f"   • Le CSV a été généré avec: solde_initial = {sample['treasury_balance']:,.2f}")
                print(f"   • Mais devrait être: solde_initial = {sample['treasury_rebuilt']:,.2f}")
                print(f"   • Ou: décalage constant de {constant_value:,.2f} MAD appliqué à toute la série")
        
        print("\n" + "=" * 100)
        print("\n✅ AUDIT TERMINÉ\n")
        print("=" * 100)
        
        self.results['final_diagnosis'] = {
            'root_cause': 'SOLDE_INITIAL_INCORRECT' if is_constant else 'MULTIPLE_ISSUES',
            'confidence': confidence_pct,
            'constant_error': is_constant,
            'constant_value': float(constant_value) if is_constant else None,
            'files_responsible': [
                'app/services/upload_parser.py',
                'app/services/continuous_history_service.py'
            ],
            'functions_responsible': [
                'normalize_financial_dataframe()',
                'append_historical_data()'
            ]
        }


async def main():
    """Point d'entrée principal"""
    
    import argparse
    parser = argparse.ArgumentParser(description='Audit complet de treasury_balance')
    parser.add_argument('--company-id', required=True, help='ID de la société à auditer')
    args = parser.parse_args()
    
    auditor = TreasuryBalanceAuditor(args.company_id)
    
    # Exécuter toutes les étapes
    await auditor.step1_locate_sources()
    await auditor.step2_reconstruct_business_logic()
    await auditor.step3_test_coherence()
    await auditor.step4_detect_root_cause()
    await auditor.step5_check_incremental_imports()
    await auditor.step6_final_report()


if __name__ == "__main__":
    asyncio.run(main())
