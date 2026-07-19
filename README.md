<div align="center">

# 🏟️ StadiumGenie AI

### Intelligent Smart Stadium & Tournament Operations Assistant
### Built for FIFA World Cup 2026 • PromptWars Challenge 4

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?style=for-the-badge&logo=flask)
![Anthropic Claude](https://img.shields.io/badge/Anthropic-Claude_4-purple?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-47_Passing-brightgreen?style=for-the-badge)
![Accessibility](https://img.shields.io/badge/WCAG-AAA-success?style=for-the-badge)
![Security](https://img.shields.io/badge/Security-Hardened-red?style=for-the-badge)
![Deployment](https://img.shields.io/badge/Deployment-Vercel-black?style=for-the-badge)

</p>

<p align="center">

🤖 AI Assistant • 📍 Smart Navigation • ♿ Accessibility • 🚨 Emergency Guidance • 📊 Tournament Operations

</p>

---

</div>

# 🌍 Vision

**StadiumGenie AI** is an AI-powered Smart Stadium Assistant built for the **FIFA World Cup 2026**.

The platform improves the stadium experience for both **fans** and **operations teams** by combining structured stadium data with **Anthropic Claude** to deliver reliable, context-aware assistance.

Unlike traditional chatbots, StadiumGenie grounds every AI response using verified stadium information such as gates, amenities, accessibility routes, emergency exits, and operational metrics before generating a response.

---

# 🎯 Problem Statement

Large sporting events involve thousands of spectators who often need instant assistance.

Common challenges include:

- Finding nearby restrooms or food stalls
- Locating accessible routes
- Reaching emergency exits quickly
- Managing gate congestion
- Responding to crowd incidents
- Assisting tournament operations teams with live recommendations

Traditional mobile applications provide static information, while human staff cannot always respond instantly.

---

# 💡 Our Solution

StadiumGenie AI combines:

- 🧠 Anthropic Claude for natural-language understanding
- 📊 Structured stadium datasets
- 📍 Context-aware navigation
- 🚨 Emergency guidance
- 📈 Live tournament operations insights
- 🔒 Security-first backend architecture

Every AI response is generated using verified stadium context instead of relying solely on the language model, significantly reducing hallucinations while improving reliability.

---

# ✨ Core Features

## 👥 Fan Experience Assistant

The public AI assistant helps visitors with:

- 🗺️ Stadium navigation
- 🚻 Nearest restrooms
- 🍔 Food stalls & wait times
- ♿ Accessible routes
- 🏥 Medical stations
- 🚨 Emergency exits
- 🎤 Natural-language interaction powered by Claude

---

## 📊 Tournament Operations Dashboard

Designed for stadium staff to monitor:

- Crowd density
- Gate utilization
- Incident reporting
- Medical & security alerts
- Operational recommendations
- AI-assisted decision support

---

# 🧠 AI Architecture

Rather than asking the language model to invent answers, StadiumGenie follows a **Grounded AI Architecture**.

### Workflow

```
Fan Question
      │
      ▼
Flask Backend
      │
      ▼
stadium_data.py
(Build Context Snapshot)
      │
      ▼
Verified Stadium Data
      │
      ▼
Anthropic Claude API
      │
      ▼
Grounded AI Response
      │
      ▼
Chat Interface
```

This Retrieval-Augmented approach ensures responses remain accurate, context-aware, and relevant to the user's stadium location.

---

# 🔒 Security Features

Security is treated as a first-class design principle.

Implemented protections include:

- Input validation & sanitization
- Rate limiting
- Secure HTTP headers
- Content Security Policy (CSP)
- X-Frame-Options
- Referrer Policy
- Generic error handling
- API key protection
- XSS-safe DOM updates
- Environment-variable based secret management

---

# ♿ Accessibility

Accessibility features include:

- High Contrast Mode
- Adjustable Text Size
- Text-to-Speech
- Keyboard Navigation
- ARIA Live Regions
- Screen Reader Support
- Step-Free Route Assistance

All primary UI colors satisfy **WCAG accessibility guidelines**.

---

# ⚙️ Technology Stack

### Backend

- Python 3.11
- Flask

### AI

- Anthropic Claude API

### Frontend

- HTML5
- CSS3
- JavaScript

### Deployment

- Vercel

### Development Tools

- Pytest
- Ruff
- Black
- MyPy

---

# 🚀 Running Locally

```bash
git clone https://github.com/Astuti5/stadium-genie.git

cd stadium-genie

pip install -r requirements.txt

cp .env.example .env
```

Add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

Run:

```bash
python app.py
```

Open:

```
http://localhost:5000
```
# ☁️ Deploying to Vercel

StadiumGenie AI is configured for **Vercel's Python Serverless Runtime**.

### Prerequisites

- Python 3.11+
- Node.js (for Vercel CLI)
- Anthropic API Key

---

### Deploy using Vercel CLI

```bash
npm install -g vercel

vercel

vercel env add ANTHROPIC_API_KEY

vercel --prod
```

When prompted, paste your Anthropic API key and select the environments where it should be available (Production and Preview).

---

### Deploy using GitHub

1. Fork or clone this repository.
2. Import the repository into Vercel.
3. Vercel automatically detects the `vercel.json` configuration.
4. Add the following environment variable:

```
ANTHROPIC_API_KEY=your_api_key
```

5. Deploy.

---

# ⚠️ Serverless Considerations

The application is deployed as **stateless serverless functions** on Vercel.

Current demo limitations:

- Rate limiter state is stored in memory.
- Incident logs are stored in memory.

Both reset after cold starts or when requests hit different serverless instances.

For production deployments, these components should be migrated to persistent storage such as:

- Vercel KV (Redis)
- PostgreSQL
- MongoDB
- Supabase

The project architecture already isolates these components, making migration straightforward.

---

# 🧪 Testing

Run the complete test suite:

```bash
pytest tests/ -v
```

Static analysis:

```bash
ruff check .
```

Formatting:

```bash
black --check .
```

Type checking:

```bash
mypy stadium_data.py ai_assistant.py app.py exceptions.py --ignore-missing-imports
```

---

# 📂 Project Structure

```
stadium-genie/
│
├── app.py
├── stadium_data.py
├── ai_assistant.py
├── exceptions.py
│
├── api/
│   └── index.py
│
├── templates/
│   ├── index.html
│   └── ops.html
│
├── static/
│   ├── style.css
│   ├── script.js
│   └── ops.js
│
├── tests/
│   ├── test_app.py
│   ├── test_ai_assistant.py
│   └── test_stadium_data.py
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── vercel.json
├── .env.example
└── README.md
```

---

# 📈 Future Enhancements

- Multi-stadium support
- Live IoT sensor integration
- Real-time crowd analytics
- Push notifications
- Indoor stadium navigation
- Ticket verification
- AI multilingual assistance
- Predictive crowd management
- Security incident prediction
- Integration with emergency response systems

---

# 🎯 Evaluation Criteria Mapping

| Category | Implementation |
|----------|----------------|
| AI Innovation | Anthropic Claude with grounded stadium context |
| Security | Input validation, CSP, rate limiting, secure headers |
| Accessibility | WCAG support, TTS, keyboard navigation, accessibility routing |
| Code Quality | Modular architecture, Ruff, Black, MyPy |
| Testing | 47 automated tests using Pytest |
| Deployment | Production-ready deployment on Vercel |
| Scalability | Context-based architecture with replaceable data layer |

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/your-feature
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push the branch

```bash
git push origin feature/your-feature
```

5. Open a Pull Request.

---

# 📜 License

This project is licensed under the **MIT License**.

---

# 🙏 Acknowledgements

- FIFA World Cup 2026 PromptWars Challenge
- Anthropic Claude API
- Flask
- Vercel
- Python Community
- Open Source Contributors

---

# 👩‍💻 Author

**Astuti Kumari**

B.Tech Computer Science Engineering

Cybersecurity | Application Security | AI Security | VAPT | Python

🔗 GitHub: https://github.com/Astuti5

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a Star!

**Built with ❤️ using Python, Flask & Anthropic Claude**

</div>