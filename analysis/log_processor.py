"""
Log Processor - CSV Time & Score Parser
Parsira log.csv i interpolira vremena između checkpoint-ova
"""

import pandas as pd
import math
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class TimeParser:
    """Parser za datetime vrednosti"""
    
    FORMAT = "%d.%m.%Y %H:%M:%S"
    
    @staticmethod
    def parse(time_str: Optional[str]) -> Optional[datetime]:
        """
        Parsira string u datetime objekat
        
        Args:
            time_str: String sa vremenom ili None
            
        Returns:
            datetime objekat ili None ako parsiranje ne uspe
        """
        if time_str is None:
            return None
        
        s = str(time_str).strip()
        if not s:
            return None
        
        try:
            return datetime.strptime(s, TimeParser.FORMAT)
        except Exception:
            return None
    
    @staticmethod
    def format(dt: Optional[datetime]) -> str:
        """Formatira datetime u string"""
        if dt is None:
            return ""
        return dt.strftime(TimeParser.FORMAT)


class ScoreParser:
    """Parser za score vrednosti"""
    
    @staticmethod
    def parse(value: Optional[str]) -> Optional[float]:
        """
        Parsira score vrednost
        
        Args:
            value: String ili broj
            
        Returns:
            float ili None ako parsiranje ne uspe
        """
        if value is None:
            return None
        
        s = str(value).strip()
        if not s:
            return None
        
        # Obradi decimalne separatore
        if ',' in s and '.' in s:
            s = s.replace(',', '')
        elif ',' in s:
            s = s.replace(',', '.')
        
        s = s.replace(' ', '')
        
        try:
            return float(s)
        except Exception:
            return None


class TimeInterpolator:
    """Interpolator za računanje vremena između checkpoint-ova"""
    
    @staticmethod
    def compute_seconds(rows: List[Dict]) -> List[Optional[int]]:
        """
        Računa sekunde za svaki red sa interpolacijom između checkpoint-ova
        
        Pravila:
          - Prvi checkpoint → sec = 0
          - Svaki sledeći checkpoint dobija prethodni_kumulativ + (time_j - time_i)
          - Redovi između checkpoint-ova dobijaju linearnu interpolaciju
          - Tail (posle poslednjeg checkpointa) se ekstrapolira koristeći
            poslednji segmentni rate (ako postoji ≥2 checkpointa)
        
        Args:
            rows: Lista dictionary-ja sa poljem 'time' (datetime ili None)
            
        Returns:
            Lista sec vrednosti (int ili None) iste dužine kao rows
        """
        n = len(rows)
        times = [r['time'] for r in rows]
        checkpoints = [i for i, t in enumerate(times) if t is not None]
        secs = [None] * n
        
        if not checkpoints:
            return secs
        
        cumulative = 0.0
        first_cp = checkpoints[0]
        
        # Sve pre prvog checkpoint-a ostaje None
        for idx in range(0, first_cp):
            secs[idx] = None
        
        # Prolaz kroz segmente između checkpoint-ova
        if len(checkpoints) >= 2:
            for k in range(len(checkpoints) - 1):
                i = checkpoints[k]
                j = checkpoints[k + 1]
                t_i = times[i]
                t_j = times[j]
                
                delta = (t_j - t_i).total_seconds()
                steps = j - i
                
                if steps == 0:
                    secs[i] = int(round(cumulative))
                    continue
                
                # Linearna interpolacija
                for p in range(0, steps + 1):
                    sec_val = cumulative + (p * delta) / steps
                    secs[i + p] = int(round(sec_val))
                
                cumulative += delta
        else:
            # Samo jedan checkpoint
            i = checkpoints[0]
            secs[i] = 0
            cumulative = 0.0
        
        # Ekstrapolacija tail-a
        last_cp = checkpoints[-1]
        tail_len = n - 1 - last_cp
        
        if tail_len > 0 and len(checkpoints) >= 2:
            # Koristi poslednji segmentni rate
            i = checkpoints[-2]
            j = checkpoints[-1]
            last_segment_delta = (times[j] - times[i]).total_seconds()
            last_segment_steps = j - i if (j - i) != 0 else 1
            per_step = last_segment_delta / last_segment_steps
            
            base = secs[last_cp] if secs[last_cp] is not None else int(round(cumulative))
            
            for p in range(1, tail_len + 1):
                val = base + per_step * p
                secs[last_cp + p] = int(round(val))
        
        return secs


class LogProcessor:
    """Glavni processor za log fajlove"""
    
    MARKETS = ['Merkur', 'BalkanBet', 'Admiral', 'Soccer']
    
    def __init__(self, logs_dir: str = "documentation/logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def is_present(value) -> bool:
        """Proveri da li vrednost postoji i nije prazna"""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, float) and math.isnan(value):
            return False
        return True
    
    def load_log(self, filename: str = "log.csv") -> List[Dict]:
        """Učitaj log fajl (CSV ili Excel)"""
        # Proveri da li je Excel ili CSV
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            log_path = self.logs_dir / filename
            if not log_path.exists():
                raise FileNotFoundError(f"Log file not found: {log_path}")
            
            try:
                import openpyxl
                df = pd.read_excel(log_path, engine='openpyxl')
            except ImportError:
                print("⚠ openpyxl nije instaliran. Instaliraj sa: pip install openpyxl")
                print("Konvertujem Excel → CSV...")
                df = pd.read_excel(log_path)
                csv_path = log_path.with_suffix('.csv')
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"✓ Kreiran CSV: {csv_path.name}")
                # Ponovo učitaj iz CSV
                df = pd.read_csv(csv_path, keep_default_na=True, encoding='utf-8-sig')
        else:
            log_path = self.logs_dir / filename
            if not log_path.exists():
                raise FileNotFoundError(f"Log file not found: {log_path}")
            df = pd.read_csv(log_path, keep_default_na=True, encoding='utf-8-sig')
        
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    
    def parse_market_data(self, raw_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Parsira podatke za sve market-e iz glavnog log-a
        
        Args:
            raw_data: Sirovi podaci iz CSV-a
            
        Returns:
            Dictionary sa podacima po market-ima
        """
        market_data = {market.lower(): [] for market in self.MARKETS}
        
        for row in raw_data:
            for market in self.MARKETS:
                key = market.lower()
                time_raw = row.get(f"Time {market}")
                score_raw = row.get(market)
                
                time_dt = TimeParser.parse(time_raw)
                score_val = ScoreParser.parse(score_raw)
                
                market_data[key].append({
                    'time': time_dt,
                    'score': score_val,
                    'sec': None
                })
        
        return market_data
    
    def compute_seconds_for_markets(self, market_data: Dict[str, List[Dict]]):
        """Izračunaj sekunde za sve market-e"""
        for market_key, rows in market_data.items():
            # Indeksi redova koje čuvamo
            keep_idxs = [
                i for i, r in enumerate(rows)
                if self.is_present(r['time']) or self.is_present(r['score'])
            ]
            
            if not keep_idxs:
                continue
            
            # Podlista sa samo vrednim redovima
            subrows = [rows[i] for i in keep_idxs]
            
            # Izračunaj sekunde
            secs_sub = TimeInterpolator.compute_seconds(subrows)
            
            # Vrati izračunate sekunde na odgovarajuće pozicije
            for idx, sec_val in zip(keep_idxs, secs_sub):
                rows[idx]['sec'] = sec_val
    
    def save_market_csvs(self, market_data: Dict[str, List[Dict]]):
        """Sačuvaj podatke za svaki market u poseban CSV"""
        for market_key, rows in market_data.items():
            output_rows = []
            
            for r in rows:
                # Preskači potpuno prazne redove
                if not (self.is_present(r['time']) or self.is_present(r['score'])):
                    continue
                
                output_rows.append({
                    'time': TimeParser.format(r['time']),
                    'score': r['score'],
                    'sec': r['sec']
                })
            
            # Kreiraj DataFrame i sačuvaj
            df = pd.DataFrame(output_rows)
            output_path = self.logs_dir / f"{market_key}.csv"
            df.to_csv(output_path, index=False)
            
            print(f"✓ Saved: {output_path.name} ({len(output_rows)} rows)")
    
    def process(self, input_filename: str = "log.csv"):
        """
        Glavna funkcija za procesiranje log-a
        
        Args:
            input_filename: Ime input log fajla
        """
        print("=" * 84)
        print("LOG PROCESSOR - Time Interpolation & CSV Export")
        print("=" * 84)
        
        # Učitaj log
        print(f"\nUčitavam: {input_filename}...")
        raw_data = self.load_log(input_filename)
        print(f"✓ Učitano {len(raw_data)} redova")
        
        # Parsiraj podatke za sve market-e
        print("\nParsiram podatke za sve market-e...")
        market_data = self.parse_market_data(raw_data)
        
        # Izračunaj sekunde
        print("Računam vremena (interpolacija)...")
        self.compute_seconds_for_markets(market_data)
        
        # Sačuvaj CSV-ove
        print("\nČuvam CSV fajlove:")
        self.save_market_csvs(market_data)
        
        print("\n" + "=" * 84)
        print("✓ Procesiranje završeno!")
        print("=" * 84)


def main(filepath: str):
    """Glavna funkcija"""
    processor = LogProcessor()
    
    # Podržava i .csv i .xlsx
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = filepath  # default
    
    processor.process(filename)


if __name__ == '__main__':
    filepath = input('Unesi naziv excel fajla (default: log.csv): ') or 'log.csv'
    main(filepath)