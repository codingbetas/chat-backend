# Real-Time Chat Backend

A secure, real-time chat backend built with FastAPI, WebSockets, PostgreSQL, and JWT authentication. This project demonstrates how to build a stateful, bidirectional communication system that supports multiple connected clients, secure user authentication, and persistent chat history.

## 🚀 Features

- **Real-Time Messaging:** Instant, bidirectional communication using WebSockets.
- **WebSocket Connection Management:** Maintains active client connections in memory.
- **JWT Authentication:** Secures WebSocket connections and protected endpoints.
- **Database Persistence:** Stores users and chat messages in PostgreSQL.
- **Message History:** Allows users to retrieve their past conversations.

## 🧠 System Design Concepts

1. **WebSockets:** Unlike traditional REST APIs, WebSockets establish persistent connections, allowing the server to push messages to clients instantly without polling.
2. **Stateful Connection Management:** The application tracks active WebSocket connections in memory. *(Note: In a distributed production environment, Redis Pub/Sub would be needed to coordinate connections across multiple servers).*
3. **Secured WebSockets:** Clients must provide a valid JWT before establishing a connection.
   `ws://localhost:8000/ws?token=YOUR_JWT_TOKEN`
4. **Database Modeling:** Uses SQLAlchemy to model users and messages with foreign key relationships between senders and receivers.

## 🏗️ Architecture

```text
Client A ────┐
             │ WebSocket Connection
             ▼
      ┌────────────────┐
      │    FastAPI     │
      │   /ws Endpoint │
      └────────┬───────┘
               │
               ▼
      ┌────────────────┐
      │  Connection    │
      │    Manager     │
      │                │
      │ Tracks Active  │
      │     Users      │
      └────────┬───────┘
               │
               ▼
      ┌────────────────┐
      │   PostgreSQL   │
      │                │
      │ Users &        │
      │ Messages       │
      └────────────────┘
               ▲
               │ WebSocket Connection
          ┌────┴────┐
          │ Client B│
          └─────────┘
```

## 📁 Project Structure

```text
chat-backend/
├── app/
│   ├── main.py          # FastAPI app and WebSocket routes
│   ├── models.py        # SQLAlchemy User and Message models
│   ├── schemas.py       # Pydantic validation schemas
│   ├── auth.py          # JWT logic and OAuth2
│   ├── security.py      # Password hashing
│   └── database.py      # Database session and engine
├── alembic/             # Database migrations
├── .env                 # Environment variables
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Project dependencies
└── README.md            # This file
```

## 🛠️ Tech Stack

- **Framework:** FastAPI
- **Real-Time Communication:** WebSockets
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Database Migrations:** Alembic
- **Authentication:** JWT (JSON Web Tokens) and OAuth2
- **ASGI Server:** Uvicorn

## 🚀 Getting Started

**1. Create a Virtual Environment**
```bash
python -m venv venv
venv\Scripts\activate
```

**2. Install Dependencies**
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic "python-jose[cryptography]" "passlib[bcrypt]" python-multipart websockets python-dotenv
```

**3. Configure Environment Variables**
Create a `.env` file in the project root and add the following:
```text
DATABASE_URL=postgresql://user:password@localhost:5432/chat_db
SECRET_KEY=your_secret_key
ALGORITHM=HS256
```

**4. Set Up the Database**
Create the PostgreSQL database if it does not already exist:
```sql
CREATE DATABASE chat_db;
```
Run the database migrations:
```bash
alembic upgrade head
```

**5. Start the Server**
```bash
uvicorn app.main:app --reload
```
- API Base URL: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## 🔌 How to Test the WebSocket

1. Start the FastAPI server.
2. Register a user and log in through the REST API to obtain a JWT access token.
3. Open Postman or another WebSocket client.
4. Connect to the following URL, replacing `YOUR_JWT_TOKEN` with your actual token:
   `ws://localhost:8000/ws?token=YOUR_JWT_TOKEN`
5. Send a message and verify it is delivered and saved to PostgreSQL.

*(Use `wss://` instead of `ws://` when deploying over HTTPS in production).*

## 📄 License

This project is licensed under the MIT License.