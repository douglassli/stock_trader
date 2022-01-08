class MissingPositionError(Exception):
    def __init__(self, symb):
        super().__init__(f"Missing position symbol: {symb}")
        self.symb = symb


class PositionAlreadyExistsError(Exception):
    def __init__(self, symb):
        super().__init__(f"Position already exists: {symb}")
        self.symb = symb


class TooManyPositionsError(Exception):
    def __init__(self):
        super().__init__("Too many positions open")


class NotEnoughCashError(Exception):
    def __init__(self):
        super().__init__("Not enough cash to buy stock")
