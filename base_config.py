# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger
from builtins import str

class base_config:
    def __init__ (self, router, name):
        self.router = router
        self.name = ' '.join(name.strip().split()) if isinstance(name, str) else name