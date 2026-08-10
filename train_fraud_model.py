import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import os

print("🚀 Training ML Fraud Detection Model")
print("="*50)

# ============================================
# Step 1 — Load Kaggle dataset
# ============================================
print("\n📂 Loading creditcard.csv...")
df = pd.read_csv('creditcard.csv')
print(f"✅ Loaded {len(df):,} transactions")
print(f"   Fraud cases: {df['Class'].sum():,}")
print(f"   Normal cases: {(df['Class']==0).sum():,}")
print(f"   Fraud rate: {df['Class'].mean()*100:.2f}%")

# ============================================
# Step 2 — Prepare features
# ============================================
print("\n🔧 Preparing features...")

# Features and target
X = df.drop('Class', axis=1)
y = df['Class']

# Scale Amount and Time
scaler_amount = StandardScaler()
scaler_time = StandardScaler()
X['Amount'] = scaler_amount.fit_transform(X[['Amount']])
X['Time'] = scaler_time.fit_transform(X[['Time']])

print(f"✅ Features prepared: {X.shape[1]} features")

# ============================================
# Step 3 — Handle class imbalance
# ============================================
print("\n⚖️ Handling class imbalance...")

# Undersample majority class for faster training
fraud = df[df['Class']==1]
normal = df[df['Class']==0].sample(n=len(fraud)*10, random_state=42)
balanced = pd.concat([fraud, normal])

X_balanced = balanced.drop('Class', axis=1)
y_balanced = balanced['Class']

X_balanced['Amount'] = scaler_amount.transform(X_balanced[['Amount']])
X_balanced['Time'] = scaler_time.transform(X_balanced[['Time']])

print(f"✅ Balanced dataset: {len(balanced):,} transactions")
print(f"   Fraud: {y_balanced.sum():,}")
print(f"   Normal: {(y_balanced==0).sum():,}")

# ============================================
# Step 4 — Split data
# ============================================
print("\n✂️ Splitting into train/test...")
X_train, X_test, y_train, y_test = train_test_split(
    X_balanced, y_balanced,
    test_size=0.2,
    random_state=42,
    stratify=y_balanced
)
print(f"✅ Training set: {len(X_train):,} transactions")
print(f"✅ Test set: {len(X_test):,} transactions")

# ============================================
# Step 5 — Train Random Forest
# ============================================
print("\n🌲 Training Random Forest model...")
print("   This takes about 1-2 minutes...")

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'
)

model.fit(X_train, y_train)
print("✅ Model trained!")

# ============================================
# Step 6 — Evaluate model
# ============================================
print("\n📊 Evaluating model...")
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\nClassification Report:")
print(classification_report(y_test, y_pred, 
    target_names=['Normal', 'Fraud']))

auc = roc_auc_score(y_test, y_prob)
print(f"AUC-ROC Score: {auc:.4f}")

cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"True Negatives:  {cm[0][0]:,} (correctly identified normal)")
print(f"False Positives: {cm[0][1]:,} (normal flagged as fraud)")
print(f"False Negatives: {cm[1][0]:,} (fraud missed)")
print(f"True Positives:  {cm[1][1]:,} (correctly caught fraud)")

accuracy = (cm[0][0] + cm[1][1]) / cm.sum() * 100
print(f"\n🎯 Overall Accuracy: {accuracy:.2f}%")

# ============================================
# Step 7 — Save model
# ============================================
print("\n💾 Saving model...")
joblib.dump(model, 'fraud_model.pkl')
joblib.dump(scaler_amount, 'scaler_amount.pkl')
joblib.dump(scaler_time, 'scaler_time.pkl')
joblib.dump(list(X.columns), 'feature_names.pkl')

print("✅ Saved fraud_model.pkl")
print("✅ Saved scaler.pkl")
print("✅ Saved feature_names.pkl")

print("\n" + "="*50)
print("🎉 ML Model training complete!")
print(f"   Model: Random Forest (100 trees)")
print(f"   Accuracy: {accuracy:.2f}%")
print(f"   AUC-ROC: {auc:.4f}")
print(f"   Trained on: 284,807 real transactions")
print("="*50)
