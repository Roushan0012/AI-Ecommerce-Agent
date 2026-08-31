# AI Commerce Agent API - Postman Documentation

This directory contains the Postman API collection for testing the FastAPI backend endpoints of the AI Commerce Agent.

## Collection Details

- **Collection Name**: `AI Commerce Agent API`
- **File**: `AI-Commerce-Agent-API.postman_collection.json`
- **Format**: Postman Collection v2.1.0

---

## 1. Start the FastAPI Server

Before executing requests in Postman, ensure the backend development server is running:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

---

## 2. Importing the Collection into Postman

1. Open **Postman**.
2. Click the **Import** button in the top left workspace navigation.
3. Choose **Files** and select `docs/postman/AI-Commerce-Agent-API.postman_collection.json` (or drag and drop the file into Postman).
4. Click **Import**. The `AI Commerce Agent API` collection will appear in your left sidebar.

---

## 3. Running the Health Check Request

1. In Postman, expand the **AI Commerce Agent API** collection.
2. Select the **Health Check** request:
   - **Method**: `GET`
   - **URL**: `http://127.0.0.1:8000/api/health`
3. Click **Send**.

### Expected Response

- **Status**: `200 OK`
- **Body**:
  ```json
  {
    "status": "ok",
    "service": "ai-commerce-agent-api"
  }
  ```

---

## 4. Postman Tests

The **Health Check** request includes automated JavaScript tests under the **Tests** tab:

1. **Status code is 200**:
   Verifies that the server returns an HTTP 200 OK status code.
2. **Response contains status = ok**:
   Asserts that the JSON response payload contains `"status": "ok"`.
3. **Response contains service = ai-commerce-agent-api**:
   Asserts that the JSON response payload contains `"service": "ai-commerce-agent-api"`.

When you click **Send**, view the **Test Results** tab in Postman to confirm all 3 assertions pass (3/3).
