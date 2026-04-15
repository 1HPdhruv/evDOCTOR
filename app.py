import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from supabase import create_client

# --- Supabase setup ---
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# --- Load dataset ---
df = pd.read_csv("EV_DTC_Dataset.csv")
X = df["TrainingText"]
y = df["Description"]

# --- Train model ---
model = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english")),
    ("nb", MultinomialNB())
])
model.fit(X, y)

# --- Prediction ---
def predict_fault(symptom_text):
    issue = model.predict([symptom_text])[0]
    row = df[df["Description"] == issue].iloc[0]
    return {
        "Predicted Issue": issue,
        "Suggested Fix": row["Solution"]
    }

# --- Save search to DB ---
def save_search(symptom, issue, fix):
    supabase.table("search_history").insert({
        "symptom_text": symptom,
        "predicted_issue": issue,
        "suggested_fix": fix
    }).execute()

# --- Save feedback to DB ---
def save_feedback(symptom, issue, helpful, comment):
    supabase.table("feedback").insert({
        "symptom_text": symptom,
        "predicted_issue": issue,
        "was_helpful": helpful,
        "comment": comment
    }).execute()

# --- UI ---
st.title("evDOCTOR — EV Fault Predictor")
st.write("Describe your EV symptoms and get an instant diagnosis.")

user_input = st.text_area("Enter symptoms:", "")

if st.button("Predict"):
    if user_input.strip():
        result = predict_fault(user_input)
        save_search(user_input, result["Predicted Issue"], result["Suggested Fix"])

        st.success("Prediction Complete")
        st.subheader("Diagnosis")
        st.write(f"**Issue:** {result['Predicted Issue']}")
        st.write(f"**Suggested Fix:** {result['Suggested Fix']}")

        st.divider()
        st.subheader("Was this helpful?")
        col1, col2 = st.columns(2)
        with col1:
            helpful = st.radio("Feedback", ["Yes", "No"], horizontal=True)
        comment = st.text_input("Any additional comments? (optional)")

        if st.button("Submit Feedback"):
            save_feedback(user_input, result["Predicted Issue"], helpful == "Yes", comment)
            st.success("Thank you for your feedback!")
    else:
        st.warning("Please enter some symptoms first.")

# --- Search History Viewer ---
with st.expander("View Recent Searches"):
    history = supabase.table("search_history").select("*").order("searched_at", desc=True).limit(10).execute()
    if history.data:
        st.dataframe(pd.DataFrame(history.data))
    else:
        st.write("No searches yet.")
