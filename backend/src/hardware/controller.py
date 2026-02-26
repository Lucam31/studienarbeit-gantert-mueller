import drivers

class Controller:
    def __init__(self, drivers):
        self.drivers = drivers

    # Controller sind higher level und koordinieren die Driver (Logik, (komplexere) Abläufe)