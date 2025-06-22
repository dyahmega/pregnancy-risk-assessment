
# ======================================================================
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.tree import DecisionTreeClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
import pickle
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
import joblib

# Impor fungsi yang dibutuhkan dari utils.py
from utils import preprocess_input_for_pipeline

print("Memulai proses training model pipeline...")

# --- FUNGSI PEMBUATAN TARGET (LOGIKA BISNIS ANDA) ---
def realistic_labeling(df_cleaned):
    df = df_cleaned.copy()
    np.random.seed(42)
    labels, scores = [], []
    for _, row in df.iterrows():
        score = 2
        if float(row['umur_ibu']) < 18 or float(row['umur_ibu']) > 35: score += 4
        if float(row['gravida']) >= 4: score += 4
        if float(row['umur_kehamilan']) > 42: score += 4
        if float(row['tinggi_badan']) < 145: score += 4
        if row['penyakit_anemia'] == 'Positif': score += 4
        if row['hasil_tes_VDRL'] == 'Positif': score += 4
        if row['hasil_tes_HbsAg'] == 'Positif': score += 4
        if row['kategori_tekanan_darah'] == 'Hipertensi Stage 1': score += 6
        if row['kategori_tekanan_darah'] == 'Hipertensi Stage 2': score += 8
        if row['posisi_janin'] == 'Abnormal': score += 8
        uncertainty_magnitude = np.random.choice([-1, 0, 1], p=[0.15, 0.70, 0.15])
        score += uncertainty_magnitude
        score = max(2, score)
        scores.append(score)
        if score <= 5: labels.append('KRR')
        elif score <= 10: labels.append('KRT')
        else: labels.append('KRST')
    df['skor_risiko'] = scores
    df['label_risiko'] = labels
    return df

# --- PROSES UTAMA ---
# 1. Muat data mentah
df_raw = pd.read_csv('pregnancy-dataset.csv')
print("Dataset dimuat.")

# 2. Lakukan cleaning dan feature engineering menggunakan fungsi dari utils
df_cleaned = preprocess_input_for_pipeline(df_raw.copy())
print("Data cleaning & feature engineering selesai.")

# 3. Buat variabel target
df_with_target = realistic_labeling(df_cleaned)
y = df_with_target['label_risiko']
print("\n" + "="*40)
print("DISTRIBUSI LABEL YANG DIHASILKAN:")
print(y.value_counts())
print("="*40 + "\n")

# 4. Siapkan Fitur (X) MENTAH untuk pipeline
X_raw = df_with_target.drop(columns=['label_risiko', 'skor_risiko', 'tekanan_sistolik', 'tekanan_diastolik'], errors='ignore')
print(f"Fitur mentah (X_raw) yang akan masuk pipeline: {X_raw.columns.tolist()}")

# 5. DEFINISIKAN PIPELINE LENGKAP
numeric_features = ['umur_ibu', 'gravida', 'umur_kehamilan', 'tinggi_badan']
categorical_features = ['penyakit_anemia', 'posisi_janin', 'hasil_tes_VDRL', 'hasil_tes_HbsAg', 'kategori_tekanan_darah']
preprocessor = ColumnTransformer(
    transformers=[
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', drop='if_binary'), categorical_features)
    ],
    remainder='drop'
)
full_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('smote', SMOTE(random_state=42, k_neighbors=5)),
    ('classifier', DecisionTreeClassifier(random_state=42))
])

# 6. Split data
X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=0.2, random_state=42, stratify=y)

# 7. Setup dan jalankan GridSearchCV
param_grid = {
    'classifier__max_depth': [3, 5, 7, 10],
    'classifier__min_samples_split': [10, 20, 30],
    'classifier__criterion': ['gini', 'entropy']
}
skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
grid_search = GridSearchCV(estimator=full_pipeline, param_grid=param_grid, cv=skf, scoring='f1_macro', n_jobs=1, verbose=1)

print("\nMemulai GridSearchCV dengan full pipeline...")
grid_search.fit(X_train, y_train)
print("GridSearchCV selesai.")

# 8. Simpan Hasil Terbaik
best_full_pipeline = grid_search.best_estimator_
print(f"\nParameter terbaik: {grid_search.best_params_}")
print(f"Skor F1-Macro CV terbaik: {grid_search.best_score_:.4f}")

# --- LANGKAH BARU: EKSTRAK NAMA FITUR DAN SIMPAN ---
# Ambil nama fitur setelah preprocessing (setelah one-hot encoding)
# Ini adalah nama-nama kolom yang sebenarnya dilihat oleh model
feature_names_transformed = best_full_pipeline.named_steps['preprocessor'].get_feature_names_out()
joblib.dump(feature_names_transformed.tolist(), 'feature_names.pkl')
print("Nama fitur yang sudah ditransformasi berhasil disimpan.")
# ----------------------------------------------------

# Simpan pipeline lengkap
with open('pregnancy_risk_full_pipeline.pkl', 'wb') as f:
    pickle.dump(best_full_pipeline, f)
    
print("\nPipeline LENGKAP berhasil disimpan sebagai 'pregnancy_risk_full_pipeline.pkl'.")
print("Proses training selesai!")