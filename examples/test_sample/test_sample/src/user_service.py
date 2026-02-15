"""User service module - handles user operations."""
import json
import os

# Security issue: Hardcoded secret
API_KEY = "sk-1234567890abcdef1234567890abcdef"

# Performance issue: No caching
user_cache = {}

def get_user(user_id):
    """Get user by ID."""
    # No input validation
    # N+1 query pattern
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    # Security issue: SQL injection possible
    result = execute_query(query)
    
    # No error handling
    user = result[0]
    
    return user

def get_all_users():
    """Get all users - potential performance issue."""
    users = []
    # N+1 query pattern
    for user_id in get_user_ids():
        user = get_user(user_id)  # Individual query per user!
        users.append(user)
    return users

def execute_query(sql):
    """Execute SQL query - security risk."""
    # Missing: connection pooling, timeout, error handling
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(sql)  # Direct execution - SQL injection!
    result = cursor.fetchall()
    conn.close()
    return result

def get_user_ids():
    """Get all user IDs."""
    result = execute_query("SELECT id FROM users")
    return [row[0] for row in result]

def process_data(data):
    """Process data - generic name."""
    # Magic values
    if len(data) > 100:
        return data[:100]
    return data

def handle_request(request):
    """Handle request - another generic name."""
    # No validation
    user_id = request.get('user_id')
    
    # Silent failure
    if not user_id:
        return None
    
    # No logging
    user = get_user(user_id)
    
    # Logs sensitive data
    print(f"User data: {user}")
    
    return user

# Unused function
def unused_helper():
    """This function is never called."""
    pass

# Dead code
if False:
    print("This will never execute")

class UserManager:
    """Generic class name - semantics issue."""
    
    def __init__(self):
        self.data = []
    
    def process(self, item):
        """Generic method name."""
        # State spaghetti
        self.data.append(item)
        self.data = sorted(self.data)
        self.data = list(set(self.data))
        return self.data
    
    def do_something(self):
        """Empty semantic name."""
        pass

# Infinite loop risk
def risky_loop(items):
    """Function with potential infinite loop."""
    i = 0
    while i < len(items):
        # Missing i increment!
        if items[i] == "stop":
            break
        print(items[i])
    return items

# Blocking call without timeout
def fetch_external_data(url):
    """Fetch data from external API."""
    import urllib.request
    # No timeout, no error handling
    response = urllib.request.urlopen(url)
    return response.read()
