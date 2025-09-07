import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Load dataset
df = pd.read_csv("EV_DTC_Dataset.csv")

# Features and labels
X = df["TrainingText"]
y = df["Description"]

# Create and train model
model = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english")),
    ("nb", MultinomialNB())
])
model.fit(X, y)

# --- Prediction Function ---
def predict_fault(symptom_text):
    issue = model.predict([symptom_text])[0]
    row = df[df["Description"] == issue].iloc[0]
    return {
        "Predicted Issue": issue,
        "Suggested Fix": row["Solution"]
    }

# --- Streamlit UI ---
st.title("EV Fault Predictor")
st.write("Enter EV fault symptoms to predict the issue, diagnostic code, and fix.")

user_input = st.text_area("Enter symptoms:", "")

if st.button("Predict"):
    if user_input.strip():
        result = predict_fault(user_input)
        st.success("✅ Prediction Complete")

        st.subheader("Main Prediction")
        st.write(f"**Issue:** {result['Predicted Issue']}")
        st.write(f"**Suggested Fix:** {result['Suggested Fix']}")
    else:
        st.warning("⚠️ Please enter some symptoms first.")
