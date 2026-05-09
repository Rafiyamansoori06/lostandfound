from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

from dotenv import load_dotenv
import os

# =========================
# APPWRITE IMPORTS
# =========================
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.storage import Storage
from appwrite.id import ID
from appwrite.input_file import InputFile

# =========================
# LOAD ENV VARIABLES
# =========================
load_dotenv()

app = FastAPI()

# =========================
# SESSION
# =========================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "secret123")
)

# =========================
# STATIC FILES
# =========================
os.makedirs("static", exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# =========================
# GOOGLE OAUTH
# =========================
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    },
)

# =========================
# APPWRITE CONFIG
# =========================
client = Client()

client.set_endpoint("https://cloud.appwrite.io/v1")
client.set_project(os.getenv("APPWRITE_PROJECT_ID"))
client.set_key(os.getenv("APPWRITE_API_KEY"))

databases = Databases(client)
storage = Storage(client)

DATABASE_ID = os.getenv("APPWRITE_DATABASE_ID")
COLLECTION_ID = os.getenv("APPWRITE_COLLECTION_ID")
BUCKET_ID = os.getenv("APPWRITE_BUCKET_ID")

# =========================
# GOOGLE LOGIN
# =========================
@app.get("/google-login")
async def google_login(request: Request):

    redirect_uri = request.url_for("auth")

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )

# =========================
# GOOGLE AUTH CALLBACK
# =========================
@app.get("/auth")
async def auth(request: Request):

    token = await oauth.google.authorize_access_token(request)

    user = token.get("userinfo")

    if user:
        request.session["user"] = user

        return RedirectResponse(
            "/",
            status_code=302
        )

    return HTMLResponse("<h2>Login Failed</h2>")

# =========================
# LOGOUT
# =========================
@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=302
    )

# =========================
# LOGIN PAGE
# =========================
@app.get("/login", response_class=HTMLResponse)
def login_page():

    return """
    <html>

    <head>

        <title>Login</title>

        <style>

            body{
                margin:0;
                padding:0;
                background:linear-gradient(135deg,#0f172a,#1e293b);
                height:100vh;
                display:flex;
                justify-content:center;
                align-items:center;
                font-family:Arial;
                color:white;
            }

            .login-box{
                background:#1e293b;
                padding:40px;
                border-radius:16px;
                width:350px;
                text-align:center;
                box-shadow:0 4px 20px rgba(0,0,0,0.5);
            }

            .login-btn{
                padding:14px;
                width:100%;
                border:none;
                border-radius:10px;
                background:#ef4444;
                color:white;
                font-size:16px;
                cursor:pointer;
            }

            .login-btn:hover{
                background:#dc2626;
            }

        </style>

    </head>

    <body>

        <div class="login-box">

            <h1>🔐 Lost & Found</h1>

            <p>Login to continue</p>

            <a href="/google-login">

                <button class="login-btn">
                    Login with Google
                </button>

            </a>

        </div>

    </body>

    </html>
    """

# =========================
# HOME PAGE
# =========================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    user = request.session.get("user")

    if not user:
        return RedirectResponse("/login")

    items_html = ""

    try:

        docs = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID
        )

        documents = docs["documents"]

        print(documents)

        for item in documents:

            print("FULL DATA =", item)

            status = item.get("status", "")

            if status == "Lost":

                image_html = ""

                image_url = item.get("image", "")

                if image_url:
                    image_html = f"""
                    <img src="{image_url}" alt="Item Image">
                    """

                item_name = item.get(
                    "itemname",
                    "Unknown Item"
                )

                description = item.get(
                    "description",
                    "No description"
                )

                location = item.get(
                    "location",
                    "Unknown Location"
                )

                email = item.get(
                    "email",
                    "No Email"
                )

                item_id = item.get("$id")

                items_html += f"""

                <div class="card">

                    {image_html}

                    <h3>{item_name}</h3>

                    <p>📝 {description}</p>

                    <p>📍 {location}</p>

                    <p>📧 {email}</p>

                    <form action="/claim/{item_id}" method="post">

                        <button class="claim-btn">
                            Claim Item
                        </button>

                    </form>

                </div>
                """

    except Exception as e:

        return HTMLResponse(
            f"<h2>Error Loading Data: {str(e)}</h2>"
        )

    return f"""
    <html>

    <head>

        <title>Lost & Found</title>

        <style>

            body{{
                margin:0;
                padding:20px;
                background:linear-gradient(135deg,#0f172a,#1e293b);
                color:white;
                font-family:Arial;
            }}

            .container{{
                max-width:1200px;
                margin:auto;
            }}

            .topbar{{
                display:flex;
                justify-content:space-between;
                align-items:center;
                margin-bottom:30px;
            }}

            .logout-btn{{
                background:#ef4444;
                border:none;
                padding:10px 18px;
                border-radius:10px;
                color:white;
                cursor:pointer;
            }}

            .card{{
                background:#1e293b;
                padding:18px;
                border-radius:14px;
                box-shadow:0 4px 15px rgba(0,0,0,0.4);
            }}

            .form-card{{
                margin-bottom:25px;
            }}

            input, textarea{{
                width:100%;
                padding:12px;
                margin-top:10px;
                border:none;
                border-radius:10px;
                background:#334155;
                color:white;
                box-sizing:border-box;
            }}

            textarea{{
                min-height:100px;
            }}

            button{{
                margin-top:12px;
                width:100%;
                padding:12px;
                border:none;
                border-radius:10px;
                background:#22c55e;
                color:white;
                font-size:15px;
                cursor:pointer;
            }}

            button:hover{{
                opacity:0.9;
            }}

            .grid{{
                display:grid;
                grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
                gap:20px;
            }}

            img{{
                width:100%;
                height:300px;
                object-fit:contain;
                border-radius:10px;
                margin-bottom:10px;
                background:white;
                padding:5px;
            }}

            .claim-btn{{
                background:#3b82f6;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <div class="topbar">

                <h2>
                    👋 Welcome, {user.get("email")}
                </h2>

                <a href="/logout">

                    <button class="logout-btn">
                        Logout
                    </button>

                </a>

            </div>

            <div class="card form-card">

                <h2>📦 Report Lost Item</h2>

                <form
                    action="/report"
                    method="post"
                    enctype="multipart/form-data"
                >

                    <input
                        type="text"
                        name="itemName"
                        placeholder="Item Name"
                        required
                    >

                    <input
                        type="text"
                        name="location"
                        placeholder="Location"
                        required
                    >

                    <input
                        type="email"
                        name="email"
                        placeholder="Email"
                        required
                    >

                    <textarea
                        name="description"
                        placeholder="Description"
                    ></textarea>

                    <input
                        type="file"
                        name="image"
                    >

                    <button type="submit">
                        Add Item
                    </button>

                </form>

            </div>

            <h2>📋 Lost Items</h2>

            <div class="grid">

                {items_html}

            </div>

        </div>

    </body>

    </html>
    """

# =========================
# REPORT ITEM
# =========================
@app.post("/report")
async def report(
    request: Request,
    itemName: str = Form(...),
    location: str = Form(...),
    email: str = Form(...),
    description: str = Form(""),
    image: UploadFile = File(None)
):

    user = request.session.get("user")

    if not user:
        return RedirectResponse("/login")

    image_url = ""

    try:

        # =====================
        # IMAGE UPLOAD
        # =====================
        if image and image.filename:

            file_bytes = await image.read()

            uploaded_file = storage.create_file(
                bucket_id=BUCKET_ID,
                file_id=ID.unique(),
                file=InputFile.from_bytes(
                    file_bytes,
                    filename=image.filename
                )
            )

            file_id = uploaded_file.id

            image_url = (
                f"https://cloud.appwrite.io/v1/storage/buckets/"
                f"{BUCKET_ID}/files/{file_id}/view"
                f"?project={os.getenv('APPWRITE_PROJECT_ID')}"
                f"&mode=admin"
            )

        # =====================
        # CREATE DOCUMENT
        # =====================
        databases.create_document(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID,
            document_id=ID.unique(),
            data={
                "itemname": itemName,
                "location": location,
                "email": email,
                "description": description,
                "image": image_url,
                "status": "Lost"
            }
        )

    except Exception as e:

        return HTMLResponse(
            f"<h2>Upload Error: {str(e)}</h2>"
        )

    return RedirectResponse(
        "/",
        status_code=303
    )

# =========================
# CLAIM ITEM
# =========================
@app.post("/claim/{item_id}")
def claim(request: Request, item_id: str):

    user = request.session.get("user")

    if not user:
        return RedirectResponse("/login")

    try:

        databases.update_document(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID,
            document_id=item_id,
            data={
                "status": "Claimed"
            }
        )

    except Exception as e:

        return HTMLResponse(
            f"<h2>Error: {str(e)}</h2>"
        )

    return RedirectResponse(
        "/",
        status_code=303
    )

# =========================
# RUN SERVER
# =========================
# uvicorn main:app --reload