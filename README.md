# 🏠 Tartibli Xonadosh (Talabalar Kvartira Boshqaruvi)
### *Multi-Tenant Flatmate, Chore, Rules & Communal Fund Management Telegram Bot*

Toshkent shahridagi talabalar turar joylari (TTJ), ijarada birga yashovchi talabalar va xonadoshlar (2–10 kishi) uchun dinamik qoidalar, navbatchilik (oshxona, 10L suv, haftalik 11 bosqichli tozalash, kunlik/juftlik navbatlari) va umumiy kassa zaxirasini (bozorlik, yig'imlar) avtomatlashtirilgan, shaffof va adolatli boshqarish platformasi.

---

## 🚀 Texnologik Stek

- **Dasturlash tili & Freymvork:** Python 3.11+, [Aiogram 3.15+](https://docs.aiogram.dev/) (Modern Asynchronous Telegram Bot Framework)
- **Ma'lumotlar bazasi & ORM:** PostgreSQL 16, [SQLAlchemy 2.0 (asyncio + asyncpg)](https://docs.sqlalchemy.org/)
- **Migratsiyalar:** [Alembic](https://alembic.sqlalchemy.org/)
- **FSM & Kesh:** Redis 7 (Aiogram `RedisStorage`)
- **Vazifalar rejalashtiruvchisi (Cron/Scheduler):** [APScheduler 3.x](https://apscheduler.readthedocs.io/) (AsyncIOScheduler, Asia/Tashkent)
- **Konteynerizatsiya:** Docker & Docker Compose (Oracle Cloud Always Free Ubuntu 24.04 ga moslangan)

---

## 📜 Dinamik Kvartira Qoidalari Boshqaruvi (Dynamic Rules)

- **`FlatRule` modeli:** Har bir kvartira uchun shaxsiy, tartiblangan uy qoidalari (`id`, `flat_id`, `order_num`, `title`, `content`).
- **Foydalanuvchi ko'rinishi:** `📜 Kvartira Qoidalari` tugmasi barcha xonadoshlarga toza formatlangan HTML ko'rinishida qoidalar ro'yxatini taqdim etadi.
- **Admin boshqaruvi:**
  * `➕ Yangi qoida qo'shish`: FSM dialogi (Sarlavha ➔ Mazmuni ➔ Saqlash).
  * `🗑 Qoidani o'chirish`: Keraksiz yoki eskirgan qoidalarni inline tugma orqali xavfsiz o'chirish.
  * `🔄 Standart qoidalarni tiklash`: Shablon bo'yicha 4 ta asosiy qoidani (22:30 sukunat, Dish Policy, mehmonlar, jarimalar) qayta tiklash.

---

## 🛠 Kengaytirilgan Navbatchilik va Jadval Sozlamalari (Duty Scheduler)

1. **📅 Kunlik navbatchi biriktirish (Hafta kunlari bo'yicha):**
   - Admin har bir vazifa uchun haftaning muayyan kunlariga (Dushanba..Yakshanba) aniq xonadoshni biriktirishi mumkin (`assigned_weekdays`).
   - Tizim har kuni belgilangan navbatchini avtomatik tanlaydi.
2. **👥 Juftliklarni shakllantirish (Paired Rotation):**
   - Haftalik katta tozalash (11 bosqichli checklist) va og'ir vazifalar uchun 2 kishilik jamoalar tuziladi (`assigned_pairs`).
   - Bot har hafta navbatni avtomatik ravishda keyingi juftlikka o'tkazadi.
3. **➕ Yangi maxsus vazifa qo'shish:**
   - Admin o'zi xohlagan davriy (`DAILY`, `WEEKLY`, `CUSTOM`) vazifalarni yaratishi mumkin.
4. **📋 Vazifalar nazorati (Toggle & Delete):**
   - Istalgan vazifani vaqtincha to'xtatish (pause) yoki bazadan butunlay o'chirish imkoniyati.

---

## 🏢 Multi-Tenant Kvartira Shablonlari (Presets)

1. **🏢 Katta Kvartira (`LARGE_FLAT`, 6–10 kishi):**
   - **Kunlik oshxona va idishlar:** Ovqat tayyorlash, non, dasturxonni yig'ishtirish, qozon va umumiy idishlarni yuvish, chiqindini to'kish.
   - **10L toza suv navbatchiligi:** Filtrlangan 10L toza suv baklajkalarini olib kelish va suv zaxirasini to'ldirish.
   - **Haftalik katta tozalash (Juftlik navbati - 2 kishi):** 11 bosqichli to'liq tozalash checklisti.
   - **Kir yuvish navbati:** Kiryuvish mashinasidan navbat bilan foydalanish va kiyimlarni yuvish grafigi.

2. **🏠 Ixcham Kvartira (`COMPACT_FLAT`, 2–5 kishi):**
   - Kunlik oshxona tozaligi, chiqindini olib chiqish, polni supurish va nam artish.

3. **🛏 TTJ / Yotoqxona (`DORMITORY`):**
   - Xona tozaligi, chiqindi navbatchiligi, 22:30 tinchlik soati nazorati.

4. **⚙️ Shaxsiy (`CUSTOM`):**
   - Bo'sh shablon (admin o'zi belgilaydi).

---

## 💰 Yagona Umumiy Kassa va Bozorlik Tizimi (Communal Fund)

- **`flat.fund_balance` (Numeric 12, 2):** Kvartiraning umumiy pul zaxirasi.
- **`📥 Pul yig'ish`:** Har bir a'zodan teng miqdorda yig'iladi va har bir kishi uchun `INCOME` operatsiyasi yoziladi.
- **`🧾 Xarid kiritish`:** Bozorlik cheki kiritilganda (masalan, 370 293 so'm), kassa balansidan tiyinigacha aniq chegiriladi (qoldiq: 29 707 so'm) va `EXPENSE` operatsiyasi qayd etiladi.
- **`💰 Kassa balansi`:** Joriy kassa qoldig'i, jami kirim va jami chiqim hisoboti.
- **`📜 Xaridlar tarixi`:** Oxirgi 5 ta kassa amaliyati tafsilotlari.

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
│   └── versions/             # DB schema versiyalari (0001, 0002)
├── app/
│   ├── config.py             # Pydantic Settings
│   ├── database/
│   │   ├── base.py           # DeclarativeBase va TimestampMixin
│   │   └── session.py        # Async Engine, SessionMaker, DB Init
│   ├── models/
│   │   ├── user.py           # User modeli
│   │   ├── flat.py           # Flat (template_type, fund_balance, quiet_hours)
│   │   ├── rule.py           # FlatRule (Dinamik qoidalar)
│   │   ├── chore.py          # Chore (weekdays, pairs, frequency_type, checklist)
│   │   └── fund.py           # FundTransaction (INCOME, EXPENSE, balance_after)
│   ├── repositories/
│   │   ├── user_repo.py      # Foydalanuvchi ma'lumotlari
│   │   ├── flat_repo.py      # Kvartira va a'zolar ombori
│   │   ├── rule_repo.py      # Dinamik qoidalar ombori
│   │   ├── chore_repo.py     # Navbatchilik vazifalari
│   │   └── fund_repo.py      # Kassa va xaridlar ombori
│   ├── services/
│   │   ├── onboarding_service.py # Kvartira yaratish, taklif kodi va shablonlar
│   │   ├── rule_service.py       # Dinamik qoidalar boshqaruvi
│   │   ├── templates.py          # 4 ta kvartira shabloni va 11 bosqichli checklist
│   │   ├── chore_service.py      # Hafta kunlari va Juftliklar rotatsiyasi
│   │   └── fund_service.py       # Yagona umumiy kassa va bozorlik xizmati
│   ├── bot/
│   │   ├── dispatcher.py     # Router va Middleware-larni yig'uvchi Dispatcher
│   │   ├── states/           # FSM holatlari (Kvartira, Navbatchilik, Kassa, Qoidalar)
│   │   ├── middlewares/      # DB Session va Foydalanuvchi Auth Middleware-lari
│   │   ├── keyboards/        # Reply va Inline tugmalar (admin, chores, fund, flat)
│   │   └── handlers/         # Onboarding, Chores, Expenses (Fund), Admin, Common
│   └── scheduler/
│       └── chore_scheduler.py# Kunlik avtomatik navbatchilik va eslatmalar (Cron)
├── tests/
│   ├── test_refactoring.py   # Presets, Fund va Pair rotatsiyasi testlari
│   └── test_rules_and_admin_chores.py # Qoidalar va kunlik/juftlik jadvali testlari
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
PYTHONPATH=. pytest tests/ -v
```
