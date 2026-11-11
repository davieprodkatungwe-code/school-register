# High Profile Private Secondary School – Attendance Register

Digital attendance system for teachers to record student presence/absence, reasons, and whether parents were informed. Generates daily reports for administration.

**School:** High Profile Private Secondary School  
**Colors:** Navy Blue + Sky Blue  
**Hosting target:** Railway

---

## Features

- Teacher login (secure)
- 8 classes: Form 1–4 × Humanities / Sciences
- Mark attendance (Present / Absent) – mobile friendly
- Capture **reason** for every absence
- Record whether the **parent was informed**
- Daily report with totals + full absentee list
- Ready for future WhatsApp / SMS parent notifications

---

## Local Setup (Windows)

1. Make sure you have **Python 3.12 or 3.13** installed (not 3.14).
2. Open Command Prompt in this folder:

```cmd
cd path\to\school_register
```

3. Install packages:

```cmd
pip install -r requirements.txt
```

4. Create database + sample data:

```cmd
python seed_data.py
```

5. Start the system:

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. Open browser: **http://localhost:8000**

### Demo Login

| Role    | Username  | Password    |
|---------|-----------|-------------|
| Admin   | admin     | admin123    |
| Teacher | teacher1  | teacher123  |
| Teacher | teacher2  | teacher123  |

---

## Deploy to Railway (Recommended)

### Step 1 – Create Railway account
Go to https://railway.app and sign up (you can use GitHub).

### Step 2 – Create a new project
- Click **New Project**
- Choose **Deploy from GitHub repo** (recommended) or **Empty Project**

### Step 3 – Push this code to GitHub
1. Create a new repository on GitHub
2. Upload all the files from this `school_register` folder
3. Connect the repository to Railway

### Step 4 – Configure the service
In Railway:
- Add environment variable:
  - `SECRET_KEY` = any long random string (example: `highprofile-school-2026-secret-xyz`)
- The start command is already set in `railway.json` / `Procfile`

### Step 5 – Deploy
Railway will automatically build and deploy.
You will get a public URL like: `https://your-app.up.railway.app`

### Step 6 – Seed the database (first time only)
After the first deploy, open the Railway console (or use a one-time command) and run:

```bash
python seed_data.py
```

---

## Adding Real Students & Teachers Later

You will be able to:
- Add real students class by class
- Create individual teacher accounts with specific usernames
- Change passwords

(We can add a simple Admin page for this when you are ready.)

---

## Project Structure

```
school_register/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── database.py
│   ├── routers/
│   └── templates/
├── seed_data.py
├── requirements.txt
├── Procfile
├── railway.json
└── README.md
```

---

## Future Improvements
- [ ] Admin page to add/edit students and teachers
- [ ] PDF & Excel export of daily reports
- [ ] WhatsApp / SMS notifications to parents
- [ ] Attendance statistics dashboard
