# MEVORA — ishlaydigan MVP

Bu loyiha MEVORA internet-do‘konining birinchi ishlaydigan versiyasi:
- Mahsulotlar katalogi va qidiruv
- Kg yoki dona/paket bo‘yicha miqdor tanlash
- Savat va buyurtma yuborish
- Admin login
- Admin panelda mahsulot qo‘shish, tahrirlash, o‘chirish va narxlarni boshqarish
- Buyurtmalarni ko‘rish va holatini o‘zgartirish
- Ma’lumotlar SQLite bazasida saqlanadi

## 1. Windows kompyuterda ishga tushirish

1. ZIP faylni oching.
2. `MEVORA_fullstack_mvp` papkasiga kiring.
3. Papka ichidagi manzil qatoriga `cmd` yozib Enter bosing.
4. Quyidagi buyruqlarni bittadan kiriting:

```bat
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
```

5. `.env` faylini Notepad bilan oching. `ADMIN_PASSWORD` qiymatini o‘zingizga tegishli kuchli parolga almashtiring. `SECRET_KEY` uchun uzun tasodifiy matn yozing.
6. Serverni ishga tushiring:

```bat
py -m uvicorn app.main:app --reload
```

7. Brauzerda `http://127.0.0.1:8000` ni oching.
8. Admin panel: `http://127.0.0.1:8000/admin`

Standart login nomi `.env` ichidagi `ADMIN_USERNAME`, standart parol esa siz o‘zgartirgan `ADMIN_PASSWORD`.

## Muhim
- Bu MVP hozircha bitta kompyuterda sinash uchun. Internetga chiqarishdan oldin HTTPS, kuchli maxfiy kalit, serverdagi PostgreSQL, zaxira nusxa, spamdan himoya va xavfsizlik tekshiruvi kerak.
- Rasmlar hozircha `static/uploads/` papkasiga yuklanadi.
- Buyurtma yuborilganda hozircha onlayn to‘lov yoki yetkazib berish xizmati ulanmagan.
- Demo mahsulotlar va narxlar namuna sifatida kiritilgan; haqiqiy bozor narxlari emas.
