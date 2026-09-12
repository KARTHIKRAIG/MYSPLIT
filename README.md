# MYSPLIT

MYSPLIT is a personal finance tracker built with Python and Flask. It helps users record daily expenses, manage a monthly budget, and view spending reports by category and month.

## Features

- User registration and login
- Add, edit, and delete expenses
- Monthly budget tracking
- Category-wise spending summaries
- Dashboard overview
- Expense reports with charts
- Indian Rupee (₹) currency formatting

## Tech Stack

- Python
- Flask
- SQLite
- HTML/CSS
- Chart.js

## Project Structure

```text
MYSPLIT/
├── app.py
├── requirements.txt
├── expensewise.db
├── static/
│   └── css/
│       └── style.css
├── templates/
│   ├── base.html
│   ├── budget.html
│   ├── dashboard.html
│   ├── expenses.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── reports.html
└── README.md
```

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/KARTHIKRAIG/MYSPLIT.git
   cd MYSPLIT
   ```

2. Create a virtual environment (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate   # On macOS/Linux
   venv\Scripts\activate      # On Windows
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app
   ```bash
   python app.py
   ```

5. Open the app in your browser
   ```text
   http://127.0.0.1:5000
   ```

## Usage

- Register a new account or log in.
- Add your monthly budget.
- Record expenses with category, description, and date.
- View summaries and reports on the dashboard and reports page.

## License

This project is for educational and personal use.
