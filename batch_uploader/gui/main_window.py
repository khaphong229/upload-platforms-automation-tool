import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os
from typing import List, Dict, Optional
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor

class MainWindow(tk.Tk):
    def __init__(self, uploader):
        super().__init__()
        
        self.uploader = uploader
        self.title("TikTok Upload Manager")
        self.geometry("1000x700")
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_style()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_widgets()
        self.load_profiles()
        
    def configure_style(self):
        """Configure ttk styles"""
        self.style.configure('TButton', padding=6)
        self.style.configure('TNotebook', tabposition='n')
        self.style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        self.style.configure('Title.TLabel', font=('Helvetica', 14, 'bold'))
        
    def create_widgets(self):
        """Create all UI widgets"""
        # Create main container
        main_container = ttk.Frame(self, padding="10")
        main_container.grid(row=0, column=0, sticky='nsew')
        
        # Header
        header = ttk.Frame(main_container)
        header.pack(fill='x', pady=(0, 10))
        
        ttk.Label(header, text="TikTok Upload Manager", style='Title.TLabel').pack(side='left')
        
        # Create tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Upload Tab
        self.create_upload_tab()
        
        # Profiles Tab
        self.create_profiles_tab()
        
        # Scheduled Uploads Tab
        self.create_scheduled_tab()
        
    def create_upload_tab(self):
        """Create the upload tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Upload")
        
        # Video Selection
        ttk.Label(tab, text="Select Video:", style='Header.TLabel').pack(anchor='w', pady=(10, 5))
        
        video_frame = ttk.Frame(tab)
        video_frame.pack(fill='x', pady=5)
        
        self.video_path = tk.StringVar()
        ttk.Entry(video_frame, textvariable=self.video_path).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(video_frame, text="Browse", command=self.browse_video).pack(side='right')
        
        # Video Preview (placeholder)
        self.preview_frame = ttk.LabelFrame(tab, text="Video Preview")
        self.preview_frame.pack(fill='both', expand=True, pady=10)
        
        # Caption
        ttk.Label(tab, text="Caption:", style='Header.TLabel').pack(anchor='w', pady=(10, 5))
        self.caption_text = tk.Text(tab, height=5, wrap='word')
        self.caption_text.pack(fill='x', pady=5)
        
        # Hashtags
        ttk.Label(tab, text="Hashtags (comma separated):", style='Header.TLabel').pack(anchor='w', pady=(10, 5))
        self.hashtags_entry = ttk.Entry(tab)
        self.hashtags_entry.pack(fill='x', pady=5)
        
        # Upload Button
        ttk.Button(tab, text="Upload Now", command=self.start_upload).pack(pady=20)
        
    def create_profiles_tab(self):
        """Create the profiles management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Profiles")
        
        # Add Profile Button
        ttk.Button(tab, text="Add Profile", command=self.add_profile_dialog).pack(pady=10)
        
        # Profiles List
        self.profiles_list = ttk.Treeview(tab, columns=('name', 'status'), show='headings')
        self.profiles_list.heading('name', text='Profile Name')
        self.profiles_list.heading('status', text='Status')
        self.profiles_list.column('name', width=200)
        self.profiles_list.column('status', width=100)
        self.profiles_list.pack(fill='both', expand=True, pady=10)
        
        # Remove Profile Button
        ttk.Button(tab, text="Remove Selected", command=self.remove_profile).pack(pady=10)
        
    def create_scheduled_tab(self):
        """Create the scheduled uploads tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Scheduled")
        
        # Schedule New Upload Button
        ttk.Button(tab, text="Schedule New Upload", command=self.schedule_upload_dialog).pack(pady=10)
        
        # Scheduled Uploads List
        self.scheduled_list = ttk.Treeview(tab, columns=('time', 'profile', 'status'), show='headings')
        self.scheduled_list.heading('time', text='Scheduled Time')
        self.scheduled_list.heading('profile', text='Profile')
        self.scheduled_list.heading('status', text='Status')
        self.scheduled_list.column('time', width=200)
        self.scheduled_list.column('profile', width=150)
        self.scheduled_list.column('status', width=100)
        self.scheduled_list.pack(fill='both', expand=True, pady=10)
        
    def browse_video(self):
        """Open file dialog to select video"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mov *.avi")]
        )
        if file_path:
            self.video_path.set(file_path)
            self.update_video_preview(file_path)
    
    def update_video_preview(self, video_path):
        """Update the video preview section"""
        # Clear existing preview
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
            
        # Create preview thumbnail (placeholder)
        ttk.Label(
            self.preview_frame, 
            text=f"Video: {os.path.basename(video_path)}\n(Preview will be shown here)",
            justify='center'
        ).pack(expand=True)
    
    def load_profiles(self):
        """Load saved profiles"""
        try:
            profiles = self.uploader.get_profiles()
            for profile in profiles:
                self.profiles_list.insert('', 'end', values=(profile, 'Ready'))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profiles: {str(e)}")
    
    def add_profile_dialog(self):
        """Show dialog to add new profile"""
        dialog = tk.Toplevel(self)
        dialog.title("Add Profile")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Profile Name:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)
        
        def add():
            name = name_entry.get().strip()
            if name:
                try:
                    self.uploader.add_profile(name)
                    self.profiles_list.insert('', 'end', values=(name, 'Ready'))
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add profile: {str(e)}")
        
        ttk.Button(dialog, text="Add", command=add).pack(pady=10)
        name_entry.focus_set()
    
    def remove_profile(self):
        """Remove selected profile"""
        selected = self.profiles_list.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a profile to remove")
            return
            
        profile_name = self.profiles_list.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Remove profile '{profile_name}'?"):
            try:
                self.uploader.delete_profile(profile_name)
                self.profiles_list.delete(selected[0])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove profile: {str(e)}")
    
    def schedule_upload_dialog(self):
        """Show dialog to schedule a new upload"""
        dialog = tk.Toplevel(self)
        dialog.title("Schedule Upload")
        dialog.transient(self)
        dialog.grab_set()
        
        # TODO: Implement scheduling dialog
        ttk.Label(dialog, text="Scheduling will be implemented here").pack(pady=20)
    
    def start_upload(self):
        """Start the upload process"""
        video_path = self.video_path.get()
        caption = self.caption_text.get("1.0", "end-1c")
        hashtags = self.hashtags_entry.get()
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error", "Please select a valid video file")
            return
            
        # Get selected profiles
        selected_profiles = []
        for item in self.profiles_list.get_children():
            if self.profiles_list.item(item, 'values')[0]:  # If profile is selected
                selected_profiles.append(self.profiles_list.item(item, 'values')[0])
        
        if not selected_profiles:
            messagebox.showwarning("No Profiles", "Please select at least one profile")
            return
            
        # Start upload in background
        self.upload_thread = threading.Thread(
            target=self._do_upload,
            args=(selected_profiles, video_path, caption, hashtags)
        )
        self.upload_thread.daemon = True
        self.upload_thread.start()
    
    def _do_upload(self, profiles, video_path, caption, hashtags):
        """Perform upload in background thread"""
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for profile in profiles:
                    future = executor.submit(
                        self.uploader.upload_video,
                        video_path=video_path,
                        caption=caption,
                        hashtags=hashtags,
                        profile_name=profile
                    )
                    futures.append(future)
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        # Update UI with result
                        self.after(0, self._update_upload_status, result)
                    except Exception as e:
                        self.after(0, messagebox.showerror, 
                                 "Upload Error", f"An error occurred: {str(e)}")
            
            self.after(0, messagebox.showinfo, "Complete", "All uploads completed!")
        except Exception as e:
            self.after(0, messagebox.showerror, 
                      "Error", f"Upload failed: {str(e)}")
    
    def _update_upload_status(self, result):
        """Update UI with upload status"""
        # TODO: Implement status updates in the UI
        pass

if __name__ == "__main__":
    from tiktok_uploader.uploader import TikTokUploader
    
    uploader = TikTokUploader()
    app = MainWindow(uploader)
    app.mainloop()
