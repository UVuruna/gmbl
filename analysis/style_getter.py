"""
Style Getter - Betting Order Calculator
Generiše betting order na osnovu željenog dobitka po rundi
"""

import betting_stats
from typing import List


DEBUG = False


class BettingStyleCalculator:
    """Kalkulator za betting style na osnovu parametara"""
    
    def __init__(self, max_bet: int = 11000, rounding: int = 5):
        self.max_bet = max_bet
        self.rounding = rounding
    
    def calculate_bet_amount(
        self,
        auto_cashout: float,
        win_per_round: int,
        total_invested: int,
        sequence: int
    ) -> int:
        """
        Računa bet amount za određenu rundu
        
        Formula: ((sequence * win_per_round + total) / (auto - 1) / rounding) * rounding
        
        Args:
            auto_cashout: Auto cashout koeficijent
            win_per_round: Željeni dobitak po rundi
            total_invested: Ukupno uloženo do sada
            sequence: Redni broj runde
            
        Returns:
            int: Zaokružen bet amount
        """
        raw_bet = (sequence * win_per_round + total_invested) / (auto_cashout - 1)
        rounded_bet = round(raw_bet / self.rounding, 0) * self.rounding
        return int(rounded_bet)
    
    def generate_betting_order(
        self,
        auto_cashout: float,
        win_per_round_order: List[int]
    ) -> List[int]:
        """
        Generiše betting order na osnovu željenih dobitaka po rundama
        
        Args:
            auto_cashout: Auto cashout koeficijent
            win_per_round_order: Lista željenih dobitaka po rundama
            
        Returns:
            List[int]: Betting order (lista uloga)
        """
        betting_order = []
        total_invested = 0
        sequence = 0
        
        if DEBUG:
            print(f'Auto cashout: {auto_cashout}, win per round order: {win_per_round_order}')
        
        while True:
            # Uzmi win_per_round za ovu rundu
            win_per_round = (
                win_per_round_order[sequence] 
                if sequence < len(win_per_round_order) 
                else win_per_round_order[-1]
            )
            
            sequence += 1
            
            # Izračunaj bet amount
            bet = self.calculate_bet_amount(
                auto_cashout, 
                win_per_round, 
                total_invested, 
                sequence
            )
            
            # Proveri da li prelazi max
            if bet > self.max_bet:
                break
            
            # Dodaj u betting order
            total_invested += bet
            total_win = bet * auto_cashout - total_invested
            betting_order.append(bet)
            
            if DEBUG:
                print(
                    f"Ulog za rundu: {bet:>6,.0f} | "
                    f"Ukupni dobitak: {total_win:>8,.0f} | "
                    f"po rundi: {total_win / sequence:>4,.1f}"
                )
        
        if DEBUG:
            print('_' * 120)
            print(f'max losses: {len(betting_order)} -- {betting_order}')
        
        return betting_order


def test_betting_styles(
    start_cashout: float = 2.10,
    end_cashout: float = 2.50,
    win_per_round_order: List[int] = None
):
    """
    Testira različite betting style-ove za opseg auto_cashout vrednosti
    
    Args:
        start_cashout: Početna vrednost auto cashout
        end_cashout: Krajnja vrednost auto cashout
        win_per_round_order: Željeni dobici po rundama
    """
    if win_per_round_order is None:
        win_per_round_order = [20, 15, 15, 15, 15, 10, 10, 10, 10, 5]
    
    calculator = BettingStyleCalculator(max_bet=11000, rounding=5)
    
    # Konvertuj u cele brojeve da izbegneš float precision error
    start_int = int(start_cashout * 100)
    end_int = int(end_cashout * 100)
    
    for auto_int in range(start_int, end_int + 1):
        # Konvertuj nazad u float sa tačnom preciznošću
        auto_cashout = round(auto_int / 100, 2)
        
        # Generiši betting order
        betting_order = calculator.generate_betting_order(auto_cashout, win_per_round_order)
        
        # Kreiraj config i analiziraj
        config = betting_stats.BettingConfig(
            bet_order=betting_order,
            auto_cashout=auto_cashout,
            max_loss_streak=len(betting_order),
            full_output=False
        )
        
        betting_stats.main(config)
        
        # Prikaži betting order
        output = '  -  '.join([f'{bet:,.0f}' for bet in betting_order])
        input(f'\t{len(betting_order)}   <<<>>>   {betting_order}   <<<>>>')


if __name__ == '__main__':
    # Parametri za testiranje
    START_CASHOUT = 2.10
    END_CASHOUT = 2.50
    WINNING_ORDER = [20, 15, 15, 15, 15, 10, 10, 10, 10, 5]
    
    test_betting_styles(START_CASHOUT, END_CASHOUT, WINNING_ORDER)