# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# FILE: admin_database.py
# PURPOSE: Manages secure admin authentication and credential storage
# WHY SEPARATE FILE: Keeps password hashing logic separate from API routes for clean architecture
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

# This file handles admin user authentication and credentials
# Stores admin credentials in a SEPARATE database (admin.db) for security
# This way, even if water.db is deleted, admin credentials are preserved

# IMPORTS: Import Python built-in modules for database and path operations
from __future__ import annotations  # WHY: Allows type hints with forward references (for Python 3.7+ compatibility)

import os  # WHY: Used to read environment variables (for custom database path if needed)
import sqlite3  # WHY: SQLite3 library to create/query the admin.db database file
from datetime import datetime, timezone  # WHY: Get current UTC time for created_at and updated_at timestamps
from pathlib import Path  # WHY: Modern way to handle file paths (works cross-platform: Windows/Linux/Mac)
from typing import Optional  # WHY: Type hint for optional parameters (Python best practice)

# IMPORTS: Import external libraries we installed via pip
from passlib.context import CryptContext  # WHY: Library for secure password hashing (PBKDF2-SHA256 algorithm)
from logger_config import get_logger  # WHY: Get logger object to write log messages about authentication events

# CREATE LOGGER INSTANCE
logger = get_logger(__name__)  # WHY: Create a logger for this file (__name__ = "admin_database")
# USAGE: logger.info(), logger.error(), logger.warning() to write logs

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION: Set up paths and password hashing
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent  
# WHY: Get the folder where this file (admin_database.py) is located
# EXAMPLE: C:\Users\shash\OneDrive\Desktop\Water-master

ADMIN_DB_PATH = PROJECT_ROOT / "database" / "admin.db"  
# WHY: Define where admin.db file will be stored
# EXAMPLE: C:\Users\shash\OneDrive\Desktop\Water-master\database\admin.db
# KEY POINT: This is SEPARATE from water.db - so credentials survive if water.db is deleted!

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")  
# WHY: Create password context object for hashing and verifying passwords
# SCHEME: pbkdf2_sha256 = PBKDF2 algorithm with SHA256 hashing (industry standard)
# DEPRECATED: "auto" = automatically handles old password hashes if needed (for future upgrades)
# SECURITY: This object will hash passwords and compare them safely


# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 1: resolve_admin_db_path()
# PURPOSE: Find the admin database path (checking multiple sources)
# WHY SEPARATE FUNCTION: Allows flexibility - test code can use custom path, production uses environment variable or default
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def resolve_admin_db_path(db_path: str | Path | None = None) -> Path:
    # FUNCTION SIGNATURE EXPLANATION:
    # db_path parameter: str | Path | None = None
    #   WHY: Optional parameter that can be:
    #        - str (like "test.db")
    #        - Path object (like Path("test.db"))
    #        - None (meaning "use default or environment variable")
    # RETURN: Path object pointing to database file
    
    """Return the SQLite file path for admin database
    
    This function looks for the database path in this order:
        1. If db_path parameter is given, use that (mainly for tests)
        2. If ADMIN_DB_PATH environment variable is set, use that
        3. Otherwise use the default path (database/admin.db)

    Args:
        db_path: Optional explicit database path

    Returns:
        A Path object pointing to the admin database file
    """
    
    # PRIORITY 1: Check if user provided a path directly (for testing)
    if db_path is not None:
        # WHY: Test code might want to use a temporary database
        # EXAMPLE: pytest calls this with db_path="test_admin.db"
        return Path(db_path)

    # PRIORITY 2: Check if environment variable ADMIN_DB_PATH is set
    env_value = os.getenv("ADMIN_DB_PATH")
    # WHY: Allow Docker/production to override database location via environment variable
    # EXAMPLE: docker run -e ADMIN_DB_PATH="/data/admin.db"
    
    # If environment variable exists, use that path
    if env_value:
        return Path(env_value)

    # PRIORITY 3: Use default path (database/admin.db in project root)
    # WHY: Most common case - use the default location
    return ADMIN_DB_PATH



# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 2: get_admin_connection()
# PURPOSE: Open a connection to the admin database
# WHY SEPARATE FUNCTION: Avoids repeating connection setup code (DRY principle)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def get_admin_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection to the admin database
    
    WHY THIS FUNCTION:
    - Centralizes database connection logic
    - Sets up row factory so results are dictionaries (easier to work with)
    - Creates database folder if it doesn't exist
    
    Args:
        db_path: Optional custom database path

    Returns:
        An active SQLite connection for admin operations
    """
    
    # Step 1: Find the database path (using resolve_admin_db_path function)
    resolved_path = resolve_admin_db_path(db_path)
    # WHY: Use the priority-based path resolution logic we defined above
    
    # Step 2: Create the database folder if it doesn't exist
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    # WHY: SQLite needs the folder to exist before creating the database file
    # parent = C:\Users\shash\OneDrive\Desktop\Water-master\database
    # mkdir(parents=True) = create parent folders too if needed
    # exist_ok=True = don't fail if folder already exists
    
    # Step 3: Open SQLite connection to the database file
    conn = sqlite3.connect(str(resolved_path))
    # WHY: str(resolved_path) converts Path object to string (what sqlite3 expects)
    # RESULT: Now we have an open connection to admin.db
    
    # Step 4: Set row factory - makes results behave like dictionaries
    conn.row_factory = sqlite3.Row
    # WHY: Instead of returning tuples like (1, 'admin@gmail.com', 'hash...'),
    #      return dictionary-like objects: row["id"], row["email"], row["password_hash"]
    # BENEFIT: More readable code - row["email"] instead of row[1]
    
    # Step 5: Return the open connection
    return conn
    # WHY: Caller can now use this connection to execute SQL queries
    # EXAMPLE: cursor = conn.cursor()
    #          cursor.execute("SELECT * FROM admins")



# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 3: hash_password()
# PURPOSE: Convert plain password into a secure hash
# WHY SECURE: Can't reverse hash back to original password (one-way encryption)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256
    
    SECURITY EXPLANATION:
    - Takes a plain password like "pmc"
    - Applies PBKDF2-SHA256 algorithm (260000 iterations)
    - Returns a hash that looks like: $pbkdf2-sha256$260000$salt$hash
    - This hash CANNOT be reversed to get the original password
    - Even if someone steals the database, they can't read passwords
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string (safe to store in database)
    """
    
    # Use passlib's pwd_context to hash the password
    return pwd_context.hash(password)
    # WHY: pwd_context was configured with PBKDF2-SHA256 algorithm at the top of this file
    # WHAT HAPPENS:
    #   1. Takes "pmc" as input
    #   2. Generates random salt (makes same password = different hashes)
    #   3. Applies PBKDF2 algorithm 260000 times (slow = prevents brute force)
    #   4. Returns: "$pbkdf2-sha256$260000$..." (can't be reversed)


# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 4: verify_password()
# PURPOSE: Check if user-entered password matches stored hash
# WHY SEPARATE: Verification is different from hashing - it's the "comparison" step
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password
    
    VERIFICATION PROCESS:
    1. User enters: "pmc"
    2. We have stored hash: "$pbkdf2-sha256$260000$..."
    3. We hash the user's "pmc" using the SAME algorithm and salt
    4. We compare the two hashes - do they match?
    5. Return True if they match, False if they don't
    
    Args:
        plain_password: Plain text password to verify (what user typed)
        hashed_password: Previously hashed password from database (what we stored)
        
    Returns:
        True if passwords match, False otherwise
    """
    
    # Use passlib's pwd_context to verify the password
    return pwd_context.verify(plain_password, hashed_password)
    # WHY: This safely compares the two hashes
    # SECURITY: Uses constant-time comparison (prevents timing attacks)
    # EXAMPLE:
    #   plain_password = "pmc" (user typed)
    #   hashed_password = "$pbkdf2-sha256$260000$..." (from database)
    #   Returns: True if they match, False otherwise



# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 5: initialize_admin_database()
# PURPOSE: Create admin table on first run and add default admin user
# WHY CALLED: Called once when FastAPI app starts (from main.py)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def initialize_admin_database(db_path: str | Path | None = None) -> None:
    """Create admin database tables and add default admin user if needed
    
    WHAT THIS DOES:
    1. First run: Creates "admins" table in admin.db
    2. First run: Creates default admin user (admin@gmail.com / pmc)
    3. Subsequent runs: Does nothing (admin already exists)
    
    WHEN CALLED: Called from main.py on app startup
    WHY NEEDED: Need table to exist before we can validate credentials
    
    This is called once when the app starts to set up the admin database.
    Default admin credentials:
        Email: admin@gmail.com
        Password: pmc (stored as PBKDF2-SHA256 hash, not plain text)
    
    Passwords are hashed using PBKDF2-SHA256 (industry-standard, no external dependencies)
    
    Args:
        db_path: Optional custom database path
    """
    
    # Step 1: Open connection to admin database
    conn = get_admin_connection(db_path)
    # WHY: Need a connection to execute SQL queries
    # RESULT: conn is ready to use
    
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # WHY: cursor is what we use to execute SQL commands
    
    try:
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 2: CREATE ADMINS TABLE IF IT DOESN'T EXIST
        # ════════════════════════════════════════════════════════════════════════════════════
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- WHY id: Unique identifier for each admin user
                -- AUTOINCREMENT: Database generates IDs automatically (1, 2, 3, ...)
                
                email TEXT UNIQUE NOT NULL,
                -- WHY UNIQUE: Only one admin per email (no duplicates)
                -- WHY NOT NULL: Email is required (can't be empty)
                
                password_hash TEXT NOT NULL,
                -- WHY password_hash: Store hashed password, NOT plain password
                -- WHY NOT NULL: Password must exist
                -- FORMAT: $pbkdf2-sha256$260000$salt$hash
                
                created_at TEXT NOT NULL,
                -- WHY: Track when admin user was created
                -- FORMAT: ISO 8601 timestamp (2026-06-09T16:42:22...)
                
                updated_at TEXT NOT NULL
                -- WHY: Track when admin password was last changed
                -- FORMAT: ISO 8601 timestamp
            )
        """)
        # WHY "IF NOT EXISTS": Don't fail if table already exists (idempotent)
        # RESULT: Table is created on first run, ignored on subsequent runs
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 3: CHECK IF DEFAULT ADMIN ALREADY EXISTS
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Query: Does admin@gmail.com already exist in the database?
        cursor.execute("SELECT id FROM admins WHERE email = ?", ("admin@gmail.com",))
        # WHY "SELECT id": We only need to know if it exists (id is smallest)
        # WHY "WHERE email = ?": Find admin with this email address
        # WHY use "?": Prevents SQL injection attacks
        
        admin_exists = cursor.fetchone()
        # WHY fetchone(): Gets first result (or None if no results)
        # RESULT: admin_exists is either a row object (exists) or None (doesn't exist)
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 4: CREATE DEFAULT ADMIN USER ON FIRST RUN ONLY
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # If default admin doesn't exist, create it with default password
        if not admin_exists:
            # WHY "if not admin_exists": Only create on first run
            # SUBSEQUENT RUNS: This condition is False, so we skip this block
            
            # Step 4a: Define default password
            default_password = "pmc"
            # WHY: Initial password when app first starts
            # NOTE: User should change this to something secure!
            
            # Step 4b: Hash the password before storing
            hashed_password = hash_password(default_password)
            # WHY: Never store plain passwords!
            # RESULT: hashed_password = "$pbkdf2-sha256$260000$..."
            
            # Step 4c: Get current UTC timestamp
            now = datetime.now(timezone.utc).isoformat()
            # WHY UTC: Consistent time regardless of server location
            # isoformat(): Converts to string like "2026-06-09T16:42:22.123456+00:00"
            
            # Step 4d: Insert the default admin into the table
            cursor.execute("""
                INSERT INTO admins (email, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, ("admin@gmail.com", hashed_password, now, now))
            # WHY "VALUES (?, ?, ?, ?)": 4 values for 4 columns
            # Values: email, hashed password, creation time, update time
            # WHY "?": Prevents SQL injection (safe way to insert user data)
            
            # Log that we created the default admin
            logger.info("Created default admin user: admin@gmail.com")
            # WHY: Important for debugging - want to know when this happened
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 5: SAVE CHANGES TO DATABASE
        # ════════════════════════════════════════════════════════════════════════════════════
        
        conn.commit()
        # WHY: Save all changes to the database file
        # MUST DO: Without commit(), changes exist only in memory!
        # ANALOGY: Like pressing Ctrl+S to save a document
        
        # Log successful initialization
        logger.info("Admin database initialized successfully")
        # WHY: Confirms the database is ready to use
        
    # ════════════════════════════════════════════════════════════════════════════════════════
    # ERROR HANDLING: If something goes wrong
    # ════════════════════════════════════════════════════════════════════════════════════════
    except Exception as e:
        # Catch any error that occurred
        logger.error(f"Error initializing admin database: {e}")
        # WHY: Log the error so we know what went wrong
        
        # Undo all changes made in this function
        conn.rollback()
        # WHY: If something fails, don't leave database in broken state
        # ROLLBACK: Revert to state before this function started
        
        # Re-raise the exception so calling code knows something failed
        raise
        # WHY: Don't silently ignore errors - let app know it failed
        
    finally:
        # Always execute this, whether success or failure
        conn.close()
        # WHY: Close the database connection
        # IMPORTANT: Must close connections to avoid resource leaks
        # ANALOGY: Like closing a file after reading it



# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 6: validate_admin_credentials()
# PURPOSE: Check if email and password are correct
# WHERE CALLED: Called from /login API endpoint when user tries to log in
# RETURNS: True if credentials match, False otherwise
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def validate_admin_credentials(email: str, password: str) -> bool:
    """Validate admin email and password
    
    THIS IS THE LOGIN VERIFICATION FUNCTION:
    1. User enters email and password in browser
    2. Frontend sends to backend
    3. This function checks: Does this email exist? Does password match?
    4. Return True = login allowed, False = login denied
    
    Args:
        email: Admin email address (what user typed)
        password: Plain text password (what user typed)
        
    Returns:
        True if credentials are valid, False otherwise
    """
    
    # Step 1: Open connection to admin database
    conn = get_admin_connection()
    # WHY: Need to query the database for this email
    
    # Create cursor to execute queries
    cursor = conn.cursor()
    
    try:
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 2: LOOK UP THE ADMIN BY EMAIL ADDRESS
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Find the stored hash for this email address
        cursor.execute("SELECT password_hash FROM admins WHERE email = ?", (email,))
        # WHY "SELECT password_hash": We only need the hash to compare
        # WHY "WHERE email = ?": Find admin with this email
        # WHY "?": Prevents SQL injection
        
        row = cursor.fetchone()
        # WHY fetchone(): Get first matching row (or None if no match)
        # RESULT: row = None (no admin with this email) OR row object with password_hash
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 3: CHECK IF EMAIL EXISTS
        # ════════════════════════════════════════════════════════════════════════════════════
        
        if not row:
            # Email doesn't exist in database
            return False
            # WHY: Wrong email = login failed
            # SECURITY: Don't reveal whether email exists (return same response for both cases)
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 4: GET THE STORED HASH FROM DATABASE
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Extract the password hash from the row
        password_hash = row["password_hash"]
        # WHY: Now we have the stored hash from database
        # EXAMPLE: "$pbkdf2-sha256$260000$salt$hash"
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 5: COMPARE USER'S PASSWORD WITH STORED HASH
        # ════════════════════════════════════════════════════════════════════════════════════
        
        return verify_password(password, password_hash)
        # WHY: Call verify_password() to securely compare
        # WHAT HAPPENS:
        #   1. User typed password = "pmc"
        #   2. Stored hash = "$pbkdf2-sha256$260000$..."
        #   3. Hash "pmc" using same algorithm
        #   4. Compare the two hashes
        #   5. Return True if match, False if not
        # SECURITY: verify_password uses constant-time comparison
        
    # ════════════════════════════════════════════════════════════════════════════════════════
    # ERROR HANDLING: If database query fails
    # ════════════════════════════════════════════════════════════════════════════════════════
    except Exception as e:
        # Something went wrong (database error, connection issue, etc)
        logger.error(f"Error validating credentials: {e}")
        # WHY: Log the error for debugging
        
        return False
        # WHY: If we can't verify, deny login (fail secure)
        # PRINCIPLE: Better to deny access than grant it when unsure
        
    finally:
        # Always execute this, whether success or failure
        conn.close()
        # WHY: Close database connection to free resources



# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FUNCTION 7: update_admin_password()
# PURPOSE: Change admin password (when user wants to update it)
# HOW TO USE: update_admin_password("admin@gmail.com", "newsecurepassword")
# RETURNS: True if password was updated, False if update failed
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def update_admin_password(email: str, new_password: str) -> bool:
    """Update admin password
    
    THIS IS HOW TO CHANGE PASSWORD:
    1. Called when user wants to change password
    2. Takes plain password (what user wants)
    3. Hashes it securely
    4. Stores in database, replacing old password
    5. Old password no longer works!
    
    USAGE EXAMPLE:
    from admin_database import update_admin_password
    success = update_admin_password("admin@gmail.com", "newpassword123")
    
    Args:
        email: Admin email address
        new_password: New plain text password (will be hashed)
        
    Returns:
        True if password updated successfully, False otherwise
    """
    
    # Step 1: Open connection to admin database
    conn = get_admin_connection()
    # WHY: Need connection to update the database
    
    # Create cursor to execute UPDATE query
    cursor = conn.cursor()
    
    try:
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 2: HASH THE NEW PASSWORD
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Convert plain password to hash
        hashed_password = hash_password(new_password)
        # WHY: Never store plain passwords! Always hash first.
        # RESULT: hashed_password = "$pbkdf2-sha256$260000$..."
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 3: GET CURRENT TIMESTAMP
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Get current UTC time
        now = datetime.now(timezone.utc).isoformat()
        # WHY: Update the "updated_at" timestamp to track when password was changed
        # FORMAT: "2026-06-09T16:42:22.123456+00:00"
        # USAGE: Useful for security - know when password was last changed
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 4: UPDATE THE DATABASE
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Update the password_hash for this email
        cursor.execute("""
            UPDATE admins 
            SET password_hash = ?, updated_at = ?
            WHERE email = ?
        """, (hashed_password, now, email))
        # WHY UPDATE: Replace old hash with new hash
        # WHY "password_hash = ?": Set password to the new hash
        # WHY "updated_at = ?": Update the timestamp
        # WHY "WHERE email = ?": Only update this admin's row
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 5: SAVE CHANGES TO DATABASE
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Commit the changes to database
        conn.commit()
        # WHY: Without commit(), changes only exist in memory!
        # ANALOGY: Like pressing Ctrl+S to save
        
        # ════════════════════════════════════════════════════════════════════════════════════
        # STEP 6: CHECK IF UPDATE WAS SUCCESSFUL
        # ════════════════════════════════════════════════════════════════════════════════════
        
        # Return True if at least one row was updated, False if no rows changed
        return cursor.rowcount > 0
        # WHY rowcount: How many rows were affected by the UPDATE
        # EXAMPLES:
        #   - rowcount = 1 → Password was updated successfully → return True
        #   - rowcount = 0 → Email not found → return False
        #   - rowcount = -1 → Database doesn't support rowcount → return False
        
    # ════════════════════════════════════════════════════════════════════════════════════════
    # ERROR HANDLING: If something goes wrong
    # ════════════════════════════════════════════════════════════════════════════════════════
    except Exception as e:
        # Something went wrong (database error, etc)
        logger.error(f"Error updating password: {e}")
        # WHY: Log the error for debugging
        
        # Undo changes made in this function
        conn.rollback()
        # WHY: If something failed, don't leave database in broken state
        # ROLLBACK: Revert to state before update started
        
        return False
        # WHY: Return False to indicate update failed
        
    finally:
        # Always execute this, whether success or failure
        conn.close()
        # WHY: Close database connection to free resources
        # IMPORTANT: Must always close connections


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# END OF FILE: admin_database.py
# 
# SUMMARY OF FUNCTIONS:
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 1. resolve_admin_db_path()         → Find database path (test/env/default)
# 2. get_admin_connection()          → Open connection to admin.db
# 3. hash_password()                 → Convert "pmc" to "$pbkdf2-sha256$..."
# 4. verify_password()               → Check if user password matches stored hash
# 5. initialize_admin_database()     → Create table and default admin on first run
# 6. validate_admin_credentials()    → Verify email/password at login time
# 7. update_admin_password()         → Change password to something new
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
