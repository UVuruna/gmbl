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
    """Parser za score vrednosti - V3 FIXED FOR REAL"""
    
    @staticmethod
    def fix_missing_suffix(score_strings: List[str]) -> List[str]:
        """
        GLAVNA FUNKCIJA: Obrađuje listu score stringova
        
        PRAVILA:
        - Spajaj SAMO: prvi NEMA suffix AND drugi IMA suffix AND prvi NEMA decimal
        """
        fixed = []
        i = 0
        
        while i < len(score_strings):
            current = score_strings[i].strip()
            
            # Proveri da li current IMA suffix
            current_has_suffix = current.endswith(('x', 'X', 'k', 'K', '%'))
            
            # Ako NEMA suffix, proveri spajanje
            if not current_has_suffix and i + 1 < len(score_strings):
                next_item = score_strings[i + 1].strip()
                next_has_suffix = next_item.endswith(('x', 'X', 'k', 'K', '%'))
                
                # Proveri da li current ima decimalni separator
                current_has_decimal = any(sep in current for sep in '.,:-/')
                
                # SPOJI samo ako sledeći IMA suffix i trenutni NEMA decimal
                if next_has_suffix and not current_has_decimal:
                    merged = current + '.' + next_item
                    print(f"  → Spojeno: '{current}' + '{next_item}' = '{merged}'")
                    
                    processed = ScoreParser._process_single_score(merged)
                    if processed:
                        fixed.extend(processed)
                    
                    i += 2
                    continue
            
            # Obradi kao single score
            processed = ScoreParser._process_single_score(current)
            if processed:
                fixed.extend(processed)
            
            i += 1
        
        return fixed
    
    @staticmethod
    def _process_single_score(score_str: str) -> List[str]:
        """Obrađuje JEDAN score string"""
        # Normalizuj suffix (X/k/% → x)
        score_str = ScoreParser._normalize_suffix(score_str)
        
        # Split spojenih skorova
        score_parts = ScoreParser._split_joined_scores(score_str)
        
        results = []
        
        for part in score_parts:
            if not part.endswith('x'):
                if any(c.isdigit() for c in part):
                    part = ScoreParser._add_missing_x(part)
                    if not part:
                        continue
                else:
                    continue
            
            x_pos = len(part) - 1
            number_str = ScoreParser._extract_number_before_x(part, x_pos)
            
            if not number_str:
                continue
            
            # KRITIČNO: Ispravi format OVDE
            fixed_number = ScoreParser._fix_number_format(number_str)
            
            fixed_score = fixed_number + 'x'
            results.append(fixed_score)
            
            if fixed_score != part:
                print(f"  → Fixed: '{part}' → '{fixed_score}'")
        
        return results
    
    @staticmethod
    def _normalize_suffix(text: str) -> str:
        """Zameni sve varijante x sa 'x'"""
        text = text.strip()
        
        if text.endswith('X'):
            return text[:-1] + 'x'
        if text.endswith(('k', 'K')):
            return text[:-1] + 'x'
        if text.endswith('%'):
            return text[:-1] + 'x'
        
        return text
    
    @staticmethod
    def _add_missing_x(text: str) -> str:
        """Dodaje 'x' broju koji nema suffix"""
        if any(sep in text for sep in '.,:-/'):
            return text + 'x'
        
        digits_only = ''.join(c for c in text if c.isdigit())
        if len(digits_only) >= 3:
            return digits_only[:-2] + '.' + digits_only[-2:] + 'x'
        
        return ''
    
    @staticmethod
    def _extract_number_before_x(text: str, x_pos: int) -> str:
        """Izvlači broj PRE x pozicije"""
        number_chars = []
        
        i = x_pos - 1
        while i >= 0:
            char = text[i]
            
            # Dozvoli cifre, separatore, i OCR greške
            if char.isdigit() or char in '., :-/\' ' or char in 'BOIlSZboisz':
                number_chars.append(char)
                i -= 1
            else:
                break
        
        number_chars.reverse()
        return ''.join(number_chars).strip()
    
    @staticmethod
    def _fix_number_format(number_str: str) -> str:
        """
        Ispravlja format broja
        
        REDOSLED JE KLJUČAN!
        1. OCR greške (B→8, /→., itd)
        2. Cleanup
        3. Dodaj tačku
        4. Normalizuj
        """
        # ========================================
        # FAZA 1: OCR GREŠKE - PRVO!
        # ========================================
        
        # Cifre
        ocr_chars = {
            'B': '8', 'b': '8',
            'O': '0', 'o': '0',
            'I': '1', 'l': '1',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2'
        }
        
        for old, new in ocr_chars.items():
            number_str = number_str.replace(old, new)
        
        # Separatori - KRITIČNO!
        number_str = number_str.replace('/', '.')
        number_str = number_str.replace(':', '.')
        
        # Hyphen između cifara
        number_str = re.sub(r'(\d)-(\d)', r'\1.\2', number_str)
        
        # ========================================
        # FAZA 2: CLEANUP
        # ========================================
        
        number_str = number_str.replace(' ', '').replace('\'', '')
        
        # ========================================
        # FAZA 3: PROVERI SEPARATORE
        # ========================================
        
        has_dot = '.' in number_str
        has_comma = ',' in number_str
        
        # Nema separatora → dodaj tačku
        if not has_dot and not has_comma:
            if len(number_str) >= 3:
                number_str = number_str[:-2] + '.' + number_str[-2:]
            return number_str
        
        # ========================================
        # FAZA 4: NORMALIZUJ
        # ========================================
        
        dot_count = number_str.count('.')
        comma_count = number_str.count(',')
        
        if dot_count > 1:
            parts = number_str.rsplit('.', 1)
            number_str = parts[0].replace('.', ',') + '.' + parts[1]
        
        if comma_count > 1:
            parts = number_str.rsplit(',', 1)
            number_str = parts[0].replace(',', '') + '.' + parts[1]
        
        if has_dot and has_comma:
            last_dot = number_str.rfind('.')
            last_comma = number_str.rfind(',')
            
            if last_dot > last_comma:
                number_str = number_str.replace(',', '')
            else:
                number_str = number_str.replace('.', '').replace(',', '.')
        
        if has_comma and not has_dot:
            parts = number_str.split(',')
            if len(parts) == 2:
                if len(parts[1]) == 2:
                    number_str = number_str.replace(',', '.')
                elif len(parts[1]) == 3:
                    number_str = number_str.replace(',', '')
        
        return number_str
    
    @staticmethod
    def _split_joined_scores(text: str) -> List[str]:
        """Razdvaja spojene skorove"""
        pattern = r'(\d+[.,:\-/]?\d*x)(?=\d)'
        
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
        """Parsira score string u float"""
        if score is None:
            raise ValueError("score is None")
        
        s = str(score).strip()
        s = s.replace('x', '').replace('X', '').strip()
        s = s.rstrip('.')
        
        if ',' in s:
            if '.' not in s:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        
        try:
            return float(s)
        except ValueError:
            raise ValueError(f"Cannot parse score: '{score}'")


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
        """Pronalazi duzinu preklapanja"""
        max_overlap = min(len(upper_chunk), len(lower_chunk))
        
        for overlap_len in range(max_overlap, 0, -1):
            upper_suffix = upper_chunk[-overlap_len:]
            lower_prefix = lower_chunk[:overlap_len]
            
            if upper_suffix == lower_prefix:
                return overlap_len
        
        return 0
    
    @staticmethod
    def remove_overlaps(chunks: List[ChunkData]) -> List[ChunkData]:
        """Uklanja preklapajuce sufixe"""
        if len(chunks) <= 1:
            return chunks
        
        result = []
        
        for i in range(len(chunks) - 1):
            upper = chunks[i]
            lower = chunks[i + 1]
            
            overlap_len = OverlapDetector.find_overlap_length(upper.scores, lower.scores)
            
            chunk_time = upper.timestamp.strftime('%Y-%m-%d %H:%M:%S') if upper.timestamp else f"#{i}"
            
            if overlap_len > 0:
                trimmed_scores = upper.scores[:-overlap_len]
                result.append(ChunkData(upper.timestamp, trimmed_scores))
                print(f"  Chunk {chunk_time}: Uklonjeno {overlap_len} preklapajucih skorova")
            else:
                print(f"  ⚠ Chunk {chunk_time}: NEMA PREKLAPANJA")
                result.append(upper)
        
        result.append(chunks[-1])
        
        return result


class TimeInterpolator:
    """Interpolator za racunanje vremena"""
    
    @staticmethod
    def calculate_times(chunks: List[ChunkData]) -> List[Dict]:
        """Racuna TIME i SEC"""
        if not chunks:
            return []
        
        results = []
        
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
            
            chunk_time = current_chunk.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"  Chunk {chunk_time}: {num_scores} skorova, {time_diff:.0f}s razlika, avg={avg_sec:.2f}s")
            
            for j, score in enumerate(current_chunk.scores):
                current_time = current_chunk.timestamp - timedelta(seconds=j * avg_sec)
                
                results.append({
                    'score': score,
                    'time': current_time,
                    'sec': None
                })
        
        last_chunk = chunks[-1]
        
        if last_chunk.timestamp is None:
            raise ValueError("Poslednji chunk nema timestamp!")
        
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
        
        last_chunk_time = last_chunk.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"  Poslednji chunk {last_chunk_time}: {len(last_chunk.scores)} skorova, avg={global_avg_sec:.2f}s")
        
        for j, score in enumerate(last_chunk.scores):
            current_time = last_chunk.timestamp - timedelta(seconds=j * global_avg_sec)
            
            results.append({
                'score': score,
                'time': current_time,
                'sec': None
            })
        
        return results


class DataExtractorV2:
    """Ekstraktor podataka"""
    
    BREAK_PATTERN = r'Break - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(
        self,
        logs_dir: str = "analysis/txt",
        output_dir: str = "analysis/csv"
    ):
        self.logs_dir = Path(logs_dir)
        self.output_dir = Path(output_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_txt_file(self, filename: str) -> List[ChunkData]:
        """Parsira txt fajl"""
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
            
            match = re.match(self.BREAK_PATTERN, line)
            
            if match:
                if current_chunk is not None:
                    chunks.append(current_chunk)
                
                timestamp_str = match.group(1)
                timestamp = datetime.strptime(timestamp_str, self.TIMESTAMP_FORMAT)
                
                current_chunk = ChunkData(timestamp, [])
            else:
                if current_chunk is not None:
                    score_strings = line.split()
                    
                    score_strings = ScoreParser.fix_missing_suffix(score_strings)
                    
                    for score_str in score_strings:
                        try:
                            score = ScoreParser.parse(score_str)
                            current_chunk.scores.append(score)
                        except ValueError as e:
                            print(f"  ⚠ Ne mogu parsirati: '{score_str}'")
        
        if current_chunk is not None:
            chunks.append(current_chunk)
        
        return chunks
    
    def process_file(self, filename: str) -> pd.DataFrame:
        """Kompletna obrada"""
        print("=" * 84)
        print("DATA EXTRACTOR V2 - Chunk Overlap & Time Interpolation")
        print("=" * 84)
        
        print(f"\n1. Parsiram: {filename}.txt...")
        chunks = self.parse_txt_file(filename)
        print(f"  ✓ Učitano {len(chunks)} chunk-ova")
        
        for i, chunk in enumerate(chunks):
            print(f"    {chunk}")
        
        print(f"\n2. Uklanjam preklapanja...")
        chunks_trimmed = OverlapDetector.remove_overlaps(chunks)
        
        total_before = sum(len(c.scores) for c in chunks)
        total_after = sum(len(c.scores) for c in chunks_trimmed)
        print(f"  ✓ Uklonjeno {total_before - total_after} skorova")
        print(f"  ✓ Preostalo {total_after} skorova")
        
        print(f"\n3. Računam vremena...")
        data_with_times = TimeInterpolator.calculate_times(chunks_trimmed)
        
        print(f"\n4. Reverse-ujem listu...")
        data_with_times.reverse()
        
        print(f"\n5. Računam SEC...")
        if data_with_times:
            first_time = data_with_times[0]['time']
            
            for entry in data_with_times:
                entry['sec'] = int((entry['time'] - first_time).total_seconds())
        
        print(f"\n6. Kreiram DataFrame...")
        df = pd.DataFrame(data_with_times)
        
        df['time'] = df['time'].dt.strftime(self.TIMESTAMP_FORMAT)
        
        df.columns = ['SCORE', 'TIME', 'SEC']
        
        print(f"  ✓ DataFrame kreiran: {len(df)} redova")
        
        output_path = self.output_dir / f"{filename}.csv"
        df.to_csv(output_path, index=False)
        print(f"\n✓ Sačuvan CSV: {output_path.name}")
        
        print("\n" + "=" * 84)
        print("✓ Procesiranje završeno!")
        print("=" * 84)
        
        return df


def main(
    filename: str,
    output_dir: str
):
    """Glavna funkcija"""
    
    
    extractor = DataExtractorV2(output_dir=output_dir)
    df = extractor.process_file(filename)
    
    print(f"\nPregled prvih 10 redova (NAJSTARIJI):")
    print(df.head(10))
    print(f"\nPregled poslednjih 10 redova (NAJNOVIJI):")
    print(df.tail(10))
    input('\nPress ANY to continue')


if __name__ == '__main__':
    BOOKMAKERS = ['Admiral','BalkanBet','Merkur','Soccer']
    
    output_dir = input('Unesi lokaciju foldera (default: "analysis/csv"): ')
    output_dir = output_dir.strip() or "analysis/csv"
    
    for i,book in enumerate(BOOKMAKERS):
        main(filename=book, output_dir=output_dir)