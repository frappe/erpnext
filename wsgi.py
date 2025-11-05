"""
WSGI Configuration for Frappe Framework
Used by Gunicorn to run the application
"""

import os
import sys
from pathlib import Path
import frappe
application = frappe.app

# Add the app directory to the path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Set up Django/Frappe environment
os.environ.setdefault('FRAPPE_ENV', os.getenv('FRAPPE_ENV', 'production'))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

# Import Frappe application
try:
    from frappe.app import application
    
    # Log that the application was loaded
    print(f"✅ Frappe application loaded successfully")
    print(f"   Environment: {os.getenv('FRAPPE_ENV')}")
    print(f"   Site Name: {os.getenv('SITE_NAME')}")
    
except ImportError as e:
    print(f"❌ Error loading Frappe application: {e}")
    print(f"   Make sure frappe-framework is installed")
    
    # Fallback application
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'text/html')]
        start_response(status, headers)
        return [b'<h1>Error: Frappe not loaded</h1>']

# Add health check endpoint
if hasattr(application, '__call__'):
    original_app = application
    
    def app_with_health(environ, start_response):
        """Add health check endpoint"""
        path = environ.get('PATH_INFO', '').lower()
        
        if path in ['/api/health', '/health', '/healthz']:
            status = '200 OK'
            headers = [
                ('Content-Type', 'application/json'),
                ('Content-Length', '18'),
            ]
            start_response(status, headers)
            return [b'{"status":"healthy"}']
        
        # Otherwise, use the original application
        return original_app(environ, start_response)
    
    application = app_with_health

if __name__ == '__main__':
    print("This is a WSGI application. Use Gunicorn to run it:")
    print("  gunicorn --config gunicorn.conf.py wsgi:application")
