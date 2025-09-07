# 🔧 EV Fault Predictor

Ever wondered what’s wrong with your EV when it starts showing strange behavior?  
This project is a **simple AI-powered assistant** that predicts possible **electric vehicle (EV) faults** based on the symptoms you type in.  

It uses a dataset of diagnostic trouble codes (DTCs), their descriptions, and solutions — and gives you the most likely fault along with a fix. 🚗⚡

---

## ✨ What it can do
- ✅ Predicts the **most likely EV issue** from your input symptoms  
- 🔢 Shows the related **diagnostic code (DTC)**  
- 🛠️ Suggests the **fix/solution** you can try  
- 🌐 Runs as a **web app** (built with Streamlit)  
- 📈 Easy to extend by adding more EV/Hybrid fault codes  

---

## 📂 Project Files
ev_fault_assistant/
│
├── EV_DTC_Dataset.csv # The fault dataset (codes, issues, fixes, keywords)
├── app.py # Streamlit web app
├── code.py # CLI-based version
└── README.md # This file 🙂

---

## 🚀 How to Run

### 1. Clone this repo
git clone https://github.com/your-username/ev-fault-predictor.git
cd ev-fault-predictor

###  2. Run the web app
streamlit run app.py (In terminal or command prompt)
Open http://localhost:8501 in your browser, and you’re ready to go! 🎉

🛠️ Built With
Python 🐍
Pandas (for handling the dataset)
Scikit-learn (for training the Naive Bayes model)
Streamlit (for the web app)

🤝 Contributing
Want to make this smarter? Add more fault codes, improve the model, or polish the UI.
Pull requests are always welcome 🚀
