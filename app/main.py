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
from .models import Product, Order
from .auth import make_token, require_admin

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "static" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)
app = FastAPI(title="MEVORA API")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

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
    customer_name: str
    phone: str
    address: str = ""
    price_type: str = "retail"
    items: list[dict]

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

@app.get("/admin")
def admin_page():
    return FileResponse(ROOT / "static" / "admin.html")

@app.post("/api/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != os.getenv("ADMIN_USERNAME", "admin") or form.password != os.getenv("ADMIN_PASSWORD", "ChangeThisPassword123!"):
        raise HTTPException(status_code=401, detail="Login yoki parol noto‘g‘ri")
    return {"access_token": make_token(form.username), "token_type": "bearer"}

@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    return [p.__dict__ | {} for p in db.query(Product).filter(Product.active == True).all()]

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
    return {"image": f"/static/uploads/{name}"}

@app.post("/api/orders")
def create_order(data: OrderIn, db: Session = Depends(get_db)):
    if not data.customer_name.strip() or not data.phone.strip() or not data.items:
        raise HTTPException(400, "Ism, telefon va savatni to‘ldiring")
    if data.price_type not in ("retail","wholesale"): raise HTTPException(400, "Narx turi xato")
    normalized=[]; total=0
    for item in data.items:
        p=db.get(Product, int(item.get("product_id",0)))
        qty=float(item.get("quantity",0))
        if not p or not p.active or qty <= 0: raise HTTPException(400, "Savatdagi mahsulot yoki miqdor xato")
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
    if status not in ["Yangi","Qabul qilindi","Tayyorlanmoqda","Yuborildi","Yakunlandi","Bekor qilindi"]: raise HTTPException(400,"Status xato")
    o.status=status; db.commit()
    return {"ok":True}
