# MRI Finding App

## Project Setup


### 1. Create a virtual environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Create a `.env` file in the project root:

```env
HOST=localhost
PORT=3306
USER=root
PASSWORD=your_password
DATABASE_NAME=mri_radiology_db

APP_HOST=127.0.0.1
APP_PORT=5000

FORCE_ETL=0
```

Replace `USER` and `PASSWORD` with your MySQL credentials.

### 4. Add the dataset

Make sure the dataset is placed in the following structure:

```text
Data Raw/
├── Radiologists Report.xlsx
└── 01_MRI_Data/
```

### 5. Start the project

Run:

```bash
python main.py
```

The `main.py` script will automatically:

1. Create the database if it does not exist.
2. Initialize the database schema.
3. Install the stored procedures.
4. Run the ETL pipeline and load the data.
5. Start the Flask application.

After the application starts, open:

```text
http://127.0.0.1:5000
```

### 6. Run the project again

If the data has already been loaded
You must change the CONSTANT :RUN_DATABASE_SETUP RUN_SCHEMA_SETUP RUN_PROCEDURE_SETUP RUN_ETL to false in main.py

After that you can run the web by:

```bash
python main.py
```

The ETL process will be skipped by default.


### 7. Stop the application

Press:

```text
Ctrl + C
```
