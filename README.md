# 🧥 Uniform Detection

## 🚀 Clone the Repository

```bash
git clone https://github.com/7078-cj/Uniform-Detection.git
```

---

## 🔧 Backend Setup

1. Create a virtual environment (make sure Python and `virtualenv` are installed):
   ```bash
   virtualenv env
   ```

2. Activate the virtual environment:
   - On **Windows**:
     ```bash
     env\Scripts\activate
     ```
   - On **Linux/macOS**:
     ```bash
     source env/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. In the `backend` folder, create a `.env` file:
   ```bash
   cd backend
   touch .env
   ```

5. Add the following to the `.env` file:
   ```env
   EMAIL_HOST_USER=your-email@example.com
   EMAIL_HOST_PASSWORD=your-email-password-or-app-password
   ```

   > 🔐 *Use an app password if you're using a Google account. You can [learn how to create one here](https://support.google.com/accounts/answer/185833?hl=en).*

6. Run the backend server:
   ```bash
   python manage.py runserver
   ```

---

## 🌐 Frontend Setup

1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the frontend development server:
   ```bash
   npm run dev
   ```

---

## ✅ You're all set!

- Backend: [http://localhost:8000](http://localhost:8000)
- Frontend: [http://localhost:5173](http://localhost:5173) *(default Vite port)*

