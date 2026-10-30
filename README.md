# 🏠 Tartibli Xonadosh (Talabalar Kvartira Boshqaruvi)
### *Multi-Tenant Flatmate, Chore & Communal Fund Management Telegram Bot*

Toshkent shahridagi talabalar turar joylari (TTJ), ijarada birga yashovchi talabalar va xonadoshlar (2–10 kishi) uchun navbatchilik (oshxona, 10L suv, haftalik 11 bosqichli tozalash, kir yuvish) va umumiy kassa zaxirasini (bozorlik, yig'imlar) avtomatlashtirilgan, shaffof va adolatli boshqarish platformasi.

---

## 🚀 Texnologik Stek

- **Dasturlash tili & Freymvork:** Python 3.11+, [Aiogram 3.15+](https://docs.aiogram.dev/) (Modern Asynchronous Telegram Bot Framework)
- **Ma'lumotlar bazasi & ORM:** PostgreSQL 16, [SQLAlchemy 2.0 (asyncio + asyncpg)](https://docs.sqlalchemy.org/)
- **Migratsiyalar:** [Alembic](https://alembic.sqlalchemy.org/)
- **FSM & Kesh:** Redis 7 (Aiogram `RedisStorage`)
- **Vazifalar rejalashtiruvchisi (Cron/Scheduler):** [APScheduler 3.x](https://apscheduler.readthedocs.io/) (AsyncIOScheduler, Asia/Tashkent)
- **Konteynerizatsiya:** Docker & Docker Compose (Oracle Cloud Always Free Ubuntu 24.04 ga moslangan)

---

## 🏢 Multi-Tenant Kvartira Shablonlari (Presets)

1. **🏢 Katta Kvartira (`LARGE_FLAT`, 6–10 kishi):**
   - **Kunlik oshxona va idishlar:** Ovqat tayyorlash, non, dasturxonni yig'ishtirish, qozon va umumiy idishlarni yuvish, chiqindini to'kish. *(Qoida: shaxsiy idishlar darhol har kim o'zi yuvadi!)*
   - **10L toza suv navbatchiligi:** Filtrlangan 10L toza suv baklajkalarini olib kelish va suv zaxirasini to'ldirish.
   - **Haftalik katta tozalash (Juftlik navbati - 2 kishi):** 11 bosqichli to'liq tozalash checklisti:
     1. 2 ta katta xonani changyutgichda tozalash
     2. Pastki stollarni artish
     3. Balkon, dahliz va oshxonani changyutgich qilish
     4. Gaz plitasi ustidagi folgani almashtirish
     5. Dasturxon va pol latta/brezentini yuvish
     6. Hojatxona, cho'tka va gilamchani xlorlab yuvish
     7. Deraza tokchalarini artish
     8. Vanna va rakovinani chuqur tozalash
     9. Poyabzal javonini tartibga keltirish
     10. Barcha xonalardagi chiqindi chelaklarini bo'shatish
     11. Polni tozalab artish / nam tozalash
   - **Kir yuvish navbati:** Kiryuvish mashinasidan navbat bilan foydalanish va kiyimlarni yuvish grafigi.

2. **🏠 Ixcham Kvartira (`COMPACT_FLAT`, 2–5 kishi):**
   - Kunlik oshxona tozaligi
   - Chiqindini olib chiqish
   - Polni supurish va nam artish (2 kunda 1 marta)

3. **🛏 TTJ / Yotoqxona (`DORMITORY`):**
   - Xona tozaligi va tartibi
   - Chiqindi navbatchiligi
   - Tinchlik soati nazorati (22:30 da chiroqlar va tartib)

4. **⚙️ Shaxsiy (`CUSTOM`):**
   - Bo'sh shablon (admin o'zi xohlagan davriy vazifalarni belgilaydi).

---

## 💰 Yagona Umumiy Kassa va Bozorlik Tizimi (Communal Fund)

Chigal o'zaro qarzdorlik matritsalari o'rniga yagona umumiy kassa balansi joriy etildi:
- **`flat.fund_balance` (Numeric 12, 2):** Kvartiraning umumiy pul zaxirasi.
- **`📥 Pul yig'ish`:** Har bir a'zodan teng miqdorda yig'iladi (masalan, 4 kishidan 100 000 so'mdan = 400 000 so'm) va har bir kishi uchun `INCOME` operatsiyasi yoziladi.
- **`🧾 Xarid kiritish`:** Bozorlik yoki xarid cheki kiritilganda (masalan, Korzinkada 370 293 so'm sarflandi), mablag' umumiy kassa balansidan tiyinigacha aniq chegiriladi (qoldiq: 29 707 so'm) va `EXPENSE` operatsiyasi qayd etiladi.
- **`💰 Kassa balansi`:** Joriy kassa qoldig'i, jami kirim va jami chiqim hisoboti.
- **`📜 Xaridlar tarixi`:** Oxirgi 5 ta kassa amaliyati (vaqt, foydalanuvchi, summa, tavsif va qoldiq).

---

## 📜 Kvartira Qoidalari va Tartibi

- 🌙 **Tinchlik soati:** Har kuni soat **22:30** dan boshlab qattiq shovqin taqiqlanadi (naushnikdan foydalanish majburiy).
- 🍽 **Idish siyosati:** Shaxsiy idishlar ovqatdan so'ng **darhol** yuviladi. Chanoqda idish qoldirish taqiqlanadi. Qozon va umumiy idishlar navbatchi zimmasida.
- 👥 **Mehmonlar:** Mehmon taklif qilishdan kamida **3–4 soat oldin** guruhda xabar berilib, rozilik olinadi.
- ⚠️ **Intizom:** Navbatchilikni sababsiz bajarmaslik holatida navbatdan tashqari tozalash yoki jarima belgilanadi.

---

## 📂 Loyiha Tuzilmasi (Folder Tree)

```text
tartibli-xonadosh/
├── .env.example              # Muhit o'zgaruvchilari namunasi
├── .gitignore                # Git e'tiborsiz qoldiradigan fayllar
├── Dockerfile                # Production-grade Python 3.11 Docker tasviri
├── docker-compose.yml        # PostgreSQL, Redis va Bot xizmatlari
├── requirements.txt          # Python kutubxonalari ro'yxati
├── alembic.ini               # Alembic konfiguratsiyasi
├── README.md                 # Arxitektura va foydalanish qo'llanmasi
├── alembic/
│   ├── env.py                # Asinxron SQLAlchemy migratsiya muhiti
│   └── versions/             # DB schema versiyalari
├── app/
│   ├── config.py             # Pydantic Settings
│   ├── database/
│   │   ├── base.py           # DeclarativeBase va TimestampMixin
│   │   └── session.py        # Async Engine, SessionMaker, DB Init
│   ├── models/
│   │   ├── user.py           # User modeli
│   │   ├── flat.py           # Flat (template_type, fund_balance, quiet_hours)
│   │   ├── chore.py          # Chore (checklist, rotation_type, assignee_ids)
│   │   └── fund.py           # FundTransaction (INCOME, EXPENSE, balance_after)
│   ├── repositories/
│   │   ├── user_repo.py      # Foydalanuvchi ma'lumotlari
│   │   ├── flat_repo.py      # Kvartira va a'zolar ombori
│   │   ├── chore_repo.py     # Navbatchilik vazifalari
│   │   └── fund_repo.py      # Kassa va xaridlar ombori
│   ├── services/
│   │   ├── onboarding_service.py # Kvartira yaratish, taklif kodi va shablonlar
│   │   ├── templates.py          # 4 ta kvartira shabloni va 11 bosqichli checklist
│   │   ├── chore_service.py      # Round-robin va Juftlik (Pair) rotatsiyasi
│   │   └── fund_service.py       # Yagona umumiy kassa va bozorlik xizmati
│   ├── bot/
│   │   ├── dispatcher.py     # Router va Middleware-larni yig'uvchi Dispatcher
│   │   ├── states/           # FSM holatlari (Kvartira, Navbatchilik, Kassa)
│   │   ├── middlewares/      # DB Session va Foydalanuvchi Auth Middleware-lari
│   │   ├── keyboards/        # Reply va Inline tugmalar
│   │   └── handlers/         # Onboarding, Chores, Expenses (Fund), Admin, Common
│   └── scheduler/
│       └── chore_scheduler.py# Kunlik avtomatik navbatchilik va eslatmalar (Cron)
├── tests/
│   └── test_refactoring.py   # Pytest asinxron testlar to'plami
└── main.py                   # Botni ishga tushirish nuqtasi (Entrypoint)
```

---

## ⚙️ Ishga Tushirish (Docker Compose)

```bash
# 1. Konfiguratsiya
cp .env.example .env

# 2. Docker Compose orqali ishga tushirish
docker compose up --build -d

# 3. Loglarni tekshirish
docker compose logs -f bot
```

---

## 🧪 Testlarni Ishga Tushirish

```bash
pytest tests/ -v
```
