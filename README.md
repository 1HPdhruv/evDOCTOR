# evDOCTOR — EV Fault Predictor

Live App: [https://ev-doctor.streamlit.app/](https://ev-doctor.streamlit.app/)

> An AI-powered assistant that diagnoses electric vehicle faults from your symptoms — instantly.

---

## What is evDOCTOR?

When your EV throws a warning or starts behaving oddly, figuring out what's wrong can be overwhelming.
**evDOCTOR** takes the symptoms you describe in plain English and predicts the most likely fault,
shows you the diagnostic trouble code (DTC), and tells you exactly how to fix it.

No technical jargon. No guesswork. Just answers.

---

## Features

- **AI-Powered Diagnosis** — Uses a Naive Bayes model trained on real EV diagnostic codes
- **DTC Lookup** — Maps your symptoms to standard diagnostic trouble codes
- **Fix Suggestions** — Gives you a clear, actionable solution for each fault
- **Instant Results** — No sign-up, no waiting, just type and predict
- **Runs in the Browser** — Built with Streamlit, works on any device

---

## Try it Live

[https://ev-doctor.streamlit.app/](https://ev-doctor.streamlit.app/)

Type in symptoms like:
- *"battery not charging, range dropped suddenly"*
- *"motor making noise at high speed"*
- *"regenerative braking not working"*

evDOCTOR will predict the fault and tell you how to fix it.

---

## Run It Locally

### 1. Clone the repo
```bash
git clone https://github.com/1HPdhruv/evDOCTOR.git
cd evDOCTOR
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the app
```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Project Structure

evDOCTOR/
│
├── EV_DTC_Dataset.csv     # Fault dataset (codes, descriptions, fixes, keywords)
├── app.py                 # Streamlit web app
├── code.py                # CLI version
├── requirements.txt       # Python dependencies
└── README.md              # This file

---

## Built With

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Pandas | Dataset handling |
| Scikit-learn | TF-IDF + Naive Bayes model |
| Streamlit | Web app framework |

---

## Roadmap

- [ ] Add support for more EV brands and models
- [ ] Improve model accuracy with a larger dataset
- [ ] Add confidence scores to predictions
- [ ] Support image/OBD scan input
- [ ] Multi-language support

---

## Contributing

Got more fault codes? Want to improve the model or the UI?
Pull requests are welcome. Let's build the best free EV diagnostic tool out there.

1. Fork the repo
2. Create a branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push and open a Pull Request

---

## License

This project is open source and available under the [MIT License](LICENSE).

---

Made by [Dhruv](https://github.com/1HPdhruv)
