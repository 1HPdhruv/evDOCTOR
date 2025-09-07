import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# Load dataset
df = pd.read_csv("EV_DTC_Dataset.csv")

# Features and labels
X = df["TrainingText"]
y = df["Description"]

# Build model (Logistic Regression → better than Naive Bayes for text)
model = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english", ngram_range=(1,2))),
    ("clf", LogisticRegression(max_iter=500))
])

# Train model
model.fit(X, y)

# --- Prediction Function (best single prediction) ---
def predict_fault(symptom_text):
    issue = model.predict([symptom_text])[0]        # best prediction
    prob = max(model.predict_proba([symptom_text])[0])  # confidence score

    # Find first matching row for this issue
    row = df[df["Description"] == issue].iloc[0]

    return {
        "Predicted Issue": issue,
        "Probability": round(prob, 3),
        "Diagnostic Code": row["Code"],
        "Suggested Fix": row["Solution"]
    }

# --- Interactive CLI ---
print("EV Fault Predictor")
print("Type your symptoms (or 'quit' to exit)\n")

while True:
    user_input = input("Enter symptoms: ").strip()
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye 👋")
        break

    result = predict_fault(user_input)

    print("\nBest Prediction:")
    for k, v in result.items():
        print(f"{k}: {v}")
    print("-" * 60)
