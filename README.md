# 🐍🚀 Python Django Server Setup Guide 🚀🐍

Welcome to the Django Server Setup Guide! Follow these steps to smoothly set up and manage your development environment.

## 🌟 Getting Started with Your Environment

Ensure a clean and organized setup by using a virtual environment for managing your project's dependencies.

### 🌱 Creating a Virtual Environment

In your project's root directory, initiate the virtual environment with:

```bash
python -m venv myproject
```

This is a one-time command to create the virtual environment.

### ⚡ Activating the Virtual Environment

Every time you start working on your project, activate the virtual environment using:

```bash
source myproject/bin/activate
```

Ensure you are in the correct directory containing your virtual environment folder before activating it.

### ❌ Deactivating the Virtual Environment

To exit the virtual environment, simply run:

```bash
deactivate
```

## 📦 Installing Required Packages

Before installing any packages, activate your virtual environment as shown above. Then install the necessary packages listed in `requirements.txt` by running:

```bash
sudo apt-get install libpq-dev
pip install -r requirements.txt
```

**Note:** If you encounter installation issues with the `psycopg2` package within a virtual environment, install `psycopg2` outside the virtual environment first, then proceed with installing the remaining packages inside the virtual environment.

## 🌐 Running the Backend Server

Start the backend server before launching the frontend server. Here's how:

### 🛠️ Apply Migrations

Run the following command to apply database migrations:

```bash
python manage.py migrate
```

### ⚙️ Create Cache Table for Development

Set up a cache table for development with:

```bash
python manage.py createcachetable
```

---

### Enjoy your development journey! 🚀👨‍💻👩‍💻