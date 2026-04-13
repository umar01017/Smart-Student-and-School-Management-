# Smart Student Management System

A production-ready web application built with Python Flask, MongoDB, and Bootstrap 5.

## Features
- **Admin Panel**: Manage students and teachers, view global attendance analytics (Charts), manage users.
- **Teacher Panel**: View assigned students, mark/update attendance, dashboard stats.
- **Student Portal**: View attendance percentages, history, visual analytics, update profile, and download PDF reports.
- **Security**: Session-based authentication, Role-based route protection, Password hashing.
- **UI/UX**: Responsive Premium dashboards, interactive Chart.js widgets.

## Step-by-Step Setup Instructions

### 1. Install Libraries
Open your terminal/command prompt and navigate to the project folder, then run:
```bash
pip install -r requirements.txt
```

### 2. Start MongoDB
Ensure MongoDB is installed on your system.
- **Windows**: MongoDB typically runs as a background service. You can start it from Services or run `mongod` in your terminal.
- The app expects MongoDB to be running at `mongodb://localhost:27017/`. (You can change this in `config.py`).

### 3. Run Flask
In your terminal, within the project folder, start the application:
```bash
python app.py
```
The application will be running at `http://127.0.0.1:5000/`.

### 4. How to Test Login
Open `http://127.0.0.1:5000/` in your web browser.

**Testing Flow**
1. Click on **Register**.
2. Fill out the details. Under "Account Role", select *Administrator* to create an Admin account.
3. Log in with the Admin credentials. You will be redirected to the Admin Dashboard.
4. From the Admin Dashboard, use the "Students" and "Teachers" tabs to add Test Students and Teachers.
5. Log out, then log in using the newly created Teacher credentials. 
6. Navigate to the "Mark Attendance" section to log attendance.
7. Log out, then log in using the Student credentials to view the generated attendance graphs and download a PDF report!

Enjoy exploring the Smart Student Management System!
