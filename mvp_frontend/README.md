# Demo Frontend

This is a minimal static client to exercise the adjudication API.

Usage:

1. Start the backend API (from project root):

```bash
uvicorn mvp_backend.app:app --reload --port 8000
```

2. Open `mvp_frontend/index.html` in your browser (double-click or serve via static host).

3. Edit the JSON documents in the form and click "Submit Claim". The decision response from the API will appear below.
