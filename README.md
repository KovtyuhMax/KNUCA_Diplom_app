# Warehouse Management System

## Overview
A comprehensive Warehouse Management System (WMS) designed to streamline warehouse operations, inventory management, and order processing. The system provides a complete solution for managing warehouse activities including receiving, storage, picking, and shipping.

## Features

- **User Authentication**: Role-based access control with different positions (Operator, Manager, etc.)
- **Inventory Management**: Track and manage inventory levels in real-time
- **Storage Management**: Organize warehouse storage locations and track item placement
- **Order Processing**: Handle supplier and customer orders efficiently
- **Picking Operations**: Optimize the picking process with location assignments
  - Picking from level 1 locations (picking zones)
  - Automatic replenishment of picking locations from higher-level storage
  - Tracking of picking operations (SKU, SSCC, quantity, weight, picking location)
  - Automatic order status updates after complete picking
- **TSD (Terminal Data Collection) Support**: Mobile terminal emulation for warehouse operations
- **Barcode Support**: SSCC barcode generation and scanning
- **Customer Management**: Maintain customer information and orders
- **Supplier Management**: Track supplier information and contracts
- **Reporting**: Generate inventory reports, stock levels, and analytics
- **Logistics Data Management**: Manage packaging data for logistics operations
- **Chatbot Integration**: AI assistance for warehouse operations

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 4
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF, WTForms
- **Migrations**: Flask-Migrate, Alembic
- **Containerization**: Docker, Docker Compose
- **Environment Management**: python-dotenv

## Project Structure

```
├── app.py                  # Main application file with routes and configuration
├── run.py                  # Application runner with migration handling
├── manage.py               # Flask CLI commands for database management
├── init_db.py              # Database initialization and initial data creation
├── extensions.py           # Flask extensions initialization
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker configuration for PostgreSQL
├── .env                    # Environment variables for configuration
├── forms/                  # Form definitions for data input
├── models/                 # Database models (SQLAlchemy)
├── routes/                 # Route handlers organized by feature
├── services/               # Business logic services
├── static/                 # Static assets (CSS, JS, images)
│   ├── css/                # Stylesheets
│   └── js/                 # JavaScript files
├── templates/              # HTML templates
└── utils/                  # Utility functions and helpers
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose
- pip (Python package manager)

### Setup

1. Clone the repository

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Unix/Linux
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Start PostgreSQL database:

   **Option 1: Using Docker** (recommended):
   ```
   docker-compose up -d
   ```

   **Option 2: Without Docker** (using local PostgreSQL installation):
   1. Install PostgreSQL on your system:
      - Windows: Download and install from [official PostgreSQL website](https://www.postgresql.org/download/windows/)
      - Linux: Use your distribution's package manager (e.g., `sudo apt install postgresql postgresql-contrib`)
   
   2. Create database and user:
      - Open PostgreSQL command line (psql):
        ```
        # Windows (run as administrator)
        psql -U postgres
        
        # Linux
        sudo -u postgres psql
        ```
      - Create user and database:
        ```sql
        CREATE USER warehouse_user WITH PASSWORD 'warehouse_password';
        CREATE DATABASE warehouse_db;
        GRANT ALL PRIVILEGES ON DATABASE warehouse_db TO warehouse_user;
        ```

5. Set up environment variables by creating or modifying the `.env` file with the following content:

   **For Docker setup**:
   ```
   POSTGRES_USER=warehouse_user
   POSTGRES_PASSWORD=warehouse_password
   POSTGRES_DB=warehouse_db
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   DATABASE_URL=postgresql://warehouse_user:warehouse_password@localhost:5432/warehouse_db
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   FLASK_DEBUG=True
   SECRET_KEY=your_secret_key
   ```

   **For local PostgreSQL setup** (adjust host, port, and credentials if needed):
   ```
   POSTGRES_USER=warehouse_user
   POSTGRES_PASSWORD=warehouse_password
   POSTGRES_DB=warehouse_db
   POSTGRES_HOST=localhost  # or your PostgreSQL server address
   POSTGRES_PORT=5432       # or your PostgreSQL port
   DATABASE_URL=postgresql://warehouse_user:warehouse_password@localhost:5432/warehouse_db
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   FLASK_DEBUG=True
   SECRET_KEY=your_secret_key
   ```

6. Initialize the database and migrations:

   **For both Docker and local PostgreSQL setup**:
   ```
   python init_db.py
   ```
   
   > **Note for local PostgreSQL setup**: Verify that the PostgreSQL server is running and available with the connection parameters specified in the `.env` file before initializing the databases.

## Running the Application

### Development Mode

```
python run.py
```

The application will be available at http://localhost:5000

   > **NOTE**This file automatically imports app from app.py and includes all routes, extensions, and middleware. It also performs initialization on startup. It is used during local development.

### Using Flask CLI

```
python manage.py run
```

### Running Without Docker

#### Option 1: Using Local PostgreSQL

If you have set up a local PostgreSQL database (Option 2 in the installation section):

1. Make sure the PostgreSQL server is running:
   - Windows: Check that the PostgreSQL service is running in Services (services.msc)
   - Linux: `sudo systemctl status postgresql`

2. Check the database connection:
   ```
   psql -U warehouse_user -d warehouse_db -h localhost
   ```

3. Run the application using one of the methods described above (Development Mode or Using Flask CLI).

> **Note**: When running without Docker, make sure all dependencies are installed (`pip install -r requirements.txt`) and the environment variables in the `.env` file are set correctly for your local PostgreSQL database.

#### Option 2: Using SQLite (without installing PostgreSQL)

If you don't want to install PostgreSQL, you can use SQLite as an alternative:

1. Change the environment variables in the `.env` file:
   ```
   DATABASE_URL=sqlite:///warehouse.db
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   FLASK_DEBUG=True
   SECRET_KEY=your_secret_key
   ```

2. Initialize the SQLite database and create migrations:
   ```
   python manage.py db init    # Initialize migrations (first time only)
   python manage.py db migrate  # Creating a migration
   python manage.py db upgrade  # Applying migration
   ```

3. Create the initial data:
   ```
   python init_db.py
   ```

4. Launch the app:
   ```
   python run.py
   ```

> **Примітка**: When using SQLite, some features that depend on PostgreSQL's specific capabilities may not work correctly. SQLite is recommended for development and testing purposes only.

## Database Migrations

The project uses Flask-Migrate for database migrations:

```
python manage.py db init    # Initialize migrations (first time only)
python manage.py db migrate  # Generate migration
python manage.py db upgrade  # Apply migration
```

## Default Credentials

After initializing the database, you can log in with the following credentials:

- Username: 1612
- Password: admin123

## Key Modules

### Storage Management
Manage warehouse storage locations, rows, and zones. The system supports hierarchical storage organization with different levels and types of storage locations.

### Inventory Management
Track inventory levels, movements, and stock status. Provides real-time visibility into inventory across the warehouse.

### Order Processing
Handle supplier orders for receiving goods and customer orders for shipping. Supports different order types and statuses.

### Picking Operations
Manage the picking process with optimized location assignments. Features include:
- Picking from level 1 locations (picking zones)
- Automatic replenishment of picking locations from higher-level storage
- Tracking of picking operations (SKU, SSCC, quantity, weight, picking location)
- Automatic order status updates after complete picking (status changes to 'packed')

### TSD Operations
Emulate terminal data collection devices for warehouse operations, including receiving, picking, and validation processes.

### Reporting
Generate inventory reports, stock levels, and analytics. Includes low stock alerts and inventory value calculations.

## Environment Variables

All database connection settings are stored in the `.env` file. Default values are:

- `POSTGRES_USER`: warehouse_user
- `POSTGRES_PASSWORD`: warehouse_password
- `POSTGRES_DB`: warehouse_db
- `POSTGRES_HOST`: localhost
- `POSTGRES_PORT`: 5432
- `FLASK_HOST`: 0.0.0.0
- `FLASK_PORT`: 5000
- `FLASK_DEBUG`: True

## License

This project is proprietary software.

## Contact

For support or inquiries, please contact the project maintainer.