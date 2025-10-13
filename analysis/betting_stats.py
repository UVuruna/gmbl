"""
Betting Statistics Analyzer
Analizira CSV logove klađenja i prikazuje statistiku performansi
"""

import pandas as pd
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class BettingConfig:
    """Konfiguracija betting sistema"""
    bet_order: List[int]
    auto_cashout: float
    max_loss_streak: int
    full_output: bool


@dataclass
class BookmakerStats:
    """Statistika za jednog bookmaker-a"""
    name: str
    total_rounds: int
    total_balance: float
    max_loss_amount: float
    max_loss_count: int
    big_losses: int
    hours_played: float
    money_needed: float
    

class BettingStatsAnalyzer:
    """Glavni analizator betting statistike"""
    
    def __init__(self, config: BettingConfig):
        self.config = config
        self.risk_amount = sum(config.bet_order[:config.max_loss_streak])
        
        # Globalne statistike
        self.total_rounds = 0
        self.total_balance = 0
        self.total_hours = 0
        self.total_big_losses = 0
        self.total_wins = 0
        
        # Praćenje dobitaka
        self.win_min = float('inf')
        self.win_max = 0
        self.money_needed_per_bookmaker: Dict[str, float] = {}
        
        # Brojač dobitaka po broju gubitaka pre pobede
        self.wins_counter = {str(i): 0 for i in range(1, config.max_loss_streak + 1)}
        self.wins_counter[f'{config.max_loss_streak + 1}+'] = 0
    
    def load_csv(self, path: str) -> List[Dict]:
        """Učitaj CSV i konvertuj u listu dictionary-ja"""
        df = pd.read_csv(f"documentation/logs/{path}.csv", keep_default_na=True)
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    
    def analyze_bookmaker(self, bookmaker_name: str) -> BookmakerStats:
        """Analiziraj podatke za jedan bookmaker"""
        bet_table = self.load_csv(bookmaker_name)
        
        # Početne vrednosti
        total_balance = 0
        current_bet_index = 0
        current_loss = 0
        current_loss_counter = 0
        
        # Praćenje maksimalnih gubitaka
        max_loss_amount = 0
        max_loss_count = 0
        big_losses = 0
        
        # Praćenje vremena
        total_time = 0
        
        # Inicijalizuj money_needed ako nije već
        if bookmaker_name not in self.money_needed_per_bookmaker:
            self.money_needed_per_bookmaker[bookmaker_name] = 0
        
        for i, bet in enumerate(bet_table):
            # Čitaj vreme i skor
            total_time = int(bet['sec']) if bet['sec'] is not None else 0
            score = float(bet['score'])
            bet_amount = self.config.bet_order[current_bet_index]
            
            # Uplati ulog
            total_balance -= bet_amount
            
            # Proveri da li je dobitak
            if score > self.config.auto_cashout:
                win_amount = bet_amount * self.config.auto_cashout
                total_balance += win_amount
                
                # Ažuriraj min/max dobitke
                self.win_max = max(self.win_max, win_amount)
                self.win_min = min(self.win_min, win_amount)
                
                # Brojač dobitaka
                counter_key = str(min(current_loss_counter + 1, self.config.max_loss_streak))
                if current_loss_counter >= self.config.max_loss_streak:
                    counter_key = f'{self.config.max_loss_streak + 1}+'
                self.wins_counter[counter_key] += 1
                
                self.total_wins += 1
                current_loss = 0
                current_bet_index = 0
                current_loss_counter = 0
            else:
                # Gubitak
                current_loss += bet_amount
                current_bet_index += 1
                current_loss_counter += 1
                
                # Proveri da li smo dostigli max
                if current_bet_index == self.config.max_loss_streak:
                    big_losses += 1
                current_bet_index %= self.config.max_loss_streak
            
            # Ažuriraj maksimalne gubitke
            if current_loss > max_loss_amount:
                max_loss_amount = current_loss
                max_loss_count = current_loss_counter
            
            # Prati najniži balans (potreban kapital)
            if total_balance < self.money_needed_per_bookmaker[bookmaker_name]:
                self.money_needed_per_bookmaker[bookmaker_name] = total_balance
            
            # Periodični ispis (svakih ~20 minuta)
            if total_time != 0 and total_time % 1800 < 20:
                if self.config.full_output is True:
                    self._print_progress(
                        bookmaker_name, total_balance, max_loss_amount, 
                        max_loss_count, big_losses, total_time
                    )
        
        # Ažuriraj globalne statistike
        self.total_rounds += i + 1
        self.total_balance += total_balance
        self.total_big_losses += big_losses
        hours = total_time / 3600
        self.total_hours = max(self.total_hours, hours)
        
        return BookmakerStats(
            name=bookmaker_name,
            total_rounds=i + 1,
            total_balance=total_balance,
            max_loss_amount=max_loss_amount,
            max_loss_count=max_loss_count,
            big_losses=big_losses,
            hours_played=hours,
            money_needed=abs(self.money_needed_per_bookmaker[bookmaker_name])
        )
    
    def _print_progress(self, bookmaker: str, total: float, max_loss: float, 
                       max_count: int, big_losses: int, time_sec: int):
        """Prikaži trenutni progres"""
        print(
            f"{bookmaker:<10}    |    "
            f"Total: {total:>10,.0f}    |    "
            f"Max gubitak: {max_loss:>6,.0f} ({max_count:>2,.0f})    |    "
            f"Veliki gubici: {big_losses:>3,.0f}  | "
            f"Vreme: {time_sec/60:>7.2f} min"
        )
    
    def print_bookmaker_summary(self, stats: BookmakerStats):
        """Prikaži finalni summary za bookmaker"""
        if self.config.full_output is True:
            print('_' * 120)
            print(
                f"{stats.total_rounds:<10,.0f}    |    "
                f"Total: {stats.total_balance:>10,.0f}    |    "
                f"Max gubitak: {stats.max_loss_amount:>6,.0f} ({stats.max_loss_count:>2,.0f})    |    "
                f"Veliki gubici: {stats.big_losses:>3,.0f}  | "
                f"Vreme: {stats.hours_played * 60:>7.2f} min"
            )
            print('_' * 120)
            
        final = (
            f'\t*** STATS {stats.name.upper()}:'.ljust(24) +
            f'total = {stats.total_balance:,.0f} RSD'.ljust(22) +
            f'din/h: {stats.total_balance/stats.hours_played:,.0f} RSD'.ljust(22) +
            f'Money needed: {stats.money_needed:,.0f} RSD ***'.ljust(22)
        )
        
        if self.config.full_output is True:
            print(final)
            print('\n')
            
        return final
    
    def print_final_summary(self, bookmaker_summaries: List[str]):
        """Prikaži finalni summary svih bookmaker-a"""
        print('\n')
        print('*' * 120)
        for summary in bookmaker_summaries:
            print(summary)
        print('*' * 120)
        print()
        
        # Prikaži raspodelu dobitaka
        filtered_wins = {k: v for k, v in self.wins_counter.items() if v > 0}
        wins_count_str = ''
        wins_percent_str = ''
        wins_visual_str = ''
        percent_bar_length = 300
        
        for k, v in filtered_wins.items():
            wins_count_str += f"{k}. {v:,.0f}".ljust(8) + " | "
        
        title_axis = ''
        jump = percent_bar_length // 50 # 50% max
        for i in range(2, 51, 2):
            txt = f'{i}%|'
            br = int(jump - len(txt))
            title_axis += ' '*br+txt
            
        for k, v in filtered_wins.items():
            percentage = (v/self.total_wins)*100
            wins_percent_str += f"{k}. {percentage:,.1f}%".ljust(8) + " | "
            
            # Vizuelna reprezentacija sa █ karakterom
            bar_length = int(round(percentage*percent_bar_length/100))  # 1% = 1 karakter
            bar = '█' * bar_length
            wins_visual_str += f"{k}.".ljust(4) + f"= {bar}" + "\n"
        
        total_money_needed = abs(sum(self.money_needed_per_bookmaker.values()))
        
        final = (
            f'\tROUNDS = {self.total_rounds:,.0f}  |  '
            f'TOTAL = {self.total_balance:,.0f} RSD  |  '
            f'HOURS: {self.total_hours:,.2f}h  |  '
            f'din/h: {self.total_balance/self.total_hours:,.0f} RSD  |  '
            f'STYLE: max: {self.config.max_loss_streak}, auto: {self.config.auto_cashout:,.2f}'
            f'\n\n\tRISK: {self.risk_amount:,.0f} RSD - '
            f'count: {self.total_big_losses:,.0f}  |  '
            f'WINS: ({self.win_min:,.0f} RSD : {self.win_max:,.0f} RSD) - '
            f'count: {self.total_wins:,.0f} ({100*self.total_wins/self.total_rounds:,.1f}%)  |  '
            f'Money needed: {total_money_needed:,.0f} RSD'
            f'\n\nAll WINS:  {wins_count_str[:-3]}'
            f'\n           {wins_percent_str[:-3]}'
            f'\n      {'_'*(percent_bar_length//2)}'
            f'\n      {title_axis}'
            f'\n{wins_visual_str[:-1]}'  # Ukloni poslednji \n
        )
        
        print(final)
        print()
        print('*' * 84)


def main(config: BettingConfig):  
    # Bookmaker-i za analizu
    bookmakers = ['admiral', 'balkanbet', 'merkur', 'soccer']
    
    # Kreiraj analizator
    analyzer = BettingStatsAnalyzer(config)
    
    # Analiziraj sve bookmaker-e

    summaries = []
    for bookmaker in bookmakers:
        if config.full_output is True:
            print(f"\n{'='*120}")
            print(f"Analiziram: {bookmaker.upper()}")
            print('='*120)
        
        stats = analyzer.analyze_bookmaker(bookmaker)
        summary = analyzer.print_bookmaker_summary(stats)
        summaries.append(summary)
    
    # Prikaži finalni summary
    analyzer.print_final_summary(summaries)


if __name__ == '__main__':
    """Glavna funkcija"""
    # Konfiguracija
    CASHOUT = 2.2
    MAX_LOSS = 1
    BETTING_ORDER = [10]
    
    config = BettingConfig(
        bet_order = BETTING_ORDER,
        auto_cashout = CASHOUT,
        max_loss_streak = MAX_LOSS if MAX_LOSS<=len(BETTING_ORDER) else len(BETTING_ORDER),
        full_output = True
    )
    
    main(config)