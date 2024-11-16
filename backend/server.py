from __future__ import annotations
import json
from typing import List
import io
import os
import tempfile

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from sqlalchemy import insert
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_unstructured import UnstructuredLoader

# OUR LIBS
from HIndices import ConnectionManager, HIndices
from Utils.stringify import stringify
from prompts import DATE_TODAY
from pydmodels import ChatToUpdate, CreatePodcast, CreateStorageSpace, DescriptionResponse, DocWithContent, DocumentsToDelete, MainUserQuery, NewUserChat, NewUserQueryResponse, UserCreate, UserQuery, RetrivedDocList, UserQueryResponse, UserQueryWithChatHistory
from podcastfy.client import generate_podcast

# Auth Libs
from fastapi import FastAPI, Depends, Form, HTTPException, Response, WebSocket, status, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from models import Chat, Documents, Podcast, SearchSpace, User
from database import SessionLocal
from fastapi.middleware.cors import CORSMiddleware


import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SMART_LLM = os.environ.get("SMART_LLM")
IS_LOCAL_SETUP = True if SMART_LLM.startswith("ollama") else False
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))
ALGORITHM = os.environ.get("ALGORITHM")
API_SECRET_KEY = os.environ.get("API_SECRET_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
UNSTRUCTURED_API_KEY = os.environ.get("UNSTRUCTURED_API_KEY")

def extract_model_name(model_string: str) -> tuple[str, str]:
    part1, part2 = model_string.split(":", 1)  # Split into two parts at the first colon
    return part2

MODEL_NAME = extract_model_name(SMART_LLM)

app = FastAPI()
manager = ConnectionManager()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Manual Origins
origins = [
    "http://localhost:3000",  # Frontend development server
    "http://127.0.0.1:3000"   # Alternative frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*", "Authorization", "Content-Type"],
    expose_headers=["*"],
    max_age=3600
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(email=user.username, username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if(user.apisecretkey != API_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_user = get_user_by_email(db, email=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    del user.apisecretkey
    return create_user(db=db, user=user)

# Authenticate the user
def authenticate_user(username: str, password: str, db: Session):
    user = get_user_by_email(db, email=username)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

# Create access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/verify-token/{token}")
async def verify_user_token(token: str):
    verify_token(token=token)
    return {"message": "Token is valid"}


@app.post("/searchspace/{search_space_id}/chat/create")
def create_chat_in_searchspace(chat: NewUserChat, search_space_id: int, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(chat.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == db.query(User).filter(User.username == username).first().id
        ).first()

        if not search_space:
            raise HTTPException(status_code=404, detail="SearchSpace not found or does not belong to the user")

        new_chat = Chat(type=chat.type, title=chat.title, chats_list=chat.chats_list)

        search_space.chats.append(new_chat)

        db.commit()
        db.refresh(new_chat)

        return {"chat_id": new_chat.id}

    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.post("/searchspace/{search_space_id}/chat/update")
def update_chat_in_searchspace(chat: ChatToUpdate, search_space_id: int, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(chat.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        chatindb = db.query(Chat).join(SearchSpace).filter(
            Chat.id == chat.chatid,
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == db.query(User).filter(User.username == username).first().id
        ).first()

        if not chatindb:
            raise HTTPException(status_code=404, detail="Chat not found or does not belong to the searchspace owned by the user")

        chatindb.chats_list = chat.chats_list
        db.commit()
        return {"message": "Chat Updated"}
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/searchspace/{search_space_id}/chat/delete/{token}/{chatid}")
async def delete_chat_in_searchspace(token: str, search_space_id: int, chatid: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        chatindb = db.query(Chat).join(SearchSpace).filter(
            Chat.id == chatid,
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == db.query(User).filter(User.username == username).first().id
        ).first()

        if not chatindb:
            raise HTTPException(status_code=404, detail="Chat not found or does not belong to the searchspace owned by the user")

        db.delete(chatindb)
        db.commit()
        return {"message": "Chat Deleted"}
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/searchspace/{search_space_id}/chat/{token}/{chatid}")
def get_chat_by_id_in_searchspace(chatid: int, search_space_id: int, token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        chat = db.query(Chat).join(SearchSpace).filter(
            Chat.id == chatid,
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == db.query(User).filter(User.username == username).first().id
        ).first()

        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found or does not belong to the searchspace owned by the user")

        return chat
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/searchspace/{search_space_id}/chats/{token}")
def get_chats_in_searchspace(search_space_id: int, token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Filter chats that are specifically in the given search space
        chats = db.query(Chat).filter(
            Chat.search_space_id == search_space_id,
            SearchSpace.user_id == user.id
        ).join(SearchSpace).all()

        return chats
        
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")




@app.get("/user/{token}/searchspace/{search_space_id}/documents/")
def get_user_documents(search_space_id: int, token: str, db: Session = Depends(get_db)):
    try:
        # Decode the token to get the username
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username and ensure they exist
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        # Retrieve documents associated with the search space
        return db.query(Documents).filter(Documents.search_space_id == search_space_id).all()

    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/user/{token}/searchspace/{search_space_id}/")
def get_user_search_space_by_id(search_space_id: int, token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the search space by ID and verify it belongs to this user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        return search_space
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/user/{token}/searchspaces/")
def get_user_search_spaces(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        user = db.query(User).filter(User.username == username).first()

        return db.query(SearchSpace).filter(SearchSpace.user_id == user.id).all()
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.post("/user/create/searchspace/")
def create_user_search_space(data: CreateStorageSpace, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        user = db.query(User).filter(User.username == username).first()

        db_search_space = SearchSpace(user_id=user.id, name=data.name, description=data.description)
        db.add(db_search_space)
        db.commit()
        db.refresh(db_search_space)
        return db_search_space
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.post("/user/save/")
def save_user_extension_documents(data: RetrivedDocList, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username and ensure they exist
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == data.search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")
        
        
        # all_search_space_docs = db.query(SearchSpace).filter(
        #     SearchSpace.user_id == user.id
        # ).all()
        
        # total_doc_count = 0
        # for search_space in all_search_space_docs:
        #     total_doc_count += db.query(Documents).filter(Documents.search_space_id == search_space.id).count()
            
        print(f"STARTED")

        # Initialize containers for documents and entries
        # DocumentPgEntry = []
        raw_documents = []

                # Process each document in the retrieved document list
        for doc in data.documents:
            # Construct document content
            content = (
                f"USER BROWSING SESSION EVENT: \n"
                f"=======================================METADATA==================================== \n"
                f"User Browsing Session ID : {doc.metadata.BrowsingSessionId} \n"
                f"User Visited website with url : {doc.metadata.VisitedWebPageURL} \n"
                f"This visited website url had title : {doc.metadata.VisitedWebPageTitle} \n"
                f"User Visited this website from referring url : {doc.metadata.VisitedWebPageReffererURL} \n"
                f"User Visited this website url at this Date and Time : {doc.metadata.VisitedWebPageDateWithTimeInISOString} \n"
                f"User Visited this website for : {str(doc.metadata.VisitedWebPageVisitDurationInMilliseconds)} milliseconds. \n"
                f"===================================================================================== \n"
                f"Webpage Content of the visited webpage url in markdown format : \n\n{doc.pageContent}\n\n"
                f"===================================================================================== \n"
            )
            raw_documents.append(Document(page_content=content, metadata=doc.metadata.__dict__))

           
            
        # pgdocmeta = stringify(doc.metadata.__dict__)

        #  DocumentPgEntry.append(Documents(
        #         file_type='WEBPAGE',
        #         title=doc.metadata.VisitedWebPageTitle,
        #         search_space=search_space,
        #         document_metadata=pgdocmeta,
        #         page_content=content
        #     ))

        # # Save documents in PostgreSQL
        # search_space.documents.extend(DocumentPgEntry)
        # db.commit()

        # Create hierarchical indices
        if IS_LOCAL_SETUP == True:
            index = HIndices(username=username)
        else:
            index = HIndices(username=username, api_key=OPENAI_API_KEY)

        # Save indices in vector stores
        index.encode_docs_hierarchical(
            documents=raw_documents, 
            search_space_instance=search_space, 
            files_type='WEBPAGE', 
            db=db
            )

        print("FINISHED")

        return {
            "success": "Save Job Completed Successfully"
        }


    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.post("/user/uploadfiles/")
async def save_user_documents(files: list[UploadFile], token: str = Depends(oauth2_scheme), search_space_id: int = Form(...), db: Session = Depends(get_db)):
    try:
        # Decode and verify the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username and ensure they exist
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        docs = []
        processed_files = []

        for file in files:
            try:
                # Create a temporary file with the correct extension
                temp_file = None
                try:
                    suffix = os.path.splitext(file.filename)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                        temp_file.write(await file.read())
                        temp_file.flush()

                    # Process the file based on type
                    if file.content_type.startswith('image'):
                        loader = UnstructuredLoader(
                            file_path=temp_file.name,
                            api_key=UNSTRUCTURED_API_KEY,
                            partition_via_api=True,
                            chunking_strategy="basic",
                            max_characters=90000,
                            include_orig_elements=False,
                        )
                    else:
                        loader = UnstructuredLoader(
                            file_path=temp_file.name,
                            api_key=UNSTRUCTURED_API_KEY,
                            partition_via_api=True,
                            chunking_strategy="basic",
                            max_characters=90000,
                            include_orig_elements=False,
                            strategy="fast"
                        )

                    filedocs = loader.load()

                    # Add filename to metadata
                    for doc in filedocs:
                        doc.metadata['filename'] = file.filename

                    # Create hierarchical indices
                    if IS_LOCAL_SETUP:
                        index = HIndices(username=username)
                    else:
                        index = HIndices(username=username, api_key=OPENAI_API_KEY)

                    # Save indices in vector stores
                    index.encode_docs_hierarchical(
                        documents=[Document(page_content=doc.page_content, metadata=doc.metadata) for doc in filedocs],
                        search_space_instance=search_space,
                        files_type='OTHER',
                        db=db
                    )

                    processed_files.append({
                        "filename": file.filename,
                        "status": "success",
                        "message": f"Successfully processed and indexed {file.filename}"
                    })

                finally:
                    if temp_file:
                        os.remove(temp_file.name)

            except Exception as e:
                print(f"Error processing file: {str(e)}")
                processed_files.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })

        if not processed_files:
            return {
                "status": "error",
                "message": "No files were successfully processed",
                "details": processed_files
            }

        return {
            "status": "success",
            "message": "Files processed and indexed successfully",
            "details": processed_files
        }

    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "message": "An unexpected error occurred",
            "error": str(e),
            "details": processed_files if 'processed_files' in locals() else []
        }

@app.websocket("/user/upload/{search_space_id}/{token}")
async def upload_files_websocket(
    websocket: WebSocket,
    search_space_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        # Verifica token e autorizzazioni
        user = verify_user_token(token, db)
        search_space = verify_search_space_access(user, search_space_id, db)
        
        await manager.connect(websocket)
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message["type"] == "file_upload":
                    await process_file_upload(message, websocket, search_space, db)
                    
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            
    except Exception as e:
        error_message = str(e)
        if isinstance(e, HTTPException):
            error_message = e.detail
        await websocket.close(code=4000, reason=error_message)

@app.post("/user/uploadfiles/")
async def save_user_documents(files: list[UploadFile], token: str = Depends(oauth2_scheme), search_space_id: int = Form(...), db: Session = Depends(get_db)):
    try:
        # Decode and verify the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username and ensure they exist
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        processed_files = []

        for file in files:
            try:
                # Create a temporary file with the correct extension
                temp_file = None
                try:
                    suffix = os.path.splitext(file.filename)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                        contents = await file.read()
                        temp_file.write(contents)
                        temp_file.flush()

                    # Process the file based on type
                    if file.content_type.startswith('image'):
                        loader = UnstructuredLoader(
                            file_path=temp_file.name,
                            api_key=UNSTRUCTURED_API_KEY,
                            partition_via_api=True,
                            chunking_strategy="basic",
                            max_characters=90000,
                            include_orig_elements=False,
                        )
                    else:
                        loader = UnstructuredLoader(
                            file_path=temp_file.name,
                            api_key=UNSTRUCTURED_API_KEY,
                            partition_via_api=True,
                            chunking_strategy="basic",
                            max_characters=90000,
                            include_orig_elements=False,
                            strategy="fast"
                        )

                    filedocs = loader.load()

                    # Add filename to metadata
                    for doc in filedocs:
                        doc.metadata['filename'] = file.filename

                    # Create hierarchical indices
                    if IS_LOCAL_SETUP:
                        index = HIndices(username=username)
                    else:
                        index = HIndices(username=username, api_key=OPENAI_API_KEY)

                    # Save indices in vector stores
                    index.encode_docs_hierarchical(
                        documents=[Document(page_content=doc.page_content, metadata=doc.metadata) for doc in filedocs],
                        search_space_instance=search_space,
                        files_type='OTHER',
                        db=db
                    )

                    processed_files.append({
                        "filename": file.filename,
                        "status": "success",
                        "message": f"Successfully processed and indexed {file.filename}"
                    })

                finally:
                    if temp_file and os.path.exists(temp_file.name):
                        os.remove(temp_file.name)

            except Exception as e:
                print(f"Error processing file: {str(e)}")
                processed_files.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })

        if not processed_files:
            return {
                "status": "error",
                "message": "No files were successfully processed",
                "details": processed_files
            }

        return {
            "status": "success",
            "message": "Files processed and indexed successfully",
            "details": processed_files
        }

    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "message": "An unexpected error occurred",
            "error": str(e),
            "details": processed_files if 'processed_files' in locals() else []
        }

@app.post("/user/searchspace/create-podcast")
async def create_podcast(
    data: CreatePodcast,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        # Verify token and get username
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify search space belongs to user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == data.search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        # Create new podcast entry
        new_podcast = Podcast(
            title=data.title,
            podcast_content=data.podcast_content,
            search_space_id=search_space.id
        )

        db.add(new_podcast)
        db.commit()
        db.refresh(new_podcast)
        
        podcast_config = {
            'word_count': data.wordcount, 
            'podcast_name': 'SurfSense Podcast', 
            'podcast_tagline': 'Your Own Personal Podcast.', 
            'output_language': 'English', 
            'user_instructions': 'Make if fun and engaging', 
            'engagement_techniques': ['Rhetorical Questions', 'Personal Testimonials', 'Quotes', 'Anecdotes', 'Analogies', 'Humor'], 
        }
        
        try:
            background_tasks.add_task(
                generate_podcast_background,
                new_podcast.id,
                data.podcast_content,
                MODEL_NAME,
                "OPENAI_API_KEY",
                podcast_config,
                db
            )
            # # Check MODEL NAME behavior on Local Setups
            # saved_file_location = generate_podcast(
            #     text=data.podcast_content,
            #     llm_model_name=MODEL_NAME,
            #     api_key_label="OPENAI_API_KEY",
            #     conversation_config=podcast_config,
            # )
            
            # new_podcast.file_location = saved_file_location
            # new_podcast.is_generated = True
            
            # db.commit()
            # db.refresh(new_podcast)
            
            
            return {"message": "Podcast created successfully", "podcast_id": new_podcast.id}
        except JWTError:
            raise HTTPException(status_code=403, detail="Token is invalid or expired") 
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


        
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_podcast_background(
    podcast_id: int,
    podcast_content: str,
    model_name: str,
    api_key_label: str,
    conversation_config: dict,
    db: Session
):
    try:
        saved_file_location = generate_podcast(
            text=podcast_content,
            llm_model_name=model_name,
            api_key_label=api_key_label,
            conversation_config=conversation_config,
        )

        # Update podcast in database
        podcast = db.query(Podcast).filter(Podcast.id == podcast_id).first()
        if podcast:
            podcast.file_location = saved_file_location
            podcast.is_generated = True
            db.commit()
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error generating podcast: {str(e)}")
        
        
@app.get("/user/{token}/searchspace/{search_space_id}/download-podcast/{podcast_id}")
async def download_podcast(search_space_id: int, podcast_id: int, token: str, db: Session = Depends(get_db)):
    try:
        # Verify the token and get the username
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        # Retrieve the podcast file from the database
        podcast = db.query(Podcast).filter(
            Podcast.id == podcast_id,
            Podcast.search_space_id == search_space_id
        ).first()
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found in the specified search space")

        # Read the file content
        with open(podcast.file_location, "rb") as file:
            file_content = file.read()

        # Create a response with the file content
        response = Response(content=file_content)
        response.headers["Content-Disposition"] = f"attachment; filename={podcast.title}.mp3"
        response.headers["Content-Type"] = "audio/mpeg"

        return response
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{token}/searchspace/{search_space_id}/podcasts")
async def get_user_podcasts(token: str, search_space_id: int, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        podcasts = db.query(Podcast).filter(Podcast.search_space_id == search_space_id).all()
        return podcasts
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

# Incomplete function, needs to be implemented based on the actual requirements and database structure
@app.post("/searchspace/{search_space_id}/delete/docs")
def delete_all_related_data(search_space_id: int, data: DocumentsToDelete, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username and ensure they exist
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")
        
        if IS_LOCAL_SETUP:
            index = HIndices(username=username)
        else:
            index = HIndices(username=username, api_key=OPENAI_API_KEY)

        message = index.delete_vector_stores(summary_ids_to_delete=data.ids_to_delete, db=db, search_space=search_space.name)

        return {
            "message": message
        }

    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.websocket("/beta/chat/{search_space_id}/{token}")
async def searchspace_chat_websocket_endpoint(websocket: WebSocket, search_space_id: int, token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")

        # Get the user by username and ensure they exist
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the search space belongs to the user
        search_space = db.query(SearchSpace).filter(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user.id
        ).first()
        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found or does not belong to the user")

        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # print(data)
                if data["type"] == "search_space_chat":
                    query = data["content"]

                    if message["searchtype"] == "local" :
                        report_source = "langchain_documents"
                    else:
                        report_source = message["searchtype"]

                    if message["answertype"] == "general_answer" :
                        report_type = "custom_report"
                    else:
                        report_type = message["answertype"]


                    # Create Heirarical Indecices
                    if(IS_LOCAL_SETUP == True):
                        index = HIndices(username=username)
                    else:
                        index = HIndices(username=username,api_key=OPENAI_API_KEY)


                    await index.ws_experimental_search(websocket=websocket, manager=manager, query=query, search_space=search_space.name, report_type=report_type,  report_source=report_source)

                    await manager.send_personal_message(
                        json.dumps({"type": "end"}),
                        websocket
                    )



                if message["type"] == "multiple_documents_chat":
                    query = message["content"]
                    received_chat_history = message["chat_history"]
                    
                    chatHistory = []
                    
                    chatHistory = [
                        SystemMessage(
                            content=DATE_TODAY + """You are an helpful assistant for question-answering tasks.
                            Use the following pieces of retrieved context to answer the question.
                            If you don't know the answer, just say that you don't know.
                            Context:""" + str(received_chat_history[0]['relateddocs']))
                    ]
                    
                    for data in received_chat_history[1:]:
                        if data["role"] == "user":
                            chatHistory.append(HumanMessage(content=data["content"]))
                        
                        if data["role"] == "assistant":
                            chatHistory.append(AIMessage(content=data["content"]))


                    chatHistory.append(("human", "{input}"))
                    
                    qa_prompt = ChatPromptTemplate.from_messages(chatHistory)
                    
                    if(IS_LOCAL_SETUP == True):
                        llm = OllamaLLM(model=MODEL_NAME,temperature=0)
                    else:
                        llm = ChatOpenAI(temperature=0, model_name=MODEL_NAME, api_key=OPENAI_API_KEY)

                    descriptionchain = qa_prompt | llm
                    
                    streamingResponse = ""
                    counter = 0
                    for res in descriptionchain.stream({"input": query}):
                        streamingResponse += res.content
                        
                        if (counter < 20) : 
                            counter += 1
                        else :
                            await manager.send_personal_message(
                                json.dumps({"type": "stream", "content": streamingResponse}),
                                websocket
                            )
                            
                            counter = 0
                            
                    await manager.send_personal_message(
                                json.dumps({"type": "stream", "content": streamingResponse}),
                                websocket
                            )
                     
                    await manager.send_personal_message(
                        json.dumps({"type": "end"}),
                        websocket
                    )
        except Exception as e:
            print(f"Error: {e}")
        finally:
            manager.disconnect(websocket)
    except JWTError:
        await websocket.close(code=4003, reason="Invalid token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, loop="asyncio")