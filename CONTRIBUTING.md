# Contributing to Atheneum

We welcome contributions! Here's how to help.

---

## 🎯 Ways to Contribute

### 1. Report Bugs
Found an issue? Open a GitHub issue with:
- What happened
- What you expected
- Steps to reproduce
- Your environment (OS, Python version, etc.)

### 2. Suggest Features
Have an idea? Open a GitHub discussion with:
- The feature idea
- Why it would be useful
- Any examples or references

### 3. Improve Documentation
- Fix typos
- Clarify instructions
- Add examples
- Write FAQs

### 4. Create New Councils
Extend Atheneum with new domain-specific councils:

**Steps:**
1. Fork the repo
2. Copy `councils/general/` to `councils/newcounsel/`
3. Modify the 4 educator personas
4. Update the prompts for your domain
5. Test locally with your API keys
6. Submit a pull request

**Example:** Finance Council with Bull, Bear, Academic, Practitioner personas

### 5. Improve Code
- Fix bugs
- Optimize performance
- Refactor for clarity
- Add error handling

### 6. Add Tests
Create tests for:
- API responses
- Response quality
- Stage execution
- Rate limit handling

---

## 📋 Before You Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create** a branch: `git checkout -b feature/your-idea`
4. **Make** your changes
5. **Test** locally
6. **Commit** with clear messages: `git commit -m "Add feature: description"`
7. **Push** to your fork
8. **Open** a pull request

---

## 🛠️ Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/atheneum.git
cd atheneum

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r councils/general/requirements.txt

# Copy .env template and add API keys
cp .env.example .env
nano .env  # Add your Groq and Cerebras keys

# Run a council to test
cd councils/general
python app.py
```

---

## 📝 Code Style

- **Python**: Follow PEP 8
- **HTML/CSS**: Use meaningful class names
- **JavaScript**: Use clear variable names
- **Documentation**: Write clear, helpful comments

Example:
```python
# Good: Clear, concise, explains purpose
def call_model(educator, prompt, max_tokens=400):
    """Call an AI model with proper retry logic."""
    
# Bad: Unclear
def cm(e, p, m=400):
    pass
```

---

## 🧪 Testing Your Changes

Before submitting:

```bash
# Test website
npm install
npm run dev
# Open http://localhost:8000 and click links

# Test Python app
cd councils/general
python app.py
# Ask a test question, verify all 5 stages work

# Test fresh setup
cd ..
rm -rf test_clone
git clone . test_clone  # Clone to new folder
cd test_clone
pip install -r councils/general/requirements.txt
cp .env.example .env
# [Add API keys to .env]
python councils/general/app.py
# If this works, setup is good!
```

---

## 📚 Commit Message Format

```
Type: Brief description (50 chars max)

Optional longer explanation of what and why
(not "how" - that's in the code)
```

**Types:**
- `fix:` Bug fixes
- `feat:` New features
- `docs:` Documentation
- `refactor:` Code improvements
- `test:` Tests
- `perf:` Performance improvements

**Examples:**
```
fix: Handle rate limit retries properly
feat: Add finance council with Bull/Bear personas
docs: Clarify API key setup in README
```

---

## 🚀 Pull Request Process

1. **Description**: Explain what and why
2. **Testing**: Show you tested it
3. **Screenshots** (if UI changes)
4. **Breaking Changes**: Document any
5. **Checklist**:
   - [ ] Code follows style guide
   - [ ] Comments added for complex logic
   - [ ] Documentation updated
   - [ ] No new warnings
   - [ ] Tested locally
   - [ ] Fresh clone works

---

## 🏛️ Creating a New Council

**Example: Finance Council**

```bash
# Copy template
cp -r councils/general councils/finance

# Edit councils/finance/app.py
# Change EDUCATORS list to:
{
  "id": "bull",
  "name": "The Bull",
  "emoji": "🐂",
  "personality": "Optimistic investor - sees opportunity"
},
{
  "id": "bear",
  "name": "The Bear",
  "emoji": "🐻",
  "personality": "Risk-aware pessimist - sees danger"
},
...
```

Then test:
```bash
cd councils/finance
python app.py
```

---

## 🐛 Found a Bug?

1. **Reproduce** it consistently
2. **Check** existing issues
3. **Describe** clearly:
   - Version/environment
   - Steps to reproduce
   - Expected vs actual behavior
4. **Share** error messages or screenshots

---

## ❓ Questions?

- **GitHub Issues**: For bugs and features
- **GitHub Discussions**: For questions and ideas
- **README.md**: For general help

---

## ✨ Thank You!

Every contribution makes Atheneum better. Thank you for helping! 🎉

When we merge your PR, we'll add you to:
- README.md contributors list
- CONTRIBUTORS.md file

---

**Ready to contribute? Fork, code, test, and open a PR! We're excited to see what you build.** 🚀
