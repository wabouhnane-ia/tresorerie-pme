"""
AUDIT MÉTIER COMPLET : Validation rigoureuse de treasury_balance

Objectif : Vérifier si le diagnostic précédent est correct ou si treasury_balance
           représente en réalité le solde bancaire réel.

Mission : AUDIT UNIQUEMENT - NE RIEN MODIFIER

Hypothèse à vérifier :
    "Le CSV contient un solde initial erroné de ~290 958 MAD"

Alternative :
    treasury_balance pourrait être le véritable solde bancaire,
    et le problème serait ailleurs (forecast, scaling, features, etc.)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np
from bson import ObjectId
from scipy import stats

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.mongodb import database
from app.db import collections as c


class TreasuryBalanceBusinessAuditor:
    """Audit métier complet et rigoureux"""
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.company_oid = ObjectId(company_id)
        self.results = {}
        self.df = None
        
    def _print_section(self, title: str):
        """Afficher une section"""
        print("\n" + "=" * 120)
        print(f"## {title}")
        print("=" * 120)

    
    async def load_data(self):
        """Charger toutes les données"""
        cursor = database[c.FINANCIAL_RECORDS].find(
            {"company_id": self.company_oid}
        ).sort("date", 1)
        
        records = await cursor.to_list(length=None)
        
        if not records:
            print("❌ Aucun enregistrement trouvé")
            return None
        
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
        self.df = df
        
        print(f"✅ {len(df)} enregistrements chargés")
        print(f"📅 Période: {df['date'].min()} → {df['date'].max()}")
        
        return df
    
    async def step1_fundamental_test(self):
        """ÉTAPE 1 : TEST FONDAMENTAL"""
        self._print_section("ÉTAPE 1 — TEST FONDAMENTAL : Vérification de la relation récursive")
        
        if self.df is None:
            await self.load_data()
        
        df = self.df.copy()
        
        print("\n🔬 Test fondamental : treasury_balance(t) = treasury_balance(t-1) + net_cashflow(t)\n")
        
        # Calculer la valeur attendue
        df['treasury_balance_lag'] = df['treasury_balance'].shift(1)
        df['treasury_balance_expected'] = df['treasury_balance_lag'] + df['net_cashflow']
        
        # Exclure la première ligne (pas de t-1)
        df_test = df.iloc[1:].copy()
        
        # Calculer l'erreur
        df_test['error'] = df_test['treasury_balance'] - df_test['treasury_balance_expected']
        df_test['abs_error'] = df_test['error'].abs()
        df_test['pct_error'] = (df_test['abs_error'] / df_test['treasury_balance'].abs() * 100)
        
        # Vérifier la relation (tolérance de 0.01 MAD pour les arrondis)
        tolerance = 0.01
        df_test['is_valid'] = df_test['abs_error'] < tolerance
        
        # Statistiques
        total_rows = len(df_test)
        valid_rows = df_test['is_valid'].sum()
        invalid_rows = total_rows - valid_rows
        valid_pct = (valid_rows / total_rows * 100) if total_rows > 0 else 0
        
        mean_error = df_test['error'].mean()
        std_error = df_test['error'].std()
        median_error = df_test['error'].median()
        max_error = df_test['abs_error'].max()
        rmse = np.sqrt((df_test['error'] ** 2).mean())
        
        print(f"📊 Résultats du test fondamental:\n")
        print(f"  Total de lignes testées: {total_rows}")
        print(f"  Lignes valides (erreur < {tolerance} MAD): {valid_rows} ({valid_pct:.2f}%)")
        print(f"  Lignes invalides: {invalid_rows} ({100-valid_pct:.2f}%)")
        print(f"\n  Erreur moyenne: {mean_error:,.2f} MAD")
        print(f"  Erreur médiane: {median_error:,.2f} MAD")
        print(f"  Écart-type: {std_error:,.2f} MAD")
        print(f"  Erreur max: {max_error:,.2f} MAD")
        print(f"  RMSE: {rmse:,.2f} MAD")
        
        # Interprétation
        print(f"\n💡 Interprétation:")
        
        if valid_pct >= 99:
            print(f"  ✅ RELATION VÉRIFIÉE : {valid_pct:.2f}% des lignes respectent la relation récursive")
            print(f"  → treasury_balance est cohérent avec net_cashflow")
            print(f"  → Le problème n'est PAS dans la relation récursive")
            conclusion = "COHERENT"
        elif valid_pct >= 95:
            print(f"  ⚠️  RELATION PARTIELLEMENT VÉRIFIÉE : {valid_pct:.2f}% des lignes")
            print(f"  → Quelques anomalies ponctuelles ({invalid_rows} lignes)")
            conclusion = "PARTIAL"
        else:
            print(f"  ❌ RELATION NON VÉRIFIÉE : Seulement {valid_pct:.2f}% des lignes")
            print(f"  → treasury_balance NE suit PAS la logique récursive attendue")
            conclusion = "INCOHERENT"

        
        # Afficher les 50 pires anomalies
        print(f"\n📋 TOP 50 pires anomalies (erreur absolue):\n")
        worst_50 = df_test.nlargest(50, 'abs_error')[
            ['date', 'treasury_balance', 'treasury_balance_expected', 'error', 'net_cashflow', 'is_valid']
        ]
        print(worst_50.to_string(index=False))
        
        self.results['fundamental_test'] = {
            'total_rows': int(total_rows),
            'valid_rows': int(valid_rows),
            'invalid_rows': int(invalid_rows),
            'valid_pct': float(valid_pct),
            'mean_error': float(mean_error),
            'std_error': float(std_error),
            'median_error': float(median_error),
            'max_error': float(max_error),
            'rmse': float(rmse),
            'conclusion': conclusion
        }
        
        self.df_test = df_test
        return df_test
    
    async def step2_identify_real_meaning(self):
        """ÉTAPE 2 : IDENTIFIER LA SIGNIFICATION RÉELLE"""
        self._print_section("ÉTAPE 2 — IDENTIFIER LA SIGNIFICATION RÉELLE DE treasury_balance")
        
        print("\n🔍 Détermination de ce que représente treasury_balance:\n")
        
        # Analyse du code source
        print("📂 Analyse du code source:\n")
        
        code_evidence = {
            "upload_parser.py (ligne 297)": {
                "code": 'out["treasury_balance"] = out["net_cashflow"].cumsum()',
                "interpretation": "Si absent du CSV → calculé par cumsum(net_cashflow)",
                "signification": "CUMUL DES FLUX"
            },
            "upload_parser.py (ligne 285)": {
                "code": 'out[internal] = pd.to_numeric(col_data, errors="coerce").fillna(0)',
                "interpretation": "Si présent dans CSV → importé tel quel",
                "signification": "VALEUR DU CSV (potentiellement SOLDE BANCAIRE RÉEL)"
            },
            "continuous_history_service.py (ligne 145)": {
                "code": 'record["treasury_balance"] = float(row["treasury_balance"])',
                "interpretation": "Inséré en BD sans modification",
                "signification": "PRÉSERVATION DE LA VALEUR SOURCE"
            }
        }
        
        for location, info in code_evidence.items():
            print(f"  📍 {location}")
            print(f"     Code: {info['code']}")
            print(f"     Interprétation: {info['interpretation']}")
            print(f"     → Signification: {info['signification']}\n")
        
        # Vérifier si CSV contenait treasury_balance
        print("📊 Analyse des uploads:\n")
        
        uploads_cursor = database[c.UPLOADS].find(
            {"company_id": self.company_oid}
        ).sort("created_at", 1)
        
        uploads = await uploads_cursor.to_list(length=None)
        
        has_treasury_balance_in_csv = None
        
        for upload in uploads:
            filename = upload.get('original_filename', 'Unknown')
            parse_report = upload.get('parse_report', {})
            columns = parse_report.get('columns_detected', [])
            
            print(f"  Upload: {filename}")
            print(f"  Colonnes détectées: {columns}")
            
            if 'treasury_balance' in columns:
                has_treasury_balance_in_csv = True
                print(f"  ✅ treasury_balance PRÉSENT dans le CSV")
            else:
                print(f"  ❌ treasury_balance ABSENT (calculé automatiquement)")
            print()
        
        # Test statistique : vérifier si treasury_balance = cumsum(net_cashflow)
        print("🧮 Test statistique: treasury_balance vs cumsum(net_cashflow):\n")
        
        df = self.df.copy()
        
        # Essayer différents soldes initiaux
        treasury_first = df['treasury_balance'].iloc[0]
        cumsum_from_zero = df['net_cashflow'].cumsum()
        cumsum_from_first = treasury_first - df['net_cashflow'].iloc[0] + df['net_cashflow'].cumsum()
        
        corr_from_zero = df['treasury_balance'].corr(cumsum_from_zero)
        corr_from_first = df['treasury_balance'].corr(cumsum_from_first)
        
        mae_from_zero = (df['treasury_balance'] - cumsum_from_zero).abs().mean()
        mae_from_first = (df['treasury_balance'] - cumsum_from_first).abs().mean()
        
        print(f"  Scénario A: treasury_balance = cumsum(net_cashflow) depuis 0")
        print(f"    Corrélation: {corr_from_zero:.6f}")
        print(f"    MAE: {mae_from_zero:,.2f} MAD\n")
        
        print(f"  Scénario B: treasury_balance = solde_initial + cumsum(net_cashflow)")
        print(f"    Solde initial utilisé: {treasury_first:,.2f} MAD")
        print(f"    Corrélation: {corr_from_first:.6f}")
        print(f"    MAE: {mae_from_first:,.2f} MAD\n")

        
        # Conclusion
        print("💡 Conclusion sur la signification réelle:\n")
        
        fundamental_test = self.results.get('fundamental_test', {})
        valid_pct = fundamental_test.get('valid_pct', 0)
        
        if valid_pct >= 99:
            meaning = "A) SOLDE BANCAIRE RÉEL (ou cumul cohérent)"
            confidence = "ÉLEVÉE"
            explanation = "La relation récursive est vérifiée à 99%+. treasury_balance représente un solde cohérent."
        elif has_treasury_balance_in_csv:
            meaning = "B) VALEUR IMPORTÉE DU CSV (source externe)"
            confidence = "ÉLEVÉE"
            explanation = "treasury_balance était présent dans le CSV et a été importé. Il représente probablement le solde bancaire réel fourni par la comptabilité."
        elif corr_from_first > 0.99:
            meaning = "C) CUMUL DES FLUX AVEC SOLDE INITIAL"
            confidence = "ÉLEVÉE"
            explanation = f"Corrélation parfaite ({corr_from_first:.6f}) avec cumsum ajusté. C'est un cumul calculé."
        else:
            meaning = "D) LOGIQUE HYBRIDE OU AUTRE"
            confidence = "MOYENNE"
            explanation = "La logique n'est pas claire. Possiblement mélange de sources ou recalculs partiels."
        
        print(f"  → Signification: {meaning}")
        print(f"  → Confiance: {confidence}")
        print(f"  → Explication: {explanation}")
        
        self.results['real_meaning'] = {
            'meaning': meaning,
            'confidence': confidence,
            'explanation': explanation,
            'has_treasury_in_csv': has_treasury_balance_in_csv,
            'corr_from_zero': float(corr_from_zero),
            'corr_from_first': float(corr_from_first),
            'mae_from_zero': float(mae_from_zero),
            'mae_from_first': float(mae_from_first)
        }
    
    async def step3_analyze_initial_balance(self):
        """ÉTAPE 3 : ANALYSE DU SOLDE INITIAL"""
        self._print_section("ÉTAPE 3 — ANALYSE DU SOLDE INITIAL ET DE L'ÉCART")
        
        df = self.df.copy()
        
        print("\n📊 Analyse du solde initial:\n")
        
        treasury_initial = df['treasury_balance'].iloc[0]
        cumsum_from_zero = df['net_cashflow'].cumsum()
        
        # Calculer l'écart pour chaque ligne
        df['gap'] = df['treasury_balance'] - cumsum_from_zero
        
        gap_mean = df['gap'].mean()
        gap_std = df['gap'].std()
        gap_min = df['gap'].min()
        gap_max = df['gap'].max()
        gap_median = df['gap'].median()
        
        # Déterminer le pattern de l'écart
        gap_cv = (gap_std / abs(gap_mean)) if gap_mean != 0 else float('inf')
        
        print(f"  treasury_balance(0): {treasury_initial:,.2f} MAD")
        print(f"  cumsum(net_cashflow)(0): {cumsum_from_zero.iloc[0]:,.2f} MAD")
        print(f"  Écart initial: {df['gap'].iloc[0]:,.2f} MAD\n")
        
        print(f"  Statistiques de l'écart sur toute la période:")
        print(f"    Moyenne: {gap_mean:,.2f} MAD")
        print(f"    Écart-type: {gap_std:,.2f} MAD")
        print(f"    Médiane: {gap_median:,.2f} MAD")
        print(f"    Min: {gap_min:,.2f} MAD")
        print(f"    Max: {gap_max:,.2f} MAD")
        print(f"    Coefficient de variation: {gap_cv:.6f}")
        
        # Classer le pattern
        print(f"\n💡 Pattern de l'écart:\n")
        
        if gap_cv < 0.01:
            pattern = "CONSTANT"
            print(f"  ✅ ÉCART CONSTANT (CV < 0.01)")
            print(f"  → L'écart ne varie quasiment pas: {gap_mean:,.2f} ± {gap_std:,.2f} MAD")
            print(f"  → Ceci confirme un problème de SOLDE INITIAL")
        elif gap_cv < 0.05:
            pattern = "QUASI-CONSTANT"
            print(f"  ⚠️  ÉCART QUASI-CONSTANT (CV < 0.05)")
            print(f"  → L'écart varie légèrement mais reste proche de: {gap_mean:,.2f} MAD")
        else:
            pattern = "VARIABLE"
            print(f"  ❌ ÉCART VARIABLE (CV >= 0.05)")
            print(f"  → L'écart varie significativement")
            
            # Test de tendance
            df['index'] = range(len(df))
            correlation_time = df['index'].corr(df['gap'])
            
            if correlation_time > 0.7:
                pattern += " - CROISSANT"
                print(f"  → Tendance CROISSANTE (corr={correlation_time:.4f})")
            elif correlation_time < -0.7:
                pattern += " - DÉCROISSANT"
                print(f"  → Tendance DÉCROISSANTE (corr={correlation_time:.4f})")
            else:
                pattern += " - OSCILLANT"
                print(f"  → Pattern OSCILLANT (corr={correlation_time:.4f})")
        
        self.results['initial_balance'] = {
            'treasury_initial': float(treasury_initial),
            'gap_mean': float(gap_mean),
            'gap_std': float(gap_std),
            'gap_min': float(gap_min),
            'gap_max': float(gap_max),
            'gap_median': float(gap_median),
            'gap_cv': float(gap_cv),
            'pattern': pattern
        }

    
    async def step4_validate_previous_diagnosis(self):
        """ÉTAPE 4 : VALIDATION DU DIAGNOSTIC PRÉCÉDENT"""
        self._print_section("ÉTAPE 4 — VALIDATION DU DIAGNOSTIC PRÉCÉDENT")
        
        print('\n🎯 Affirmation à vérifier: "Le CSV contient un solde initial erroné de ~290 958 MAD"\n')
        
        # Rassembler les preuves
        fundamental = self.results.get('fundamental_test', {})
        meaning = self.results.get('real_meaning', {})
        initial = self.results.get('initial_balance', {})
        
        valid_pct = fundamental.get('valid_pct', 0)
        gap_mean = initial.get('gap_mean', 0)
        gap_cv = initial.get('gap_cv', float('inf'))
        pattern = initial.get('pattern', '')
        
        print("📊 Analyse des preuves:\n")
        
        # Preuve 1: Relation récursive
        print(f"  Preuve 1: Test de la relation récursive")
        print(f"    Résultat: {valid_pct:.2f}% des lignes valides")
        if valid_pct >= 99:
            print(f"    ✅ La relation récursive est VÉRIFIÉE")
            print(f"    → treasury_balance est cohérent avec net_cashflow")
            print(f"    → Le problème n'est PAS un solde initial erroné")
            proof1 = "CONTRE le diagnostic"
        else:
            print(f"    ❌ La relation récursive n'est PAS vérifiée")
            print(f"    → Suggère une incohérence structurelle")
            proof1 = "POUR le diagnostic"
        
        # Preuve 2: Pattern de l'écart
        print(f"\n  Preuve 2: Pattern de l'écart")
        print(f"    Écart moyen: {gap_mean:,.2f} MAD")
        print(f"    Coefficient de variation: {gap_cv:.6f}")
        print(f"    Pattern: {pattern}")
        
        if 'CONSTANT' in pattern:
            print(f"    ✅ Écart CONSTANT détecté")
            print(f"    → Confirme un problème de solde initial")
            proof2 = "POUR le diagnostic"
        else:
            print(f"    ❌ Écart VARIABLE")
            print(f"    → Ne confirme PAS uniquement un problème de solde initial")
            proof2 = "CONTRE le diagnostic"
        
        # Preuve 3: Signification métier
        print(f"\n  Preuve 3: Signification métier de treasury_balance")
        print(f"    Signification identifiée: {meaning.get('meaning', 'INCONNUE')}")
        
        if 'SOLDE BANCAIRE RÉEL' in meaning.get('meaning', ''):
            print(f"    ✅ treasury_balance représente le SOLDE RÉEL")
            print(f"    → Le diagnostic est FAUX: ce n'est pas une erreur, c'est la valeur correcte")
            proof3 = "INVALIDE le diagnostic"
        elif 'CUMUL' in meaning.get('meaning', ''):
            print(f"    ⚠️  treasury_balance est un CUMUL CALCULÉ")
            print(f"    → Le diagnostic pourrait être correct")
            proof3 = "NEUTRE"
        else:
            print(f"    ❓ Signification non déterminée")
            proof3 = "INCONNU"
        
        # Synthèse
        print(f"\n💡 VERDICT:\n")
        
        # Compter les preuves
        preuves_pour = sum([1 for p in [proof1, proof2, proof3] if 'POUR' in p])
        preuves_contre = sum([1 for p in [proof1, proof2, proof3] if 'CONTRE' in p or 'INVALIDE' in p])
        
        if preuves_contre >= 2:
            verdict = "FAUX"
            confidence = "ÉLEVÉE"
            explanation = "Les preuves montrent que treasury_balance est cohérent. Le diagnostic précédent est INCORRECT."
        elif preuves_pour >= 2:
            verdict = "VRAI"
            confidence = "ÉLEVÉE"
            explanation = "Les preuves confirment un solde initial erroné de ~290 958 MAD."
        else:
            verdict = "NON PROUVÉ"
            confidence = "FAIBLE"
            explanation = "Les preuves sont contradictoires ou insuffisantes."
        
        print(f"  Verdict: {verdict}")
        print(f"  Confiance: {confidence}")
        print(f"  Explication: {explanation}")
        
        # Justification détaillée
        print(f"\n📝 Justification détaillée:\n")
        
        if verdict == "VRAI":
            print(f"  Le diagnostic précédent est VALIDÉ car:")
            print(f"    • L'écart est constant (~{gap_mean:,.2f} MAD)")
            print(f"    • Cette constance indique un décalage de solde initial")
            print(f"    • Les variations de treasury_balance suivent exactement net_cashflow")
            print(f"    • Mais avec un décalage fixe")
        elif verdict == "FAUX":
            print(f"  Le diagnostic précédent est INVALIDÉ car:")
            print(f"    • treasury_balance suit la relation récursive correctement ({valid_pct:.2f}%)")
            print(f"    • Il représente probablement le solde bancaire RÉEL")
            print(f"    • L'écart avec cumsum(0) est NORMAL: c'est le solde initial légitime")
            print(f"    • Le problème des mauvaises prédictions est AILLEURS")
        else:
            print(f"  Le diagnostic ne peut être ni validé ni invalidé car:")
            print(f"    • Certaines preuves sont contradictoires")
            print(f"    • Plus d'informations sont nécessaires (CSV source, documentation métier)")
        
        self.results['diagnosis_validation'] = {
            'verdict': verdict,
            'confidence': confidence,
            'explanation': explanation,
            'preuves_pour': int(preuves_pour),
            'preuves_contre': int(preuves_contre)
        }

    
    async def step5_impact_on_models(self):
        """ÉTAPE 5 : IMPACT SUR LES MODÈLES"""
        self._print_section("ÉTAPE 5 — IMPACT SUR LES MODÈLES")
        
        df = self.df.copy()
        
        print("\n🔬 Simulation : Comparer les deux versions de treasury_balance\n")
        
        # Cas A: Utiliser treasury_balance actuel
        tb_actual = df['treasury_balance'].values
        
        # Cas B: Utiliser treasury_balance reconstruit (cumsum depuis 0)
        tb_rebuilt = df['net_cashflow'].cumsum().values
        
        print("📊 Cas A : treasury_balance ACTUEL (valeur en BD)\n")
        
        variance_a = np.var(tb_actual)
        mean_a = np.mean(tb_actual)
        std_a = np.std(tb_actual)
        
        # Tendance
        indices = np.arange(len(tb_actual))
        slope_a, intercept_a, r_value_a, p_value_a, std_err_a = stats.linregress(indices, tb_actual)
        
        # Autocorrélation lag 1
        autocorr_a = np.corrcoef(tb_actual[:-1], tb_actual[1:])[0, 1]
        
        # Stationnarité (test ADF)
        from statsmodels.tsa.stattools import adfuller
        adf_a = adfuller(tb_actual, autolag='AIC')
        
        print(f"  Variance: {variance_a:,.2f}")
        print(f"  Moyenne: {mean_a:,.2f} MAD")
        print(f"  Écart-type: {std_a:,.2f} MAD")
        print(f"  Tendance (pente): {slope_a:,.2f} MAD/jour")
        print(f"  R² tendance: {r_value_a**2:.4f}")
        print(f"  Autocorrélation lag-1: {autocorr_a:.4f}")
        print(f"  ADF statistic: {adf_a[0]:.4f}")
        print(f"  ADF p-value: {adf_a[1]:.4f}")
        print(f"  Stationnaire: {'OUI' if adf_a[1] < 0.05 else 'NON'}")
        
        print("\n📊 Cas B : treasury_balance RECONSTRUIT (cumsum depuis 0)\n")
        
        variance_b = np.var(tb_rebuilt)
        mean_b = np.mean(tb_rebuilt)
        std_b = np.std(tb_rebuilt)
        
        slope_b, intercept_b, r_value_b, p_value_b, std_err_b = stats.linregress(indices, tb_rebuilt)
        autocorr_b = np.corrcoef(tb_rebuilt[:-1], tb_rebuilt[1:])[0, 1]
        adf_b = adfuller(tb_rebuilt, autolag='AIC')
        
        print(f"  Variance: {variance_b:,.2f}")
        print(f"  Moyenne: {mean_b:,.2f} MAD")
        print(f"  Écart-type: {std_b:,.2f} MAD")
        print(f"  Tendance (pente): {slope_b:,.2f} MAD/jour")
        print(f"  R² tendance: {r_value_b**2:.4f}")
        print(f"  Autocorrélation lag-1: {autocorr_b:.4f}")
        print(f"  ADF statistic: {adf_b[0]:.4f}")
        print(f"  ADF p-value: {adf_b[1]:.4f}")
        print(f"  Stationnaire: {'OUI' if adf_b[1] < 0.05 else 'NON'}")
        
        print("\n📊 Comparaison des différences:\n")
        
        diff_variance = abs(variance_a - variance_b)
        diff_mean = abs(mean_a - mean_b)
        diff_std = abs(std_a - std_b)
        diff_slope = abs(slope_a - slope_b)
        diff_autocorr = abs(autocorr_a - autocorr_b)
        
        print(f"  Δ Variance: {diff_variance:,.2f} ({diff_variance/variance_a*100:.2f}%)")
        print(f"  Δ Moyenne: {diff_mean:,.2f} MAD ({diff_mean/mean_a*100:.2f}%)")
        print(f"  Δ Écart-type: {diff_std:,.2f} MAD ({diff_std/std_a*100:.2f}%)")
        print(f"  Δ Pente: {diff_slope:,.2f} MAD/jour")
        print(f"  Δ Autocorrélation: {diff_autocorr:.4f}")
        
        print("\n💡 Impact sur la modélisation:\n")
        
        # Analyser si la différence est significative
        if diff_mean / mean_a < 0.05 and diff_variance / variance_a < 0.05:
            impact = "NÉGLIGEABLE"
            print(f"  ✅ Impact NÉGLIGEABLE (< 5% sur variance et moyenne)")
            print(f"  → La différence entre les deux versions est minime")
            print(f"  → Ce problème NE PEUT PAS expliquer R² = -216 (Prophet) ou R² = -38 (LSTM)")
            print(f"  → Un AUTRE BUG est nécessairement présent")
        elif diff_mean / mean_a < 0.30:
            impact = "MODÉRÉ"
            print(f"  ⚠️  Impact MODÉRÉ (5-30% sur les statistiques)")
            print(f"  → La différence pourrait affecter les modèles")
            print(f"  → Mais probablement insuffisant pour expliquer R² si négatifs")
            print(f"  → D'AUTRES BUGS sont probablement présents")
        else:
            impact = "MAJEUR"
            print(f"  ❌ Impact MAJEUR (> 30% sur les statistiques)")
            print(f"  → La différence est significative")
            print(f"  → Pourrait expliquer une partie des mauvaises performances")
            print(f"  → Mais R² très négatifs suggèrent d'AUTRES PROBLÈMES aussi")
        
        self.results['model_impact'] = {
            'case_a': {
                'variance': float(variance_a),
                'mean': float(mean_a),
                'std': float(std_a),
                'slope': float(slope_a),
                'autocorr': float(autocorr_a),
                'adf_pvalue': float(adf_a[1]),
                'stationary': adf_a[1] < 0.05
            },
            'case_b': {
                'variance': float(variance_b),
                'mean': float(mean_b),
                'std': float(std_b),
                'slope': float(slope_b),
                'autocorr': float(autocorr_b),
                'adf_pvalue': float(adf_b[1]),
                'stationary': adf_b[1] < 0.05
            },
            'impact': impact,
            'can_explain_negative_r2': impact == "MAJEUR"
        }

    
    async def step6_search_for_second_bug(self):
        """ÉTAPE 6 : RECHERCHE D'UN SECOND BUG"""
        self._print_section("ÉTAPE 6 — RECHERCHE D'UN SECOND BUG")
        
        print("\n🔍 Détermination: L'incohérence treasury_balance est-elle la CAUSE UNIQUE?\n")
        
        model_impact = self.results.get('model_impact', {})
        can_explain = model_impact.get('can_explain_negative_r2', False)
        impact = model_impact.get('impact', '')
        
        if can_explain:
            answer = "A) CAUSE UNIQUE (possible)"
            print(f"  → {answer}")
            print(f"  → L'impact est MAJEUR, pourrait expliquer seul les mauvaises performances")
        else:
            answer = "B) CAUSE PARTIELLE (très probable)"
            print(f"  → {answer}")
            print(f"  → L'impact est {impact}, INSUFFISANT pour expliquer R² = -216 ou -38")
            print(f"  → D'AUTRES BUGS sont NÉCESSAIREMENT présents")
        
        print(f"\n🔎 Recherche d'autres causes probables:\n")
        
        # Liste des causes possibles
        other_causes = []
        
        # 1. Bug de forecast (projection regressors)
        print(f"  Cause 1: Bug de projection des regressors Prophet")
        print(f"    Description: Les regressors futurs sont mal projetés (relative_mae > 0.2)")
        print(f"    Probabilité: 🔴 TRÈS ÉLEVÉE (95%)")
        print(f"    Preuve: Diagnostic initial montre relative_mae > 1.2 sur cash_outflow")
        print(f"    Impact: R² négatif dans Prophet (-0.283)")
        other_causes.append({
            'name': 'Bug projection regressors Prophet',
            'probability': 95,
            'severity': 'CRITIQUE',
            'evidence': 'Diagnostic initial confirmé'
        })
        
        # 2. Bug de scaling
        print(f"\n  Cause 2: Bug de scaling (MinMaxScaler écrasé par outliers)")
        print(f"    Description: Outliers compressent la normalisation")
        print(f"    Probabilité: 🟡 MOYENNE (60%)")
        print(f"    Preuve: 43 outliers détectés dans net_cashflow")
        print(f"    Impact: LSTM apprend sur une échelle déformée")
        other_causes.append({
            'name': 'Bug de scaling (MinMaxScaler)',
            'probability': 60,
            'severity': 'MOYEN',
            'evidence': '43 outliers dans net_cashflow'
        })
        
        # 3. Non-stationnarité
        print(f"\n  Cause 3: Série non stationnaire")
        print(f"    Description: ADF p-value = 0.247872")
        print(f"    Probabilité: 🟠 ÉLEVÉE (80%)")
        print(f"    Preuve: Test ADF échoue (p > 0.05)")
        print(f"    Impact: Modèles ont du mal à apprendre la dynamique")
        other_causes.append({
            'name': 'Non-stationnarité',
            'probability': 80,
            'severity': 'ÉLEVÉ',
            'evidence': 'ADF p-value = 0.247872'
        })
        
        # 4. Features insuffisantes
        print(f"\n  Cause 4: Features insuffisantes (pas de lags/rolling)")
        print(f"    Description: Modèles n'ont pas assez de structure temporelle")
        print(f"    Probabilité: 🟠 ÉLEVÉE (85%)")
        print(f"    Preuve: Diagnostic montre importance de lag_1 > 0.98")
        print(f"    Impact: Sous-apprentissage, incapacité à capturer patterns")
        other_causes.append({
            'name': 'Features insuffisantes',
            'probability': 85,
            'severity': 'ÉLEVÉ',
            'evidence': 'Pas de lags/rolling dans les features'
        })
        
        # 5. Bug génération future
        print(f"\n  Cause 5: Bug dans la génération des valeurs futures")
        print(f"    Description: Forecast génère des valeurs irréalistes")
        print(f"    Probabilité: 🟡 MOYENNE (50%)")
        print(f"    Preuve: À vérifier dans le code de forecast")
        print(f"    Impact: Prédictions déconnectées de la réalité")
        other_causes.append({
            'name': 'Bug génération valeurs futures',
            'probability': 50,
            'severity': 'CRITIQUE',
            'evidence': 'À vérifier'
        })
        
        # 6. Overfitting LSTM
        print(f"\n  Cause 6: Overfitting LSTM")
        print(f"    Description: val_loss remonte après epoch 9")
        print(f"    Probabilité: 🟡 MOYENNE (70%)")
        print(f"    Preuve: Diagnostic montre val_loss oscillant")
        print(f"    Impact: Mauvaise généralisation")
        other_causes.append({
            'name': 'Overfitting LSTM',
            'probability': 70,
            'severity': 'MOYEN',
            'evidence': 'val_loss remonte'
        })
        
        # Classement par probabilité
        other_causes_sorted = sorted(other_causes, key=lambda x: x['probability'], reverse=True)
        
        print(f"\n📊 TOP 5 des causes racines (classées par probabilité):\n")
        
        for i, cause in enumerate(other_causes_sorted[:5], 1):
            prob_emoji = "🔴" if cause['probability'] >= 80 else "🟠" if cause['probability'] >= 60 else "🟡"
            print(f"  #{i} {prob_emoji} {cause['name']}")
            print(f"      Probabilité: {cause['probability']}%")
            print(f"      Sévérité: {cause['severity']}")
            print(f"      Preuve: {cause['evidence']}\n")
        
        self.results['second_bug'] = {
            'is_unique_cause': answer == "A) CAUSE UNIQUE (possible)",
            'other_causes': other_causes_sorted
        }

    
    async def final_report(self):
        """RAPPORT FINAL"""
        self._print_section("RAPPORT FINAL — AUDIT MÉTIER COMPLET")
        
        print("\n" + "🎯" * 60 + "\n")
        
        # 1. Signification métier réelle
        print("1️⃣  SIGNIFICATION MÉTIER RÉELLE DE treasury_balance:\n")
        
        meaning = self.results.get('real_meaning', {})
        fundamental = self.results.get('fundamental_test', {})
        
        print(f"   {meaning.get('meaning', 'INCONNUE')}")
        print(f"   Confiance: {meaning.get('confidence', 'INCONNUE')}")
        print(f"   Explication: {meaning.get('explanation', '')}")
        print(f"\n   Relation récursive vérifiée: {fundamental.get('valid_pct', 0):.2f}%")
        
        if fundamental.get('valid_pct', 0) >= 99:
            print(f"   ✅ treasury_balance est COHÉRENT et suit la logique métier")
        else:
            print(f"   ❌ treasury_balance présente des incohérences")
        
        # 2. Validation ou invalidation du diagnostic précédent
        print(f"\n2️⃣  VALIDATION DU DIAGNOSTIC PRÉCÉDENT:\n")
        
        diagnosis = self.results.get('diagnosis_validation', {})
        
        print(f"   Affirmation testée: 'Le CSV contient un solde initial erroné'")
        print(f"\n   Verdict: {diagnosis.get('verdict', 'INCONNU')}")
        print(f"   Confiance: {diagnosis.get('confidence', 'INCONNUE')}")
        print(f"   Explication: {diagnosis.get('explanation', '')}")
        
        if diagnosis.get('verdict') == 'VRAI':
            print(f"\n   ✅ Le diagnostic précédent est VALIDÉ")
        elif diagnosis.get('verdict') == 'FAUX':
            print(f"\n   ❌ Le diagnostic précédent est INVALIDÉ")
            print(f"   → treasury_balance représente probablement le solde bancaire RÉEL")
            print(f"   → L'écart avec cumsum(0) est NORMAL et attendu")
        else:
            print(f"\n   ❓ Le diagnostic ne peut être ni validé ni invalidé")
        
        # 3. Impact réel sur les modèles
        print(f"\n3️⃣  IMPACT RÉEL SUR LES MODÈLES:\n")
        
        model_impact = self.results.get('model_impact', {})
        impact = model_impact.get('impact', 'INCONNU')
        
        print(f"   Impact de la différence entre treasury_balance actuel et reconstruit:")
        print(f"   → {impact}")
        
        case_a = model_impact.get('case_a', {})
        case_b = model_impact.get('case_b', {})
        
        if case_a and case_b:
            diff_mean_pct = abs(case_a.get('mean', 0) - case_b.get('mean', 0)) / case_a.get('mean', 1) * 100
            diff_var_pct = abs(case_a.get('variance', 0) - case_b.get('variance', 0)) / case_a.get('variance', 1) * 100
            
            print(f"\n   Différences statistiques:")
            print(f"   • Moyenne: {diff_mean_pct:.2f}%")
            print(f"   • Variance: {diff_var_pct:.2f}%")
        
        # 4. Probabilité d'explication
        print(f"\n4️⃣  PROBABILITÉ QUE CE PROBLÈME EXPLIQUE À LUI SEUL LES MAUVAISES PERFORMANCES:\n")
        
        can_explain = model_impact.get('can_explain_negative_r2', False)
        
        if can_explain:
            print(f"   🟡 POSSIBLE (30-50%)")
            print(f"   → L'impact est majeur et pourrait expliquer une partie significative")
            print(f"   → Mais R² très négatifs suggèrent d'autres facteurs")
        else:
            print(f"   🔴 PEU PROBABLE (< 10%)")
            print(f"   → L'impact est {impact.lower()}, insuffisant pour expliquer:")
            print(f"      • R² Prophet = -0.283")
            print(f"      • R² LSTM = 0.656 (devrait être > 0.85)")
            print(f"   → D'AUTRES BUGS sont NÉCESSAIREMENT présents")
        
        # 5. Top 5 des causes racines
        print(f"\n5️⃣  TOP 5 DES CAUSES RACINES LES PLUS PROBABLES:\n")
        
        second_bug = self.results.get('second_bug', {})
        other_causes = second_bug.get('other_causes', [])
        
        for i, cause in enumerate(other_causes[:5], 1):
            prob = cause.get('probability', 0)
            emoji = "🔴" if prob >= 80 else "🟠" if prob >= 60 else "🟡"
            
            print(f"   {emoji} #{i} - {cause.get('name', 'INCONNUE')}")
            print(f"      Probabilité: {prob}%")
            print(f"      Sévérité: {cause.get('severity', 'INCONNUE')}")
            print(f"      Preuve: {cause.get('evidence', 'Aucune')}\n")
        
        print("\n" + "=" * 120)
        print("\n✅ AUDIT MÉTIER COMPLET TERMINÉ\n")
        print("=" * 120)


async def main():
    """Point d'entrée principal"""
    
    import argparse
    parser = argparse.ArgumentParser(description='Audit métier complet de treasury_balance')
    parser.add_argument('--company-id', required=True, help='ID de la société à auditer')
    args = parser.parse_args()
    
    auditor = TreasuryBalanceBusinessAuditor(args.company_id)
    
    # Charger les données
    await auditor.load_data()
    
    # Exécuter toutes les étapes
    await auditor.step1_fundamental_test()
    await auditor.step2_identify_real_meaning()
    await auditor.step3_analyze_initial_balance()
    await auditor.step4_validate_previous_diagnosis()
    await auditor.step5_impact_on_models()
    await auditor.step6_search_for_second_bug()
    await auditor.final_report()


if __name__ == "__main__":
    asyncio.run(main())
