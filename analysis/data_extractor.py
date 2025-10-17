"""
Data Extractor V2 - Chunk Parser with Overlap Detection & Time Interpolation
Parsira txt fajl sa Break timestamp-ima, uklanja preklapanja i interpolira vremena
"""

import re
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional


class ScoreParser:
    """Parser za score vrednosti"""
    
    @staticmethod
    def has_decimal_part(number_str: str) -> bool:
        """
        Proveri da li broj ima DECIMALNI deo (ne thousands separator)
        
        Format:
        - 20.02 → ima decimalni deo (2 cifre posle .)
        - 1,194 → NEMA decimalni deo (3 cifre = thousands separator)
        - 10:46 → ima decimalni deo (: je uvek decimalni)
        """
        # : je uvek decimalni separator
        if ':' in number_str:
            return True
        
        # Proveri tačku
        if '.' in number_str:
            parts = number_str.rsplit('.', 1)
            if len(parts) == 2:
                decimal_part = parts[1]
                # 2 cifre = decimalni deo
                if len(decimal_part) == 2:
                    return True
                # 3 cifre = thousands separator
                if len(decimal_part) == 3:
                    return False
        
        # Proveri zarez
        if ',' in number_str:
            parts = number_str.rsplit(',', 1)
            if len(parts) == 2:
                decimal_part = parts[1]
                # 2 cifre = decimalni deo
                if len(decimal_part) == 2:
                    return True
                # 3 cifre = thousands separator
                if len(decimal_part) == 3:
                    return False
        
        return False
    
    @staticmethod
    def fix_missing_suffix(score_strings: List[str]) -> List[str]:
        """
        Popravlja brojeve sa nedostajućim ili pogrešnim sufixom
        
        Edge case-ovi:
        1. 20.02 (ima decimalni deo, fali x) → 20.02x
        2. 1,194 (thousands separator, fali decimalni deo) → spoji sa sledećim
        3. 91k (k umesto x) → 91x
        4. 114 + 56x → 114.56x (spoji jer 56x nema decimalni deo)
        5. 114 + 105.77x → skip 114 (ne spajaj jer 105.77x već ima decimalni deo)
        """
        fixed = []
        i = 0
        
        while i < len(score_strings):
            current = score_strings[i].strip()
            
            # Proveri da li ima validan suffix (x, X, %)
            has_valid_suffix = current.endswith('x') or current.endswith('X') or current.endswith('%')
            
            # Slučaj 1: Pogrešan suffix (k, K umesto x)
            if current.endswith('k') or current.endswith('K'):
                fixed_current = current[:-1] + 'x'
                fixed.append(fixed_current)
                print(f"  → Zamenjen suffix: '{current}' → '{fixed_current}'")
                i += 1
                continue
            
            # Slučaj 2: Ima validan suffix - dodaj ga
            if has_valid_suffix:
                fixed.append(current)
                i += 1
                continue
            
            # Slučaj 3: Nema suffix - proveri da li ima DECIMALNI deo
            has_decimal = ScoreParser.has_decimal_part(current)
            
            if has_decimal:
                # Format tipa 20.02, 38.11, 10:46 - dodaj x
                fixed_current = current + 'x'
                fixed.append(fixed_current)
                print(f"  → Dodat x: '{current}' → '{fixed_current}'")
                i += 1
                continue
            
            # Slučaj 4: Nema suffix i nema decimalni deo (ili ima thousands separator)
            # Proveri da li treba spojiti sa sledećim
            if i + 1 < len(score_strings):
                next_item = score_strings[i + 1].strip()
                next_has_suffix = next_item.endswith('x') or next_item.endswith('X') or next_item.endswith('%') or next_item.endswith('k') or next_item.endswith('K')
                
                # Ukloni suffix da proveriš strukturu
                next_without_suffix = next_item[:-1] if next_has_suffix else next_item
                next_has_decimal = ScoreParser.has_decimal_part(next_without_suffix)
                
                if next_has_suffix:
                    if not next_has_decimal:
                        # Sledeći nema decimalni deo - spoji (114 + 56x → 114.56x)
                        merged = current + '.' + next_item
                        fixed.append(merged)
                        print(f"  → Spojeno: '{current}' + '{next_item}' = '{merged}'")
                        i += 2
                        continue
                    else:
                        # Sledeći već ima decimalni deo - ne spajaj (114 + 105.77x → skip 114)
                        print(f"  ⚠ '{current}' nema suffix, '{next_item}' već kompletan - preskačem '{current}'")
                        i += 1
                        continue
                else:
                    # Sledeći takođe nema suffix - skip trenutni
                    print(f"  ⚠ '{current}' i '{next_item}' oba bez suffixa - preskačem '{current}'")
                    i += 1
                    continue
            else:
                # Poslednji broj bez suffixa
                print(f"  ⚠ Broj bez x/%: '{current}' - preskačem!")
                i += 1
                continue
        
        return fixed
    
    @staticmethod
    def split_joined_scores(text: str) -> List[str]:
        """
        Razdvaja spojene skorove tipa '1.24x1.00x' u ['1.24x', '1.00x']
        """
        pattern = r'(\d+(?:[.,:]\d+)?[xX%])(?=\d)'
        
        parts = []
        last_end = 0
        
        for match in re.finditer(pattern, text):
            parts.append(text[last_end:match.end()])
            last_end = match.end()
        
        if last_end < len(text):
            parts.append(text[last_end:])
        
        return parts if parts else [text]
    
    @staticmethod
    def parse(score: Union[str, float, None]) -> float:
        """Parsira string sa score-om"""
        if score is None:
            raise ValueError("score is None")
        
        s = str(score).strip()
        
        # c) i d) Ukloni trailing tacku posle x ili %
        s = re.sub(r'([xX%])\.+$', r'\1', s)
        
        # Ukloni sufikse x, X, %
        s = s.replace('x', '').replace('X', '').replace('%', '').strip()
        
        # Ukloni trailing tacke koje su ostale
        s = s.rstrip('.')
        
        # b) i e) Proveri format tipa 1.248.57 ili 8.615.90
        dot_count = s.count('.')
        comma_count = s.count(',')
        
        if dot_count >= 2 and comma_count == 0:
            # Format: 1.248.57 → 1248.57
            parts = s.split('.')
            if len(parts) >= 2:
                s = ''.join(parts[:-1]) + '.' + parts[-1]
        
        # Ako sadrzi ':' i ne sadrzi druge decimalne sep
        if ':' in s and '.' not in s and ',' not in s:
            s = s.replace(':', '.')
        
        # Odredi decimalni separator kada postoje i ',' i '.'
        if ',' in s and '.' in s:
            last_comma = s.rfind(',')
            last_dot = s.rfind('.')
            
            if last_comma > last_dot:
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        else:
            if ',' in s:
                s = s.replace(',', '.')
        
        # Ukloni sve sto nije broj, tacka, znak ili exponent
        s = re.sub(r'[^0-9\.\+\-eE]', '', s)
        
        # Validacija
        if s in ('', '.', '+', '-', '+.', '-.'):
            raise ValueError(f"Cannot parse score from '{score}'")
        
        return float(s)


class ChunkData:
    """Predstavlja jedan chunk sa timestamp-om i score-ovima"""
    
    def __init__(self, timestamp: Optional[datetime], scores: List[float]):
        self.timestamp = timestamp
        self.scores = scores
    
    def __repr__(self):
        ts_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "None"
        return f"Chunk(ts={ts_str}, scores={len(self.scores)})"


class OverlapDetector:
    """Detektuje preklapanja između chunk-ova"""
    
    @staticmethod
    def find_overlap_length(upper_chunk: List[float], lower_chunk: List[float]) -> int:
        """
        Pronalazi duzinu preklapanja: sufix gornjeg = prefix donjeg
        
        Args:
            upper_chunk: Gornji chunk (noviji u txt fajlu)
            lower_chunk: Donji chunk (stariji u txt fajlu)
            
        Returns:
            Duzina preklapanja
        """
        max_overlap = min(len(upper_chunk), len(lower_chunk))
        
        for overlap_len in range(max_overlap, 0, -1):
            upper_suffix = upper_chunk[-overlap_len:]
            lower_prefix = lower_chunk[:overlap_len]
            
            if upper_suffix == lower_prefix:
                return overlap_len
        
        return 0
    
    @staticmethod
    def remove_overlaps(chunks: List[ChunkData]) -> List[ChunkData]:
        """
        Uklanja preklapajuce sufixe iz gornjih chunk-ova
        
        Args:
            chunks: Lista chunk-ova (kako su u txt fajlu - od najnovijeg)
            
        Returns:
            Lista chunk-ova sa uklonjenim preklapanjima
        """
        if len(chunks) <= 1:
            return chunks
        
        result = []
        
        for i in range(len(chunks) - 1):
            upper = chunks[i]
            lower = chunks[i + 1]
            
            overlap_len = OverlapDetector.find_overlap_length(upper.scores, lower.scores)
            
            # Formatiraj timestamp za debug
            chunk_time = upper.timestamp.strftime('%Y-%m-%d %H:%M:%S') if upper.timestamp else f"#{i}"
            
            if overlap_len > 0:
                trimmed_scores = upper.scores[:-overlap_len]
                result.append(ChunkData(upper.timestamp, trimmed_scores))
                print(f"  Chunk {chunk_time}: Uklonjeno {overlap_len} preklapajucih skorova")
            else:
                result.append(upper)
        
        # Poslednji chunk ostaje netaknut
        result.append(chunks[-1])
        
        return result


class TimeInterpolator:
    """Interpolator za racunanje vremena za sve skorove"""
    
    @staticmethod
    def calculate_times(chunks: List[ChunkData]) -> List[Dict]:
        """
        Racuna TIME i SEC za sve skorove
        
        LOGIKA:
        - Svaki chunk ima timestamp za PRVI skor
        - Ostali skorovi u chunku idu UNAZAD u prošlost (- avg_sec)
        - avg_sec za chunk = (timestamp_i - timestamp_{i+1}) / broj_skorova_u_chunku_i
        - Za poslednji chunk: avg_sec = ukupno_vreme / ukupno_skorova_sa_timestamp
        
        Args:
            chunks: Lista chunk-ova (od najnovijeg ka najstarijem)
            
        Returns:
            Lista {'score', 'time', 'sec'} (u redosledu kao što su chunk-ovi)
        """
        if not chunks:
            return []
        
        results = []
        
        # Izracunaj avg_sec za svaki chunk (osim poslednjeg)
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            if current_chunk.timestamp is None or next_chunk.timestamp is None:
                raise ValueError(f"Chunk {i} ili {i+1} nema timestamp!")
            
            time_diff = (current_chunk.timestamp - next_chunk.timestamp).total_seconds()
            num_scores = len(current_chunk.scores)
            
            if num_scores == 0:
                continue
            
            avg_sec = time_diff / num_scores
            
            # Formatiraj timestamp za debug
            chunk_time = current_chunk.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"  Chunk {chunk_time}: {num_scores} skorova, {time_diff:.0f}s razlika, avg={avg_sec:.2f}s")
            
            # Dodaj skorove za ovaj chunk
            for j, score in enumerate(current_chunk.scores):
                current_time = current_chunk.timestamp - timedelta(seconds=j * avg_sec)
                
                results.append({
                    'score': score,
                    'time': current_time,
                    'sec': None
                })
        
        # Poslednji chunk (najstariji)
        last_chunk = chunks[-1]
        
        if last_chunk.timestamp is None:
            raise ValueError("Poslednji chunk nema timestamp!")
        
        # Izracunaj prosečan avg_sec iz svih prethodnih chunk-ova
        total_time = 0
        total_scores = 0
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            time_diff = (current_chunk.timestamp - next_chunk.timestamp).total_seconds()
            total_time += time_diff
            total_scores += len(current_chunk.scores)
        
        if total_scores > 0:
            global_avg_sec = total_time / total_scores
        else:
            global_avg_sec = 20.0
        
        # Formatiraj timestamp za debug
        last_chunk_time = last_chunk.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"  Poslednji chunk {last_chunk_time}: {len(last_chunk.scores)} skorova, avg={global_avg_sec:.2f}s")
        
        # Dodaj skorove za poslednji chunk
        for j, score in enumerate(last_chunk.scores):
            current_time = last_chunk.timestamp - timedelta(seconds=j * global_avg_sec)
            
            results.append({
                'score': score,
                'time': current_time,
                'sec': None
            })
        
        return results


class DataExtractorV2:
    """Ekstraktor podataka iz txt fajla sa Break timestamp-ima"""
    
    BREAK_PATTERN = r'Break - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(self, logs_dir: str = "analysis/txt"):
        self.logs_dir = Path(logs_dir)
        self.output_dir = Path(logs_dir.replace('txt','csv'))
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_txt_file(self, filename: str) -> List[ChunkData]:
        """
        Parsira txt fajl i izvlaci chunk-ove
        
        Returns:
            Lista ChunkData objekata (od najnovijeg ka najstarijem kako su u fajlu)
        """
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        txt_path = self.logs_dir / filename
        
        if not txt_path.exists():
            raise FileNotFoundError(f"Text file not found: {txt_path}")
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        current_chunk = None
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Proveri da li je Break linija
            match = re.match(self.BREAK_PATTERN, line)
            
            if match:
                # Sacuvaj prethodni chunk ako postoji
                if current_chunk is not None:
                    chunks.append(current_chunk)
                
                # Parsiraj timestamp
                timestamp_str = match.group(1)
                timestamp = datetime.strptime(timestamp_str, self.TIMESTAMP_FORMAT)
                
                # Kreiraj novi chunk
                current_chunk = ChunkData(timestamp, [])
            else:
                # Parsiraj score-ove iz linije
                if current_chunk is not None:
                    score_strings = line.split()
                    
                    # KRITIČNO: Fix brojeva bez x/% (19 74x → 19.74x)
                    score_strings = ScoreParser.fix_missing_suffix(score_strings)
                    
                    for score_str in score_strings:
                        # Razdvoj spojene skorove (1.24x1.00x → 1.24x, 1.00x)
                        split_scores = ScoreParser.split_joined_scores(score_str)
                        
                        for individual_score in split_scores:
                            try:
                                score = ScoreParser.parse(individual_score)
                                current_chunk.scores.append(score)
                            except ValueError as e:
                                print(f"  ⚠ Ne mogu parsirati: '{individual_score}' (original: '{score_str}')")
        
        # Dodaj poslednji chunk
        if current_chunk is not None:
            chunks.append(current_chunk)
        
        return chunks
    
    def process_file(self, filename: str) -> pd.DataFrame:
        """
        Kompletna obrada fajla
        
        Args:
            filename: Ime fajla bez ekstenzije
            
        Returns:
            DataFrame sa kolonama SCORE, TIME, SEC (najstariji gore, najnoviji dole)
        """
        print("=" * 84)
        print("DATA EXTRACTOR V2 - Chunk Overlap & Time Interpolation")
        print("=" * 84)
        
        # 1. Parse txt fajl
        print(f"\n1. Parsiram: {filename}.txt...")
        chunks = self.parse_txt_file(filename)
        print(f"  ✓ Učitano {len(chunks)} chunk-ova")
        
        for i, chunk in enumerate(chunks):
            print(f"    {chunk}")
        
        # 2. Ukloni preklapanja
        print(f"\n2. Uklanjam preklapanja...")
        chunks_trimmed = OverlapDetector.remove_overlaps(chunks)
        
        total_before = sum(len(c.scores) for c in chunks)
        total_after = sum(len(c.scores) for c in chunks_trimmed)
        print(f"  ✓ Uklonjeno {total_before - total_after} skorova")
        print(f"  ✓ Preostalo {total_after} skorova")
        
        # 3. Interpoliraj vremena
        print(f"\n3. Računam vremena za sve skorove...")
        data_with_times = TimeInterpolator.calculate_times(chunks_trimmed)
        
        # 4. Reverse celu listu (najstariji gore, najnoviji dole)
        print(f"\n4. Reverse-ujem listu (najstariji → najnoviji)...")
        data_with_times.reverse()
        
        # 5. Izracunaj SEC (od 0 za najstariji do max za najnoviji)
        print(f"\n5. Računam SEC vrednosti...")
        if data_with_times:
            first_time = data_with_times[0]['time']
            
            for entry in data_with_times:
                entry['sec'] = int((entry['time'] - first_time).total_seconds())
        
        # 6. Kreiraj DataFrame
        print(f"\n6. Kreiram DataFrame...")
        df = pd.DataFrame(data_with_times)
        
        # Formatiraj TIME kolonu
        df['time'] = df['time'].dt.strftime(self.TIMESTAMP_FORMAT)
        
        # Preimenovanje kolona (uppercase)
        df.columns = ['SCORE', 'TIME', 'SEC']
        
        print(f"  ✓ DataFrame kreiran: {len(df)} redova")
        
        # 7. Sacuvaj CSV
        output_path = self.output_dir / f"{filename}.csv"
        df.to_csv(output_path, index=False)
        print(f"\n✓ Sačuvan CSV: {output_path.name}")
        
        print("\n" + "=" * 84)
        print("✓ Procesiranje završeno!")
        print("=" * 84)
        
        return df


def main(filename):
    """Glavna funkcija"""
    #filename = input('Unesi naziv txt fajla (bez ekstenzije, default: extracted_numbers): ')
    #filename = filename.strip() or 'extracted_numbers'
    
    extractor = DataExtractorV2()
    df = extractor.process_file(filename)
    
    print(f"\nPregled prvih 10 redova (NAJSTARIJI):")
    print(df.head(10))
    print(f"\nPregled poslednjih 10 redova (NAJNOVIJI):")
    print(df.tail(10))
    input('\nPress ANY to continiue')


if __name__ == '__main__':
    BOOKMAKERS = ['Admiral','BalkanBet','Merkur','Soccer']
    for book in BOOKMAKERS:
        main(filename=book)