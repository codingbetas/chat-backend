from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy.orm import Session
from app.database import get_db, engine, SessionLocal
from app import models, schemas
from app.security import hash_password, verify_password
from app.auth import create_access_token, get_current_user, decode_access_token
from fastapi.security import OAuth2PasswordRequestForm

app = FastAPI()


connections = {}  # user_id -> set of WebSocket connections
active_users = set()

# Create tables
models.Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "Backend running 🚀"}


@app.get("/me")
def get_me(user_id: int = Depends(get_current_user)):
    return {"user_id": user_id}


# 👉 CREATE USER
@app.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_pwd = hash_password(user.password)

    new_user = models.User(
        name=user.name,
        email=user.email,
        password=hashed_pwd
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# 👉 GET USER WITH MESSAGES
@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@app.get("/chat/{user_id}", response_model=list[schemas.MessageResponse])
def get_chat(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    messages = db.query(models.Message).filter(
        (
            (models.Message.sender_id == current_user) &
            (models.Message.receiver_id == user_id)
        )
        |
        (
            (models.Message.sender_id == user_id) &
            (models.Message.receiver_id == current_user)
        )
    ).order_by(
        models.Message.created_at.asc()
    ).all()

    return messages

# 👉 CREATE MESSAGE
@app.post("/messages", response_model=schemas.MessageResponse)
def create_message(
    message: schemas.MessageCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    # Check receiver exists
    receiver = db.query(models.User).filter(
        models.User.id == message.receiver_id
    ).first()

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    # Prevent sending to yourself
    if message.receiver_id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send a message to yourself"
        )

    # Create message
    new_message = models.Message(
        content=message.content.strip(),
        sender_id=user_id,
        receiver_id=message.receiver_id
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


# 👉 GET MESSAGES (ONLY CURRENT USER)
@app.get(
    "/messages",
    response_model=list[schemas.MessageResponse]
)
def get_messages(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    messages = db.query(models.Message).filter(
        (models.Message.sender_id == user_id) |
        (models.Message.receiver_id == user_id)
    ).order_by(
        models.Message.created_at.asc()
    ).all()

    return messages


@app.get("/online-users")
def get_online_users():
    return list(active_users)


# 👉 WEBSOCKET (SECURE)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            await websocket.close(code=1008)
            return

    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    if user_id not in connections:
     connections[user_id] = set()
   
    connections[user_id].add(websocket)
    active_users.add(user_id)

    try:
      while True:
        data = await websocket.receive_json()

        receiver_id = data.get("receiver_id")
        message_text = data.get("message")

        # Validate receiver_id
        if receiver_id is None:
            await websocket.send_json({
                "error": "receiver_id is required"
            })
            continue

        # Validate message
        if not isinstance(message_text, str) or not message_text.strip():
            await websocket.send_json({
                "error": "Message cannot be empty"
            })
            continue

        # Limit message length
        message_text = message_text.strip()

        if len(message_text) > 2000:
            await websocket.send_json({
                "error": "Message cannot exceed 2000 characters"
            })
            continue

        # Convert receiver ID
        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            await websocket.send_json({
                "error": "Invalid receiver_id"
            })
            continue

        # Prevent sending to yourself
        if receiver_id == user_id:
            await websocket.send_json({
                "error": "You cannot send a message to yourself"
            })
            continue

        # Check receiver exists
        with SessionLocal() as db:

            receiver = db.query(models.User).filter(
                models.User.id == receiver_id
            ).first()

            if not receiver:
                await websocket.send_json({
                    "error": "Receiver not found"
                })
                continue

            # Save message
            new_message = models.Message(
                content=message_text,
                sender_id=user_id,
                receiver_id=receiver_id
            )

            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            created_at = new_message.created_at.isoformat()

        # Send to receiver ONLY if online
        if receiver_id in connections:
           for connection in connections[receiver_id].copy():
            try:
               await connection.send_json({
                "from": user_id,
                "message": message_text,
                "created_at": created_at
               })
            except Exception:
             connections[receiver_id].discard(connection)
        # Send confirmation back to sender
        await websocket.send_json({
            "to": receiver_id,
            "message": message_text,
            "created_at": created_at
        })

    except WebSocketDisconnect:
     if user_id in connections:
        connections[user_id].discard(websocket)

        if not connections[user_id]:
            del connections[user_id]
            active_users.discard(user_id)
    # except Exception as e:
    #     db.rollback()
    #     print("Error:", e)

   

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    db_user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_access_token(data={"user_id": db_user.id})

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.post("/forgot-password")
def forgot_password(
    request: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Generate secure random token
    reset_token = secrets.token_urlsafe(32)

    # Token valid for 15 minutes
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    user.reset_token = reset_token
    user.reset_token_expires = expires

    db.commit()

    # TEMPORARY: return token directly for testing.
    # Later we will send this token through email.
    return {
        "message": "Password reset token generated",
        "reset_token": reset_token,
        "expires_at": expires
    }

@app.post("/reset-password")
def reset_password(
    request: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Check token
    if not user.reset_token:
        raise HTTPException(
            status_code=400,
            detail="No reset request found"
        )

    if user.reset_token != request.reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid reset token"
        )

    # Check expiration
    if not user.reset_token_expires:
        raise HTTPException(
            status_code=400,
            detail="Reset token expiration missing"
        )

    # PostgreSQL returns timezone-aware/naive values depending on column configuration.
    expires = user.reset_token_expires

    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        raise HTTPException(
            status_code=400,
            detail="Reset token expired"
        )

    # Update password
    user.password = hash_password(request.new_password)

    # Invalidate token after successful reset
    user.reset_token = None
    user.reset_token_expires = None

    db.commit()

    return {
        "message": "Password reset successful"
    }