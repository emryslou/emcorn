import io

class StringIO(io.StringIO):
    
    @property
    def len(self):
        return len(self.getvalue())
