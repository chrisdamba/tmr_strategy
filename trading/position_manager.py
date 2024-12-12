class PositionManager:
    def __init__(self, max_positions, allocation_per_trade):
        self.max_positions = max_positions
        self.allocation_per_trade = allocation_per_trade

    def calculate_position_size(self, price, available_capital):
        if price <= 0:
            return 0
        shares = int(min(self.allocation_per_trade, available_capital) / price)
        return max(shares, 0)
