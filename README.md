# Python Django Server Setup Guide

## Getting Started with Your Environment

To ensure a clean and organized setup, it's highly recommended to use a local virtual environment for managing your project's dependencies.

### Creating a Virtual Environment

Initiate the following command in your project's root directory to establish a virtual environment:

```bash
python -m venv myproject
```

This command is required only once to create the virtual environment.

### Activating the Virtual Environment

Each time you begin working on your project, activate the virtual environment with:

```bash
source myproject/bin/activate
```

It's advisable to install all necessary packages within this virtual environment. Ensure you're in the directory containing your virtual environment folder before activating it.

### Deactivating the Virtual Environment

To exit the virtual environment, simply run:

```bash
deactivate
```

## Installing Required Packages

Before installing any packages, make sure your virtual environment is active. Follow the steps above to activate it.

Install the necessary packages listed in `requirements.txt` by running:

```bash
sudo apt-get install libpq-dev
pip install -r requirements.txt
```

**Note:** The `psycopg2` package might cause installation issues within a virtual environment. If you encounter such errors, install `psycopg2` outside the virtual environment first, then proceed with installing the remaining packages inside the virtual environment.

## Running the Backend Server

It's important to start the backend server before launching the frontend server located in a different directory.

### Apply Migrations

Run the following command to apply database migrations:

```bash
python manage.py migrate
```

### Create Cache Table for Development

To set up a cache table for development, execute:

```bash
python manage.py createcachetable
```

---

Enjoy your development journey!