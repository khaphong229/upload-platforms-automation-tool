import os
import threading
import json
from tkinter import *
from tkinter import ttk, messagebox, simpledialog
from .tiktok_uploader.uploader import TikTokUploader, BatchUploadGUI
from concurrent.futures import ThreadPoolExecutor

class Dashboard:
    def __init__(self, root):
        self.root = root
        # Don't set title if root is a Frame
        if hasattr(root, 'title') and callable(getattr(root, 'title')):
            try:
                self.root.title("TikTok Upload Tool")
            except:
                pass  # Ignore if can't set title
        
        # Set geometry only if root is a Tk window
        if hasattr(root, 'geometry') and callable(getattr(root, 'geometry')):
            try:
                self.root.geometry("900x700")
            except:
                pass  # Ignore if can't set geometry
        
        self.setup_variables()
        self.setup_ui()
    
    def setup_variables(self):
        """Initialize variables"""
        self.tiktok_video_path = StringVar()
        self.tiktok_caption = StringVar() 
        self.tiktok_hashtags = StringVar()
        self.profile_configs = {}
        self.selected_accounts = set()
        self.account_configs = {}

    def setup_ui(self):
        """Setup the dashboard UI"""
        # Create main container that works with both Tk and Frame
        if isinstance(self.root, (Tk, Toplevel)):
            main_frame = ttk.Frame(self.root)
            main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        else:
            # Root is already a Frame
            main_frame = self.root

        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(expand=True, fill='both')

        # TikTok Upload tab
        tiktok_frame = self.create_tiktok_tab(notebook)
        notebook.add(tiktok_frame, text="TikTok Uploader")
    
    def create_tiktok_tab(self, notebook):
        frame = ttk.Frame(notebook)
        
        # Video Configuration Frame
        self.config_frame = ttk.LabelFrame(frame, text="Video Configuration")
        self.config_frame.pack(padx=10, pady=5, fill="x")
        self.config_frame.pack_forget()  # Hide initially
        
        # Selected account label
        self.selected_account_label = Label(self.config_frame, text="")
        self.selected_account_label.pack(pady=5)
        
        # Video path
        Label(self.config_frame, text="Video Path:").pack(pady=5)
        self.path_var = StringVar()
        path_entry = Entry(self.config_frame, textvariable=self.path_var, width=50)
        path_entry.pack(pady=5)
        
        def browse_video():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                filetypes=[("Video files", "*.mp4;*.mov;*.avi")]
            )
            if file_path:
                self.path_var.set(file_path)
                
        Button(self.config_frame, text="Browse", command=browse_video).pack()
        
        # Caption
        Label(self.config_frame, text="Caption:").pack(pady=5)
        self.caption_var = StringVar()
        Entry(self.config_frame, textvariable=self.caption_var, width=50).pack(pady=5)
        
        # Hashtags
        Label(self.config_frame, text="Hashtags (comma separated):").pack(pady=5)
        self.hashtags_var = StringVar()
        Entry(self.config_frame, textvariable=self.hashtags_var, width=50).pack(pady=5)
        
        def save_config():
            profile_name = self.selected_account_label.cget("text").replace("Account: ", "")
            if not profile_name:
                return
            
            config = {
                'video_path': self.path_var.get(),
                'caption': self.caption_var.get(),
                'hashtags': [tag.strip() for tag in self.hashtags_var.get().split(',') if tag.strip()]
            }
            
            # Save to profile configs
            self.profile_configs[profile_name] = config
            
            # Save to file using uploader
            uploader = TikTokUploader()
            uploader.set_video_config(profile_name, 
                                    config['video_path'],
                                    config['caption'],
                                    config['hashtags'])
            
            messagebox.showinfo("Success", "Video configuration saved!")
            self.update_profile_list()  # Refresh list to show updated config
            
        Button(self.config_frame, text="Save", command=save_config).pack(pady=10)
        
        # Profile Management Frame
        profile_frame = ttk.LabelFrame(frame, text="Profile Management")
        profile_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Profile list with extended selection mode
        self.profile_listbox = Listbox(profile_frame, selectmode=EXTENDED, height=10)
        self.profile_listbox.pack(side=LEFT, padx=5, pady=5, fill=BOTH, expand=True)
        
        # Profile buttons frame
        profile_buttons = ttk.Frame(profile_frame)
        profile_buttons.pack(side=RIGHT, padx=5, pady=5)
        
        # Add profile button
        Button(profile_buttons, text="Add Profile", command=self.add_new_profile).pack(pady=2)
        
        # Delete profile button
        Button(profile_buttons, text="Delete Profile", command=self.delete_profile).pack(pady=2)
        
        # Configure Video button
        Button(profile_buttons, text="Configure Video", command=self.show_config_frame).pack(pady=2)
        
        # Upload Selected button
        Button(profile_buttons, text="Upload Selected", command=self.start_batch_upload,
               bg="#2D2D2D", fg="white").pack(pady=2)
        
        # Initialize profile configs
        self.profile_configs = {}
        self.load_profile_configs()
        
        self.update_profile_list()
        return frame

    def add_new_profile(self):
        profile_name = simpledialog.askstring("New Profile", "Enter profile name:")
        if profile_name:
            uploader = TikTokUploader()
            try:
                uploader.create_driver(profile_name)
                uploader.manual_login(profile_name)
                messagebox.showinfo("Success", "Profile created successfully!")
                self.update_profile_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create profile: {str(e)}")
            finally:
                if uploader.driver:
                    uploader.driver.quit()

    def delete_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to delete")
            return
            
        profile_name = self.profile_listbox.get(selection[0])
        if messagebox.askyesno("Confirm Delete", f"Delete profile '{profile_name}'?"):
            uploader = TikTokUploader()
            if uploader.delete_profile(profile_name):
                messagebox.showinfo("Success", "Profile deleted successfully!")
                self.update_profile_list()
            else:
                messagebox.showerror("Error", "Failed to delete profile")

    def update_profile_list(self):
        self.profile_listbox.delete(0, END)
        uploader = TikTokUploader()
        profiles = uploader.get_profiles()
        for profile_name in profiles:
            self.profile_listbox.insert(END, profile_name)

    def load_profile_configs(self):
            """Load saved profile configurations"""
            try:
                uploader = TikTokUploader()
                profiles = uploader.get_profiles()
                
                for profile_name in profiles:
                    if profile_name not in self.profile_configs:
                        self.profile_configs[profile_name] = {
                            'video_path': '',
                            'caption': '',
                            'hashtags': []
                        }
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load profile configs: {str(e)}")

    def show_config_frame(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile")
            return
            
        profile_name = self.profile_listbox.get(selection[0])
        
        # Show config frame
        self.config_frame.pack(padx=10, pady=5, fill="x")
        
        # Update selected account label
        self.selected_account_label.config(text=f"Account: {profile_name}")
        
        # Load existing config if any
        existing_config = self.profile_configs.get(profile_name, {})
        self.path_var.set(existing_config.get('video_path', ''))
        self.caption_var.set(existing_config.get('caption', ''))
        hashtags = existing_config.get('hashtags', [])
        self.hashtags_var.set(','.join(hashtags))

    def start_single_upload(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile")
            return
            
        profile_name = self.profile_listbox.get(selection[0])
        uploader = TikTokUploader()
        batch_gui = BatchUploadGUI(uploader)
        batch_gui.root.mainloop()

    def start_batch_upload(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select profiles to upload")
            return
        
        selected_profiles = [self.profile_listbox.get(idx) for idx in selection]
        
        # Validate configurations
        unconfigured = [profile for profile in selected_profiles 
                       if profile not in self.profile_configs or 
                       not self.profile_configs[profile].get('video_path')]
        if unconfigured:
            messagebox.showerror("Error", 
                f"Please configure videos for accounts: {', '.join(unconfigured)}")
            return
        
        # Start upload in separate thread
        threading.Thread(target=self.run_batch_upload, args=(selected_profiles,)).start()

    def run_batch_upload(self, selected_profiles):
        uploader = TikTokUploader()
        max_workers = min(len(selected_profiles), 3)  # Max 3 concurrent uploads
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for profile in selected_profiles:
                config = self.profile_configs[profile]
                future = executor.submit(
                    self.upload_single_account,
                    uploader,
                    profile,
                    config['video_path'],
                    config['caption'],
                    config['hashtags']
                )
                futures.append((future, profile))
            
            # Process results
            for future, profile in futures:
                try:
                    success = future.result()
                    status = "Success" if success else "Failed"
                    print(f"Upload for {profile}: {status}")
                except Exception as e:
                    print(f"Error uploading {profile}: {str(e)}")

    def upload_single_account(self, uploader, profile, video_path, caption, hashtags):
        try:
            driver = uploader.create_driver(profile)
            success = uploader.upload_video_with_driver(
                driver, video_path, caption, hashtags)
            return success
        finally:
            if driver:
                driver.quit()

    def create_table(self):
        table_frame = Frame(self.root, bg="#1E1E1E")
        table_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Headers
        headers = ["#", "username", "password", "cookie", "ip", "status", "action", "video"]
        for i, header in enumerate(headers):
            Label(table_frame, text=header, bg="#1E1E1E", fg="white").grid(
                row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Get profiles from uploader
        uploader = TikTokUploader()
        profiles = uploader.get_profiles()
        
        # Add data rows with checkboxes
        for i, profile_name in enumerate(profiles, 1):
            # Checkbox
            var = BooleanVar()
            chk = Checkbutton(table_frame, bg="#1E1E1E", variable=var,
                            command=lambda p=profile_name, v=var: self.on_account_selected(p, v))
            chk.grid(row=i, column=0, padx=5)
            
            # Profile data
            config = self.account_configs.get(profile_name, {})
            video_path = config.get('video_path', 'Not configured')
            
            data = [
                profile_name,
                "123456@a",
                "msToken=...",
                "",
                "",
                "Bắt đầu",
                os.path.basename(video_path) if video_path != 'Not configured' else 'Not configured'
            ]
            
            for j, value in enumerate(data):
                fg_color = "white"
                if j == 4:  # status
                    fg_color = self.get_status_color(value)
                elif j == 5:  # action
                    fg_color = self.get_action_color(value)
                    
                Label(table_frame, text=value, bg="#1E1E1E", fg=fg_color).grid(
                    row=i, column=j+1, padx=5, pady=2, sticky="w")

    def on_account_selected(self, profile_name, checkbox_var):
        if checkbox_var.get():
            self.selected_accounts.add(profile_name)
        else:
            self.selected_accounts.discard(profile_name)
        self.update_status_bar()

    def configure_selected_videos(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Please select accounts to configure")
            return
            
        # Create configuration window
        config_window = Toplevel(self.root)
        config_window.title("Video Configuration")
        config_window.geometry("500x400")
        
        # Video path
        Label(config_window, text="Video Path:").pack(pady=5)
        path_var = StringVar()
        path_entry = Entry(config_window, textvariable=path_var, width=50)
        path_entry.pack(pady=5)
        
        def browse_video():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                filetypes=[("Video files", "*.mp4;*.mov;*.avi")]
            )
            if file_path:
                path_var.set(file_path)
                
        Button(config_window, text="Browse", command=browse_video).pack()
        
        # Caption
        Label(config_window, text="Caption:").pack(pady=5)
        caption_var = StringVar()
        Entry(config_window, textvariable=caption_var, width=50).pack(pady=5)
        
        # Hashtags
        Label(config_window, text="Hashtags (comma separated):").pack(pady=5)
        hashtags_var = StringVar()
        Entry(config_window, textvariable=hashtags_var, width=50).pack(pady=5)
        
        def save_config():
            config = {
                'video_path': path_var.get(),
                'caption': caption_var.get(),
                'hashtags': [tag.strip() for tag in hashtags_var.get().split(',') if tag.strip()]
            }
            
            for profile in self.selected_accounts:
                self.account_configs[profile] = config
                
            self.save_account_configs()  # Save to file
            config_window.destroy()
            self.create_table()  # Refresh table to show new config
            
        Button(config_window, text="Save", command=save_config).pack(pady=10)

    def save_account_configs(self):
        """Save account configurations to file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'account_configs.json')
        with open(config_path, 'w') as f:
            json.dump(self.account_configs, f, indent=4)

    def load_account_configs(self):
        """Load account configurations from file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'account_configs.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.account_configs = json.load(f)

def main():
    root = Tk()
    app = Dashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
