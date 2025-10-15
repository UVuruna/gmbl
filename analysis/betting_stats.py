"""
Betting Statistics Analyzer v2.0
- Improved lossless_end logic
- Better handling of incomplete cycles
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
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
    trimmed_rounds: int  # Broj odsečenih rundi
    

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
        self.total_trimmed = 0
        
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
    
    def find_lossless_cutoff(self, bet_table: list) -> Tuple[Optional[int], int]:
        """
        Pronađi tačku gde treba seći tabelu da završi sa kompletnim loss cycle-om.
        
        Logika:
        - Ako kraj završava sa WIN-om → uzmi celu tabelu
        - Ako kraj završava sa LOSS-ovima → broji ih i seći nepotpune cycle-e
        
        Primer: max_loss_streak = 6
        - 15 loss-ova na kraju → 15 % 6 = 3 → seći 3, ostaviti 12 (2 kompletna cycle-a)
        - 10 loss-ova na kraju → 10 % 6 = 4 → seći 4, ostaviti 6 (1 kompletan cycle)
        - 12 loss-ova na kraju → 12 % 6 = 0 → uzmi sve (2 kompletna cycle-a)
        
        Returns:
            (cutoff_index, trimmed_count): 
                - cutoff_index: Indeks do kog da se koristi tabela (None = cela tabela)
                - trimmed_count: Broj odsečenih rundi
        """
        auto = self.config.auto_cashout
        max_loss = self.config.max_loss_streak
        
        # Broji uzastopne loss-ove od kraja
        consecutive_losses = 0
        
        for bet in reversed(bet_table):
            if bet['score'] is None:
                continue
            
            score = float(bet['score'])
            
            if score >= auto:
                # Našli smo WIN - kraj je čist
                break
            else:
                # LOSS
                consecutive_losses += 1
        
        # Ako nema loss-ova na kraju (završava sa WIN-om ili prazna tabela)
        if consecutive_losses == 0:
            return None, 0
        
        # Izračunaj koliko nepotpunih loss-ova treba odseći
        incomplete_losses = consecutive_losses % max_loss
        
        if incomplete_losses == 0:
            # Svi loss cycle-i su kompletni - uzmi celu tabelu
            return None, 0
        else:
            # Seći nepotpune loss-ove
            cutoff = len(bet_table) - incomplete_losses
            return cutoff, incomplete_losses
    
    def analyze_bookmaker(self, bookmaker_name: str) -> BookmakerStats:
        """Analiziraj podatke za jedan bookmaker"""
        bet_table = self.load_csv(bookmaker_name)
        
        # Odredi gde da sečemo tabelu
        cutoff, trimmed = self.find_lossless_cutoff(bet_table)
        working_table = bet_table[:cutoff] if cutoff is not None else bet_table
        
        if self.config.full_output and trimmed > 0:
            print(f"  ⚠️  Trimmed {trimmed} incomplete rounds at the end")
        
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
        
        for i, bet in enumerate(working_table):
            # Čitaj vreme i skor
            total_time = int(bet['sec']) if bet['sec'] is not None else 0
            
            if bet['score'] is None:
                continue
                
            score = float(bet['score'])
            bet_amount = self.config.bet_order[current_bet_index]
            
            # Uplati ulog
            total_balance -= bet_amount
            
            # Proveri da li je dobitak
            if score >= self.config.auto_cashout:
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
                if self.config.full_output:
                    self._print_progress(
                        bookmaker_name, total_balance, max_loss_amount, 
                        max_loss_count, big_losses, total_time
                    )
        
        # Ažuriraj globalne statistike
        rounds_played = len(working_table)
        self.total_rounds += rounds_played
        self.total_balance += total_balance
        self.total_big_losses += big_losses
        self.total_trimmed += trimmed
        hours = total_time / 3600
        self.total_hours = max(self.total_hours, hours)
        
        return BookmakerStats(
            name=bookmaker_name,
            total_rounds=rounds_played,
            total_balance=total_balance,
            max_loss_amount=max_loss_amount,
            max_loss_count=max_loss_count,
            big_losses=big_losses,
            hours_played=hours,
            money_needed=abs(self.money_needed_per_bookmaker[bookmaker_name]),
            trimmed_rounds=trimmed
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
        if self.config.full_output:
            print('_' * 120)
            print(
                f"{stats.total_rounds:<10,.0f}    |    "
                f"Total: {stats.total_balance:>10,.0f}    |    "
                f"Max gubitak: {stats.max_loss_amount:>6,.0f} ({stats.max_loss_count:>2,.0f})    |    "
                f"Veliki gubici: {stats.big_losses:>3,.0f}  | "
                f"Vreme: {stats.hours_played * 60:>7.2f} min"
            )
            print('_' * 120)
        
        trim_info = f" [trimmed: {stats.trimmed_rounds}]" if stats.trimmed_rounds > 0 else ""
        final = (
            f'\t*** STATS {stats.name.upper()}:'.ljust(28) +
            f'total = {stats.total_balance:,.0f} RSD'.ljust(24) +
            f'din/h: {stats.total_balance/stats.hours_played:,.0f} RSD'.ljust(24) +
            f'Money needed: {stats.money_needed:,.0f} RSD'.ljust(33) +
            f'({stats.big_losses:,.0f}) ***{trim_info}'.ljust(6)
        )
        
        if self.config.full_output:
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
        jump = percent_bar_length // 50  # 50% max
        for i in range(2, 51, 2):
            txt = f'{i}%|'
            br = int(jump - len(txt))
            title_axis += ' '*br+txt
            
        for k, v in filtered_wins.items():
            percentage = (v/self.total_wins)*100
            wins_percent_str += f"{k}. {percentage:,.1f}%".ljust(8) + " | "
            
            # Vizuelna reprezentacija sa █ karakterom
            bar_length = int(round(percentage*percent_bar_length/100))
            bar = '█' * bar_length
            wins_visual_str += f"{k}.".ljust(4) + f"= {bar}" + "\n"
        
        total_money_needed = abs(sum(self.money_needed_per_bookmaker.values()))
        trim_info = f" | Trimmed: {self.total_trimmed}" if self.total_trimmed > 0 else ""
        
        final = (
            f'\tROUNDS = {self.total_rounds:,.0f}{trim_info}  |  '
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
            f'\n{wins_visual_str[:-1]}'
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
        if config.full_output:
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
    CASHOUT = 2.0
    
    BETTING_ORDER = [25, 50, 100, 200, 400, 800, 1600]
    MAX_LOSS = len(BETTING_ORDER)
    
    config = BettingConfig(
        bet_order=BETTING_ORDER,
        auto_cashout=CASHOUT,
        max_loss_streak=MAX_LOSS if MAX_LOSS <= len(BETTING_ORDER) else len(BETTING_ORDER),
        full_output=True
    )
    
    main(config)