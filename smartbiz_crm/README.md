# SmartBiz CRM — Flask + SQLite MVP

A runnable web application based on the MVP described in Deliverable 2.

## Included features
- Customer records: add, list, edit, search and delete
- Sales opportunities: record values in UGX and update stages (Lead, Proposal, Negotiation, Won, Lost)
- Follow-up tasks: create, view, complete/reopen and delete
- Dashboard: customer count, won sales value, active pipeline value, open/overdue follow-ups
- Reports: sales opportunity count and value grouped by stage
- Responsive layout for desktop and mobile browsers

## Requirements
- Python 3.10 or newer
- pip

## Run on Windows
1. Extract `smartbiz_crm.zip`.
2. Open Command Prompt or PowerShell in the extracted `smartbiz_crm` folder.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

4. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the application:

   ```powershell
   py app.py
   ```

6. Open `http://127.0.0.1:5000` in your browser.

## Run on macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then visit `http://127.0.0.1:5000`.

## Database
On first run, the application creates `smartbiz.db` in the project folder and creates the required SQLite tables automatically. Keep this file to retain your records. Back it up before moving or deleting the project.

To use a different database location, set the `SMARTBIZ_DATABASE` environment variable to the desired file path.

## Important project scope and security
This is an academic MVP, not a production-ready service. In line with Deliverable 2, authentication/login, complaint tracking, automated SMS/email reminders, and CSV/PDF exports are not implemented in this version. It has no user accounts or role permissions. Run it locally for demonstration with fictional data only; do not enter real customer personal information or expose the development server to the public internet. Before deployment, add authentication, CSRF protection, secure secret management, HTTPS, authorization, backups and appropriate privacy controls.

The Flask development server is for local testing only. Do not use `debug=True` on a public server.
