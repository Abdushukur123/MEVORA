import os, json, shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from .database import Base, engine, get_db
from .models import Product, Order, Customer
from .auth import make_token, require_admin
import hashlib, hmac, secrets
from jose import jwt

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
UPLOADS = Path(os.getenv("UPLOAD_DIR", str(ROOT / "static" / "uploads")))
UPLOADS.mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)
app = FastAPI(title="MEVORA API")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")

class ProductIn(BaseModel):
    name: str
    category: str = "Quritilgan mevalar"
    description: str = ""
    unit: str = "kg"
    retail_price: float = Field(ge=0)
    wholesale_price: float = Field(ge=0)
    image: str = ""
    active: bool = True
    stock: float = Field(default=100, ge=0)

class OrderIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=9, max_length=20)
    address: str = Field(min_length=10, max_length=300)
    price_type: str = "retail"
    items: list[dict] = Field(min_length=1, max_length=50)

@app.on_event("startup")
def seed():
    from .database import SessionLocal
    db = SessionLocal()
    if db.query(Product).count() == 0:
        samples = [
            ("Turshak premium","Quritilgan o‘rik","kg",68000,59000,""),
            ("Qora mayiz","Mayiz","kg",52000,45000,""),
            ("Sariq mayiz","Mayiz","kg",48000,42000,""),
            ("Quritilgan olxo‘ri","Quritilgan mevalar","kg",60000,52000,""),
            ("Bodom mag‘zi","Yong‘oqlar","kg",115000,102000,""),
            ("Pista","Yong‘oqlar","kg",145000,130000,""),
            ("Quritilgan anjir","Quritilgan mevalar","kg",95000,84000,""),
            ("Xurmo qadoq","Qadoqlangan mahsulot","dona",35000,30000,""),
        ]
        for name, cat, unit, retail, wholesale, image in samples:
            db.add(Product(name=name, category=cat, unit=unit, retail_price=retail, wholesale_price=wholesale, image=image, description="MEVORA demo mahsuloti. Narxlar namuna uchun."))
        db.commit()
    db.close()

@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")

def admin_page():
    return FileResponse(ROOT / "app" / "admin.html")

# Admin sahifasi faqat Render'dagi ADMIN_PATH maxfiy yo'li orqali ochiladi.
ADMIN_PATH = os.getenv("ADMIN_PATH", "").strip()
if ADMIN_PATH:
    if not ADMIN_PATH.startswith("/"):
        ADMIN_PATH = "/" + ADMIN_PATH
    app.add_api_route(ADMIN_PATH, admin_page, methods=["GET"], include_in_schema=False)

@app.post("/api/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_username or not admin_password or not os.getenv("SECRET_KEY"):
        raise HTTPException(status_code=503, detail="Admin login serverda sozlanmagan")
    if form.username != admin_username or form.password != admin_password:
        raise HTTPException(status_code=401, detail="Login yoki parol noto‘g‘ri")
    return {"access_token": make_token(form.username), "token_type": "bearer"}

def hash_customer_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()

def verify_customer_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False

def make_customer_token(customer: Customer) -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret or len(secret) < 32:
        raise HTTPException(503, "Server xavfsizlik kaliti sozlanmagan")
    from datetime import datetime, timedelta, timezone
    payload = {"sub": str(customer.id), "role": "customer", "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, secret, algorithm="HS256")

@app.post("/api/register")
def register_customer(data: dict, db: Session = Depends(get_db)):
    full_name = str(data.get("full_name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))
    if len(full_name) < 2 or len(full_name) > 120:
        raise HTTPException(400, "Ism-familiyani to‘g‘ri kiriting")
    if len(phone) < 7 or len(phone) > 40:
        raise HTTPException(400, "Telefon raqamini to‘g‘ri kiriting")
    if len(password) < 8:
        raise HTTPException(400, "Parol kamida 8 ta belgidan iborat bo‘lsin")
    if db.query(Customer).filter(Customer.phone == phone).first():
        raise HTTPException(409, "Bu telefon raqam bilan akkaunt mavjud")
    customer = Customer(full_name=full_name, phone=phone, password_hash=hash_customer_password(password))
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"ok": True, "access_token": make_customer_token(customer), "token_type": "bearer", "customer": {"id": customer.id, "full_name": customer.full_name, "phone": customer.phone}}

@app.post("/api/customer/login")
def customer_login(data: dict, db: Session = Depends(get_db)):
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    if not customer or not verify_customer_password(password, customer.password_hash):
        raise HTTPException(401, "Telefon raqam yoki parol noto‘g‘ri")
    return {"ok": True, "access_token": make_customer_token(customer), "token_type": "bearer", "customer": {"id": customer.id, "full_name": customer.full_name, "phone": customer.phone}}

@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.active == True).all()
    return [{
        "id": p.id, "name": p.name, "category": p.category,
        "description": p.description, "unit": p.unit,
        "retail_price": p.retail_price, "wholesale_price": p.wholesale_price,
        "image": p.image, "active": p.active, "stock": p.stock,
    } for p in rows]

@app.post("/api/products", dependencies=[Depends(require_admin)])
def add_product(data: ProductIn, db: Session = Depends(get_db)):
    p = Product(**data.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return {"ok": True, "id": p.id}

@app.put("/api/products/{pid}", dependencies=[Depends(require_admin)])
def update_product(pid: int, data: ProductIn, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Mahsulot topilmadi")
    for k,v in data.model_dump().items(): setattr(p,k,v)
    db.commit()
    return {"ok": True}

@app.delete("/api/products/{pid}", dependencies=[Depends(require_admin)])
def delete_product(pid: int, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Mahsulot topilmadi")
    db.delete(p); db.commit()
    return {"ok": True}

@app.post("/api/upload", dependencies=[Depends(require_admin)])
def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in [".jpg",".jpeg",".png",".webp"]: raise HTTPException(400, "Faqat JPG, PNG yoki WEBP rasm")
    name = f"product_{os.urandom(8).hex()}{ext}"
    with (UPLOADS / name).open("wb") as f: shutil.copyfileobj(file.file, f)
    return {"image": f"/uploads/{name}"}

@app.post("/api/orders")
def create_order(data: OrderIn, db: Session = Depends(get_db)):
    if not data.customer_name.strip() or not data.address.strip():
        raise HTTPException(400, "Ism va to‘liq yetkazish manzilini kiriting")
    phone_digits = "".join(ch for ch in data.phone if ch.isdigit())
    if len(phone_digits) < 9 or len(phone_digits) > 13:
        raise HTTPException(400, "Telefon raqamini xalqaro yoki mahalliy formatda to‘g‘ri kiriting")
    if data.price_type not in ("retail","wholesale"): raise HTTPException(400, "Narx turi xato")
    normalized=[]; total=0
    for item in data.items:
        try:
            p=db.get(Product, int(item.get("product_id",0)))
            qty=float(item.get("quantity",0))
        except (TypeError, ValueError):
            raise HTTPException(400, "Savatdagi mahsulot yoki miqdor xato")
        if not p or not p.active or qty <= 0 or qty > 1000: raise HTTPException(400, "Savatdagi mahsulot yoki miqdor xato")
        if qty > p.stock: raise HTTPException(400, f"{p.name}: omborda yetarli mahsulot yo‘q")
        price=p.wholesale_price if data.price_type=="wholesale" else p.retail_price
        line=round(price*qty,2); total+=line
        normalized.append({"product_id":p.id,"name":p.name,"unit":p.unit,"quantity":qty,"unit_price":price,"line_total":line})
    order=Order(customer_name=data.customer_name.strip(), phone=data.phone.strip(), address=data.address.strip(), items_json=json.dumps(normalized,ensure_ascii=False), total=round(total,2), price_type=data.price_type)
    db.add(order); db.commit(); db.refresh(order)
    return {"ok":True,"order_id":order.id,"total":order.total}

@app.get("/api/admin/orders", dependencies=[Depends(require_admin)])
def admin_orders(db: Session = Depends(get_db)):
    rows=db.query(Order).order_by(Order.id.desc()).all()
    return [{"id":o.id,"customer_name":o.customer_name,"phone":o.phone,"address":o.address,"items":json.loads(o.items_json),"total":o.total,"price_type":o.price_type,"status":o.status,"created_at":o.created_at.isoformat()} for o in rows]

@app.patch("/api/admin/orders/{oid}", dependencies=[Depends(require_admin)])
def set_order_status(oid: int, status: str, db: Session = Depends(get_db)):
    o=db.get(Order,oid)
    if not o: raise HTTPException(404,"Buyurtma topilmadi")
    if status not in ["Yangi","Qabul qilindi","Tayyorlanmoqda","Kuryerga berildi","Yo‘lda","Yetkazildi","Bekor qilindi"]: raise HTTPException(400,"Status xato")
    o.status=status; db.commit()
    return {"ok":True}
