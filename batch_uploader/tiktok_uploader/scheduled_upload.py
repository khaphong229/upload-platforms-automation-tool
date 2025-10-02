#tiktok_uploader/scheduled-upload.py
import datetime
import json
import os
from pathlib import Path
import schedule
import time
import threading
from queue import Queue

class ScheduledUploader:
    def __init__(self, tiktok_uploader):
        self.uploader = tiktok_uploader
        self.schedule_file = os.path.join(str(Path.home()), '.tiktok_profiles', 'schedules.json')
        self.upload_queue = Queue()
        self.running = False
        
        # Load existing schedules
        self.schedules = self.load_schedules()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
    def load_schedules(self):
        """Load saved upload schedules"""
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def save_schedules(self):
        """Save upload schedules"""
        with open(self.schedule_file, 'w') as f:
            json.dump(self.schedules, f, indent=4)
            
    def add_scheduled_upload(self, profile_name, video_path, caption, hashtags, 
                           schedule_time, repeat=None):
        """Add new scheduled upload"""
        schedule_id = str(int(time.time()))
        
        self.schedules[schedule_id] = {
            'profile': profile_name,
            'video_path': video_path,
            'caption': caption,
            'hashtags': hashtags,
            'schedule_time': schedule_time,
            'repeat': repeat,  # None, 'daily', 'weekly'
            'status': 'pending'
        }
        
        self.save_schedules()
        self._schedule_upload(schedule_id)
        
        return schedule_id
        
    def remove_scheduled_upload(self, schedule_id):
        """Remove scheduled upload"""
        if schedule_id in self.schedules:
            schedule.clear(schedule_id)
            del self.schedules[schedule_id]
            self.save_schedules()
            
    def _schedule_upload(self, schedule_id):
        """Create schedule for upload"""
        upload_data = self.schedules[schedule_id]
        schedule_time = datetime.datetime.strptime(
            upload_data['schedule_time'], 
            '%Y-%m-%d %H:%M:%S'
        )
        
        def upload_job():
            self.upload_queue.put(schedule_id)
            
            # Reschedule if repeat is enabled
            if upload_data['repeat'] == 'daily':
                next_time = schedule_time + datetime.timedelta(days=1)
                upload_data['schedule_time'] = next_time.strftime('%Y-%m-%d %H:%M:%S')
                self.save_schedules()
                self._schedule_upload(schedule_id)
                
            elif upload_data['repeat'] == 'weekly':
                next_time = schedule_time + datetime.timedelta(days=7)
                upload_data['schedule_time'] = next_time.strftime('%Y-%m-%d %H:%M:%S')
                self.save_schedules()
                self._schedule_upload(schedule_id)
        
        # Schedule the job
        schedule.every().day.at(schedule_time.strftime('%H:%M')).do(
            upload_job
        ).tag(schedule_id)
        
    def _run_scheduler(self):
        """Run the scheduler loop"""
        self.running = True
        
        while self.running:
            # Run pending schedules
            schedule.run_pending()
            
            # Process upload queue
            while not self.upload_queue.empty():
                schedule_id = self.upload_queue.get()
                upload_data = self.schedules[schedule_id]
                
                try:
                    # Perform upload
                    success = self.uploader.upload_video(
                        upload_data['video_path'],
                        upload_data['caption'],
                        upload_data['hashtags']
                    )
                    
                    # Update status
                    upload_data['status'] = 'completed' if success else 'failed'
                    upload_data['last_attempt'] = datetime.datetime.now().strftime(
                        '%Y-%m-%d %H:%M:%S'
                    )
                    self.save_schedules()
                    
                except Exception as e:
                    upload_data['status'] = 'failed'
                    upload_data['error'] = str(e)
                    self.save_schedules()
            
            time.sleep(1)
            
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.scheduler_thread.join()