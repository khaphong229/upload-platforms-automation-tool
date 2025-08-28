#tiktok_uploader/uploader.py
import os
import time
import json
import shutil
import tempfile
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from tkinter import messagebox, Tk, Listbox, Button, MULTIPLE, Frame, Label, Entry, END

class BatchUploadGUI:
    def __init__(self, uploader):
        self.uploader = uploader
        self.root = Tk()
        self.root.title("TikTok Batch Uploader")
        self.root.geometry("600x800")
        
        # Video details
        self.video_path = ""
        self.caption = ""
        self.hashtags = []
        
        # Selected profiles
        self.selected_profiles = []
        
        self.create_gui()

    def create_gui(self):
        # Video Details Frame
        video_frame = Frame(self.root)
        video_frame.pack(pady=10, padx=10, fill="x")
        
        Label(video_frame, text="Video Path:").pack()
        self.video_entry = Entry(video_frame, width=50)
        self.video_entry.pack()
        Button(video_frame, text="Browse", command=self.browse_video).pack()
        
        Label(video_frame, text="Caption:").pack()
        self.caption_entry = Entry(video_frame, width=50)
        self.caption_entry.pack()
        
        Label(video_frame, text="Hashtags (comma separated):").pack()
        self.hashtags_entry = Entry(video_frame, width=50)
        self.hashtags_entry.pack()
        
        # Profile Selection Frame
        profile_frame = Frame(self.root)
        profile_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        Label(profile_frame, text="Select Profiles:").pack()
        self.profile_listbox = Listbox(profile_frame, selectmode=MULTIPLE, height=10)
        self.profile_listbox.pack(fill="both", expand=True)
        
        # Load profiles
        self.load_profiles()
        
        # Buttons Frame
        button_frame = Frame(self.root)
        button_frame.pack(pady=10, padx=10)
        
        Button(button_frame, text="Start Batch Upload", command=self.start_batch_upload).pack(side="left", padx=5)
        Button(button_frame, text="Cancel", command=self.root.quit).pack(side="left", padx=5)
        
        # Status Frame
        self.status_frame = Frame(self.root)
        self.status_frame.pack(pady=10, padx=10, fill="x")
        
        self.status_label = Label(self.status_frame, text="Ready")
        self.status_label.pack()

    def load_profiles(self):
        profiles = self.uploader.get_profiles()
        for profile_name in profiles:
            self.profile_listbox.insert(END, profile_name)

    def browse_video(self):
        from tkinter import filedialog
        self.video_path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4;*.mov;*.avi")]
        )
        self.video_entry.delete(0, END)
        self.video_entry.insert(0, self.video_path)

    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update()

    def start_batch_upload(self):
        # Get selected profiles
        selected_indices = self.profile_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "Please select at least one profile")
            return
            
        self.selected_profiles = [self.profile_listbox.get(idx) for idx in selected_indices]
        
        # Get video details
        video_path = self.video_entry.get()
        caption = self.caption_entry.get()
        hashtags = [tag.strip() for tag in self.hashtags_entry.get().split(',') if tag.strip()]
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error", "Please select a valid video file")
            return
            
        # Start batch upload in a separate thread
        threading.Thread(target=self.run_batch_upload, 
                        args=(video_path, caption, hashtags)).start()

    def run_batch_upload(self, video_path, caption, hashtags):
        self.update_status("Starting batch upload...")
        
        # Create a thread pool for parallel uploads
        with ThreadPoolExecutor(max_workers=min(len(self.selected_profiles), 3)) as executor:
            # Submit upload tasks
            future_to_profile = {
                executor.submit(
                    self.upload_for_profile, 
                    profile_name, 
                    video_path, 
                    caption, 
                    hashtags
                ): profile_name for profile_name in self.selected_profiles
            }
            
            # Process results as they complete
            for future in as_completed(future_to_profile):
                profile_name = future_to_profile[future]
                try:
                    success = future.result()
                    status = "Success" if success else "Failed"
                    self.update_status(f"Profile {profile_name}: {status}")
                except Exception as e:
                    self.update_status(f"Profile {profile_name}: Error - {str(e)}")
        
        self.update_status("Batch upload completed!")
        messagebox.showinfo("Complete", "Batch upload process has finished!")

    def upload_for_profile(self, profile_name, video_path, caption, hashtags):
        try:
            self.update_status(f"Starting upload for profile {profile_name}...")
            
            # Create new driver instance for this profile
            driver = None
            try:
                driver = self.uploader.create_driver(profile_name)
                
                # Check login status and perform login if needed
                driver.get('https://www.tiktok.com/upload')
                time.sleep(3)
                
                if 'login' in driver.current_url.lower():
                    self.update_status(f"Login required for profile {profile_name}")
                    if not self.uploader.manual_login(profile_name):
                        raise Exception("Login failed")
                
                # Perform upload with the specific driver
                success = self.uploader.upload_video_with_driver(driver, video_path, caption, hashtags)
                
                return success
                
            except Exception as e:
                print(f"Error uploading for profile {profile_name}: {e}")
                return False
            finally:
                # Always cleanup the driver
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        except Exception as e:
            print(f"Critical error for profile {profile_name}: {e}")
            return False

    

    def run(self):
        self.root.mainloop()

class TikTokUploader:
    def __init__(self, base_dir=None):
        # Use user's home directory for profiles instead of temp directory
        if base_dir is None:
            base_dir = os.path.join(str(Path.home()), '.tiktok_profiles')
        
        self.profiles_dir = base_dir
        self.driver = None
        self.wait = None
        self.current_profile = None
        
        # Ensure base directory exists
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        # Create profiles index file
        self.profiles_file = os.path.join(self.profiles_dir, 'profiles.json')
        if not os.path.exists(self.profiles_file):
            self.save_profiles_index({})
        
        self.config_file = os.path.join(self.profiles_dir, 'video_configs.json')
        self.load_configs()

    def get_unique_profile_path(self, profile_name):
        """Generate a unique profile path"""
        base_path = os.path.join(self.profiles_dir, profile_name)
        path = base_path
        counter = 1
        
        while os.path.exists(path):
            path = f"{base_path}_{counter}"
            counter += 1
            
        return path

    def create_driver(self, profile_name=None):
        """Create Chrome WebDriver with optional profile"""
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        if profile_name:
            self.current_profile = profile_name
            profiles = self.get_profiles()
            
            if profile_name in profiles:
                profile_path = profiles[profile_name]['path']
            else:
                profile_path = self.get_unique_profile_path(profile_name)
                # Add new profile to index immediately
                self.add_profile(profile_name, profile_path)
            
            # Ensure profile directory exists
            os.makedirs(profile_path, exist_ok=True)
            
            # Add profile arguments
            chrome_options.add_argument(f'--user-data-dir={profile_path}')
            chrome_options.add_argument('--profile-directory=Default')
            
            # Add persistence flags
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_argument('--password-store=basic')
            chrome_options.add_argument('--enable-profile-shortcut-manager')

        service = Service(ChromeDriverManager().install())
        
        try:
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            return self.driver
        except Exception as e:
            if profile_name and "user data directory is already in use" in str(e).lower():
                # Kill any existing Chrome processes
                os.system('taskkill /f /im chrome.exe')
                time.sleep(2)
                # Retry with same profile
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.wait = WebDriverWait(self.driver, 30)
                return self.driver
            raise e

    def get_profiles(self):
        """Get list of saved profiles"""
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_profiles_index(self, profiles):
        """Save profiles index"""
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(profiles, f, indent=4)
        except Exception as e:
            print(f"Error saving profiles index: {e}")

    def add_profile(self, profile_name, profile_path=None):
        """Add new profile"""
        profiles = self.get_profiles()
        if profile_path is None:
            profile_path = self.get_unique_profile_path(profile_name)
        
        profiles[profile_name] = {
            'path': profile_path,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.save_profiles_index(profiles)
        return profile_path

    def delete_profile(self, profile_name):
        """Delete a Chrome profile"""
        profiles = self.get_profiles()
        if profile_name in profiles:
            profile_path = profiles[profile_name]['path']
            try:
                # Force close any running Chrome instances
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                # Delete profile directory
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path, ignore_errors=True)
                
                # Remove from index
                del profiles[profile_name]
                self.save_profiles_index(profiles)
                return True
            except Exception as e:
                print(f"Error deleting profile: {e}")
                return False
        return False


    def manual_login(self, profile_name):
        """Manual login process with profile saving"""
        try:
            self.driver.get('https://www.tiktok.com/login')
            messagebox.showinfo("Login Required", 
                "Please login to TikTok in the browser window.\n"
                "After logging in, click OK to continue.")
            
            # Wait for login completion and verify
            time.sleep(5)
            self.driver.get('https://www.tiktok.com/upload')
            time.sleep(3)
            
            # Check if we're still on login page
            current_url = self.driver.current_url
            if 'login' in current_url.lower():
                raise Exception("Login failed or incomplete")
            
            # Save the profile
            if profile_name not in self.get_profiles():
                self.add_profile(profile_name)
                
            return True
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def restore_session(self):
        """Restore previous session"""
        self.driver.get('https://www.tiktok.com')
        
        session_data = self.load_session()
        if session_data:
            for cookie in session_data:
                self.driver.add_cookie(cookie)
            
            self.driver.refresh()

    def get_video_details(self):
        """Interactive video details input"""
        while True:
            video_path = input("Enter full video path: ").strip()
            if os.path.exists(video_path) and video_path.lower().endswith(('.mp4', '.mov', '.avi')):
                break
            print("Invalid file path. Please check the file.")

        caption = input("Enter video caption (optional): ").strip()
        hashtags_input = input("Enter hashtags separated by comma (optional): ").strip()
        hashtags = [tag.strip() for tag in hashtags_input.split(',')] if hashtags_input else None

        return video_path, caption, hashtags

    def upload_video(self, video_path, caption='', hashtags=None):
        """Upload video to TikTok"""
        try:
            # First verify login status
            self.driver.get('https://www.tiktok.com/upload')
            time.sleep(3)
            
            # Check if redirected to login page
            if 'login' in self.driver.current_url.lower():
                raise Exception("Not logged in")

            # Look for file input
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(os.path.abspath(video_path))
            time.sleep(5)

            if caption or hashtags:
                caption_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
                )
                caption_input.send_keys(Keys.CONTROL, 'a')
                caption_input.send_keys(Keys.BACKSPACE)
                if caption:
                    caption_input.send_keys(caption)

                if hashtags:
                    hashtag_str = ' '.join([f'#{tag}' for tag in hashtags])
                    caption_input.send_keys(f' {hashtag_str}')

            # Scroll to make sure the Post button is in view
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Give time for any animations to complete

            # Try multiple possible button selectors
            post_button_selectors = [
                "//button[contains(text(), 'Post')]",
                "//button[contains(@class, 'post-button')]",
                "//button[contains(@class, 'submit')]",
                "//div[contains(@class, 'post-button')]//button",
                "//button[.//span[contains(text(), 'Post')]]"
            ]

            post_button = None
            for selector in post_button_selectors:
                try:
                    post_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue

            if not post_button:
                raise Exception("Could not find Post button")

            # Try JavaScript click if regular click fails
            try:
                post_button.click()
            except:
                self.driver.execute_script("arguments[0].click();", post_button)

            # Wait for upload completion - look for success indicator or new URL
            try:
                success_wait = WebDriverWait(self.driver, 30)
                success_wait.until(lambda driver: 
                    'upload' not in driver.current_url.lower() or
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'success')]"))
                )
            except:
                print("Warning: Could not confirm upload completion")

            return True

        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def upload_for_profile(self, profile_name, video_path, caption, hashtags):
        try:
            self.update_status(f"Starting upload for profile {profile_name}...")
            
            # Create new driver instance for this profile
            driver = None
            try:
                driver = self.uploader.create_driver(profile_name)
                
                # Check login status and perform login if needed
                driver.get('https://www.tiktok.com/upload')
                time.sleep(3)
                
                if 'login' in driver.current_url.lower():
                    self.update_status(f"Login required for profile {profile_name}")
                    if not self.uploader.manual_login(profile_name):
                        raise Exception("Login failed")
                
                # Perform upload with the specific driver
                success = self.uploader.upload_video_with_driver(driver, video_path, caption, hashtags)
                
                return success
                
            except Exception as e:
                print(f"Error uploading for profile {profile_name}: {e}")
                return False
            finally:
                # Always cleanup the driver
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        except Exception as e:
            print(f"Critical error for profile {profile_name}: {e}")
            return False

    # Add this new method to TikTokUploader class
    def upload_video_with_driver(self, driver, video_path, caption='', hashtags=None):
        """Upload video to TikTok using a specific driver instance"""
        try:
            wait = WebDriverWait(driver, 30)
            
            # First verify login status
            driver.get('https://www.tiktok.com/upload')
            time.sleep(3)
            
            # Check if redirected to login page
            if 'login' in driver.current_url.lower():
                raise Exception("Not logged in")

            # Look for file input
            file_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(os.path.abspath(video_path))
            time.sleep(5)

            if caption or hashtags:
                caption_input = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
                )
                caption_input.send_keys(Keys.CONTROL, 'a')
                caption_input.send_keys(Keys.BACKSPACE)
                if caption:
                    caption_input.send_keys(caption)

                if hashtags:
                    hashtag_str = ' '.join([f'#{tag}' for tag in hashtags])
                    caption_input.send_keys(f' {hashtag_str}')

            # Scroll to make sure the Post button is in view
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Give time for any animations to complete

            # Try multiple possible button selectors
            post_button_selectors = [
                "//button[contains(text(), 'Post')]",
                "//button[contains(@class, 'post-button')]",
                "//button[contains(@class, 'submit')]",
                "//div[contains(@class, 'post-button')]//button",
                "//button[.//span[contains(text(), 'Post')]]"
            ]

            post_button = None
            for selector in post_button_selectors:
                try:
                    post_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue

            if not post_button:
                raise Exception("Could not find Post button")

            # Try JavaScript click if regular click fails
            try:
                post_button.click()
            except:
                driver.execute_script("arguments[0].click();", post_button)

            # Wait for upload completion - look for success indicator or new URL
            try:
                success_wait = WebDriverWait(driver, 30)
                success_wait.until(lambda d: 
                    'upload' not in d.current_url.lower() or
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'success')]"))
                )
            except:
                print("Warning: Could not confirm upload completion")

            return True

        except Exception as e:
            print(f"Upload failed: {e}")
            return False        

    def run_interactive_upload(self):
        """
        Interactive workflow for uploading a video
        """
        # Create or restore driver
        if not self.driver:
            self.driver = self.create_driver()

        # Try to restore session, if fails, do manual login
        try:
            self.restore_session()
        except:
            self.manual_login()

        # Get video details interactively
        video_path, caption, hashtags = self.get_video_details()

        # Upload video
        upload_success = self.upload_video(video_path, caption, hashtags)
        
        # Close browser after upload
        if self.driver:
            self.driver.quit()

        return upload_success
    def batch_upload(self):
        """Start the batch upload GUI"""
        gui = BatchUploadGUI(self)
        gui.run()

    def load_configs(self):
        """Load video configurations"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.video_configs = json.load(f)
            else:
                self.video_configs = {}
        except:
            self.video_configs = {}

    def save_configs(self):
        """Save video configurations"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.video_configs, f, indent=4)
        except Exception as e:
            print(f"Error saving configs: {e}")

    def set_video_config(self, profile_name, video_path, caption='', hashtags=None):
        """Set video configuration for a profile"""
        self.video_configs[profile_name] = {
            'video_path': video_path,
            'caption': caption,
            'hashtags': hashtags or []
        }
        self.save_configs()

    def get_video_config(self, profile_name):
        """Get video configuration for a profile"""
        return self.video_configs.get(profile_name, {})

# Interactive script
if __name__ == "__main__":
    # uploader = TikTokUploader()
    # uploader.run_interactive_upload()
    uploader = TikTokUploader()
    uploader.batch_upload()