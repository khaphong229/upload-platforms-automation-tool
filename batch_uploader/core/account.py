class Account:
    def __init__(self, username, password, cookie="", ip=""):
        self.username = username
        self.password = password
        self.cookie = cookie
        self.ip = ip
        self.status = ""
        self.action = "Bắt đầu"
        
class AccountManager:
    def __init__(self):
        self.accounts = {}
        self.selected_accounts = set()
        
    def add_account(self, username, password, cookie="", ip=""):
        self.accounts[username] = Account(username, password, cookie, ip)
        
    def select_account(self, username, selected=True):
        if selected:
            self.selected_accounts.add(username)
        else:
            self.selected_accounts.remove(username)
            
    def update_status(self, username, status):
        if username in self.accounts:
            self.accounts[username].status = status
            
    def get_total_count(self):
        return len(self.accounts)
        
    def get_selected_count(self):
        return len(self.selected_accounts) 