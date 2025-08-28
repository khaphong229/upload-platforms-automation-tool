from tkinter import *
from tkinter import ttk
from .styles import *
from .components import AccountRow
from core.account import AccountManager

class Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("MainWindow")
        self.root.geometry("900x600")
        self.root.configure(bg=DARK_BG)
        
        self.account_manager = AccountManager()
        self.setup_ui()
        
    def setup_ui(self):
        # Settings header
        settings_label = Label(self.root, text="Settings", **HEADER_STYLE)
        settings_label.pack(padx=10, pady=5, anchor="w")
        
        # Add Accounts button
        add_btn = Button(self.root, text="Add Accounts", 
                        command=self.add_accounts,
                        **BUTTON_STYLE)
        add_btn.pack(pady=5)
        
        # Create table
        self.create_table()
        
        # Status bar
        self.status_label = Label(self.root, 
                                text="Tổng tài khoản tiktok: 8 | Đã chọn: 2",
                                **HEADER_STYLE)
        self.status_label.pack(padx=10, pady=5, anchor="w")
        
    def create_table(self):
        table_frame = Frame(self.root, bg=DARK_BG)
        table_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Headers
        headers = ["#", "username", "password", "cookie", "ip", "status", "action"]
        for i, header in enumerate(headers):
            Label(table_frame, text=header, **TABLE_HEADER_STYLE).grid(
                row=0, column=i, sticky="w")
        
        # Sample data (replace with real data later)
        sample_data = [
            ("user227728", "123456@a", "msToken=n...", "171.232.31.200", "Đang nhập trình công", "Kết thúc"),
            ("user580019", "123456@a", "msToken=b...", "171.227.31.200", "Chờ đến lượt chạy...", "Kết thúc"),
            ("user661615", "123456@a", "odin_tt=fac...", "", "", "Bắt đầu"),
            # ... more rows ...
        ]
        
        # Add data rows
        for i, data in enumerate(sample_data, 1):
            AccountRow(table_frame, data, i).grid(row=i, column=0, columnspan=7, sticky="ew")
            
    def add_accounts(self):
        # Implement account addition logic
        pass
        
    def update_status_bar(self):
        total = self.account_manager.get_total_count()
        selected = self.account_manager.get_selected_count()
        self.status_label.config(
            text=f"Tổng tài khoản tiktok: {total} | Đã chọn: {selected}") 