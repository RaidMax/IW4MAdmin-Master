from datetime import datetime


class BaseModel:
    def __init__(self):
        self.date_created = datetime.utcnow()
        self.date_modified = datetime.utcnow()
        self.is_active = True
