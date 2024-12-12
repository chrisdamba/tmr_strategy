from typing import Dict


class RiskManager:
    def __init__(self, max_drawdown: float, max_position_size: float):
        self.max_drawdown = max_drawdown
        self.max_position_size = max_position_size

    def check_risk_limits(self, portfolio: Dict) -> bool:
        current_drawdown = portfolio.get('drawdown', 0.0)
        if current_drawdown > self.max_drawdown:
            return False

        total_capital = portfolio.get('total_capital', 100000)
        for pos in portfolio.get('positions', []):
            position_value = pos['quantity'] * pos['price']
            if position_value / total_capital > self.max_position_size:
                return False
        return True
