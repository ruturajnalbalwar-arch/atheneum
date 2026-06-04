# 🚀 ATHENEUM — Quick Start Guide

Get started in 5 minutes.

---

## Option 1: Website Only (Recommended for First-Time Users)

**No setup needed. Just:**

```bash
git clone https://github.com/yourusername/atheneum.git
cd atheneum
npm install
npm run dev
```

Then open: **http://localhost:8000**

You'll see the website with links to all 4 live councils. Click any link to use them immediately.

---

## Option 2: Run a Council Locally (For Developers)

### Prerequisites

- Python 3.8+
- Free API keys (takes 2 minutes):
  - Groq: https://console.groq.com
  - Cerebras: https://cloud.cerebras.ai

### Setup

```bash
# Navigate to a council
cd atheneum/councils/general

# Create virtual environment
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Add your API keys to .env
nano .env                         # Or use your favorite editor
# Add your keys and save

# Run the council
python app.py
```

Then open: **http://localhost:7860**

---

## Option 3: Deploy Your Own Version (For Production)

See `DEPLOYMENT.md` in the `docs/` folder.

---

## Which Council to Run?

| Path | Purpose | Best For |
|------|---------|----------|
| `councils/general/` | Ask any question | Everyone |
| `councils/paideia/` | Learn concepts deeply | Students |
| `councils/lex/` | Legal analysis | Legal questions |
| `councils/medica/` | Health questions | Medical info |

---

## Troubleshooting

### "npm: command not found"
Install Node.js from nodejs.org, then try again.

### "python: command not found"
Install Python from python.org, then try again.

### "ModuleNotFoundError"
Make sure you've run `pip install -r requirements.txt` and are using the virtual environment.

### "GROQ_API_KEY not found"
Create `.env` file and add your keys:
```bash
cp .env.example .env
nano .env
```

### "Port already in use"
Change port in command:
```bash
npm run dev -- --port 8001
# or
python app.py (automatically picks available port)
```

---

## Next Steps

1. **Try the website first** → `npm install && npm run dev`
2. **Explore the councils** → Visit the live spaces
3. **Read the docs** → See `README.md` and `docs/` folder
4. **Deploy your own** → Follow `DEPLOYMENT.md`

---

**Questions? Check FAQ.md or open an issue on GitHub.**
