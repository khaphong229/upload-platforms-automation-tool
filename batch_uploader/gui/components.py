from tkinter import Frame, Label, Checkbutton
from .styles import *

class AccountRow(Frame):
    def __init__(self, parent, data, row_idx, **kwargs):
        super().__init__(parent, bg=DARK_BG, **kwargs)
        
        # Checkbox
        self.checkbox = Checkbutton(self, bg=DARK_BG)
        self.checkbox.grid(row=0, column=0, padx=5, pady=2)
        
        # Data columns
        for col_idx, value in enumerate(data):
            fg_color = WHITE
            
            # Status column styling
            if col_idx == 4:  # status column
                if value == "Đang nhập trình công":
                    fg_color = PURPLE
                elif value == "Chờ đến lượt chạy...":
                    fg_color = ORANGE
            # Action column styling        
            elif col_idx == 5:  # action column
                if value == "Kết thúc":
                    fg_color = RED
                elif value == "Bắt đầu":
                    fg_color = GREEN
                    
            label = Label(self, text=value, bg=DARK_BG, fg=fg_color)
            label.grid(row=0, column=col_idx+1, padx=5, pady=2, sticky="w") 