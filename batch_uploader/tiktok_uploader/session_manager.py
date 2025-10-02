"""
Session Manager for TikTok Uploader
Handles session persistence and cookie management
"""
import json
import os
import pickle
import time
from pathlib import Path


class SessionManager:
    def __init__(self, profile_name=None):
        self.profile_name = profile_name
        self.session_dir = Path.home() / '.tiktok_profiles' / 'sessions'
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        if profile_name:
            self.session_file = self.session_dir / f"{profile_name}_session.json"
            self.cookies_file = self.session_dir / f"{profile_name}_cookies.pkl"
        else:
            self.session_file = self.session_dir / "default_session.json"
            self.cookies_file = self.session_dir / "default_cookies.pkl"
    
    def save_session(self, driver):
        """Save session data including cookies and local storage"""
        try:
            # Save cookies
            cookies = driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            # Save session info
            session_data = {
                'url': driver.current_url,
                'timestamp': int(time.time()),
                'profile': self.profile_name
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def load_session(self, driver):
        """Load session data and restore cookies"""
        try:
            if not self.session_file.exists() or not self.cookies_file.exists():
                return False
            
            # Load cookies
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            
            # Navigate to TikTok first
            driver.get('https://www.tiktok.com')
            
            # Add cookies
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Error adding cookie: {e}")
            
            # Refresh to apply cookies
            driver.refresh()
            
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False
    
    def clear_session(self):
        """Clear saved session data"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            if self.cookies_file.exists():
                self.cookies_file.unlink()
            return True
        except Exception as e:
            print(f"Error clearing session: {e}")
            return False