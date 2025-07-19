# Nominex - School Voting Application

This is an offline voting application built for a school that allows a secure and efficient voting process. The app is designed for both voters (students using one-time codes) and administrative staff (headteacher and designated personnel). Voters enter their unique voting code, cast their vote for multiple positions, and view the live results—all without needing a full internet connection.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stacks and Tools](#tech-stacks-and-tools)
- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)

## Overview

The app provides a secure way to manage school elections, preventing double voting with one-time voting codes. It features:
- A landing page where students enter their voting codes.
- A voting interface presenting multiple positions (e.g., Head Boy, Head Girl, Compound Overseers).
- An automatic assignment of assistant roles to the runner-up for each position.
- An admin dashboard that allows creation and management of elections, positions, candidates, and the generation of voting codes.
- Live results pages with real-time visualizations showing vote percentages via horizontal progress bars.

## Features

- **One-Time Voting Codes:** Generated in bulk to secure access for voters.
- **Multiple Positions:** Supports various positions with exactly 2 candidates per position.
- **Live Results Dashboard:** Real-time vote counts with charts and progress bars for each position.
- **Admin Control:** Manage elections, candidates, positions, and voting codes through an intuitive admin panel.
- **Offline Operation:** Designed to run locally (using Flask and XAMPP/phpMyAdmin) without requiring reliable internet connectivity.

## Tech Stacks and Tools

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, Bootstrap
- **Database:** MySQL (managed via phpMyAdmin in a local environment using XAMPP or WAMP)
- **Deployment:** Offline executable setup (with PyInstaller for bundling) or local server setup
- **Additional Tools:** 
  - Random code generation for voting codes
  - Optional export features to generate PDF reports of voting codes and results

## Project Structure

Below is the project tree view for the application:

```
voting_app/
├── database/               # Database configuration and connection setup
├── static/                 # Custom styles and Bootstrap overrides and other assets
├── templates/              # HTML templates
├── main.py                 # Main Flask application with routes
├── pdf.py                  # Pdf Generator (voting codes and results)
├── README.md               # Project documentation (this file)
└── requirements.txt        # Python dependencies

```

## Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/wireduclement/voting-app.git
   cd voting-app
   ```

2. **Set up the virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/MacOS
   venv\Scripts\activate       # Windows
   pip install -r requirements.txt
   ```

3. **Add secret_key in .env file**
   ```bash
   SECRET_KEY=your_secret_key
   ```

4. **Configure MySQL:**
   - Install and run XAMPP/WAMP.
   - Set up your MySQL database.
   - Import the provided schema (located in your schema file or as commands in the README).
   - Adjust `db.py` with your MySQL credentials.

5. **Running the Application:**
   ```bash
   python main.py
   ```
   The app will run locally (e.g., at `http://localhost:5000`).

6. **(Optional) Packaging as an Executable:**
   - Use PyInstaller to create an executable for offline use:
     ```bash
     pyinstaller --onefile main.py
     ```

## Usage

- **Voter Flow:**
  1. Navigate to the landing page.
  2. Enter your one-time voting code.
  3. Vote for your preferred candidates for each position.
  4. View the “Thank You” page after successfully casting your vote.

- **Admin Flow:**
  1. Log in via the admin portal.
  2. Manage positions, candidates, and elections.
  3. Generate and view voting codes.
  4. Monitor live results as votes are cast.
  5. Close election when done to find out the winners
  6. Reset election when needed.

