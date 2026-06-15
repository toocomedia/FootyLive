# FootyLive

FootyLive is a high-performance Python web application built with FastAPI that provides real-time football scores, match events, and World Cup standings. It acts as a lightweight proxy for live sports data, heavily optimized with in-memory caching to serve high volumes of traffic without triggering external rate limits.

## Features

- Live Match Tracking: Real-time score updates, live events ticker, and match minute tracking.
- Intelligent Caching: Custom in-memory TTLCache mechanism to drastically reduce outbound network requests during high concurrency.
- Responsive Design: Custom CSS framework with a sleek glassmorphism aesthetic and seamless dark/light mode toggle.
- Production Ready: Pre-configured for instant deployment on Render using Infrastructure as Code (render.yaml).

## Tech Stack

- Backend: FastAPI, Python 3.10+
- Frontend: HTML5, CSS3, Jinja2 Templates
- Networking: HTTPX
- Data Source: ESPN Soccer API

## Local Development

### 1. Install Dependencies
Ensure you have Python installed. Create a virtual environment and install the required packages:

```bash
python -m venv .venv
# On Windows use: .venv\Scripts\activate
# On Mac/Linux use: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Server
You can start the local development server using uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

The application will be available at http://localhost:8000.

## Deployment

This project is configured to be deployed automatically to Render.com.

1. Push this repository to GitHub.
2. Create an account on Render.com.
3. Click "New" -> "Blueprint".
4. Select your GitHub repository.
5. Render will automatically provision the environment, install dependencies, and start the application using the configuration provided in `render.yaml`.
