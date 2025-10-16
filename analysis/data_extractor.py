"""
Data Extractor V2 - Chunk Parser with Overlap Detection & Time Interpolation
Parsira txt fajl sa Break timestamp-ima i score-ovima, uklanja preklapanja i interpolira vremena
"""

import re
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional


class ScoreParser:
    """Parser za score vrednosti"""
    
    @staticmethod
    def parse(score: Union[str, float, None]) -> float:
        """
        Parsira string sa score-om u razlicitim formatima i vraca float.
        """
        if score is None:
            raise ValueError("score is None")
        
        s = str(score).strip()
        
        # Ukloni poznate sufikse i whitespace
        s = s.replace('x', '').replace('X', '').replace('%', '').strip()
        
        # Ako sadrzi ':' i ne sadrzi druge decimalne sep, tretiraj ':' kao decimalnu tacku
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
            Duzina preklapanja (broj elemenata)
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
            chunks: Lista chunk-ova (od najnovijeg ka najstarijem)
            
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
            
            if overlap_len > 0:
                # Skrati gornji chunk
                trimmed_scores = upper.scores[:-overlap_len]
                result.append(ChunkData(upper.timestamp, trimmed_scores))
                print(f"  Chunk {i}: Uklonjeno {overlap_len} preklapajucih skorova")
            else:
                result.append(upper)
        
        # Poslednji chunk ostaje netaknut
        result.append(chunks[-1])
        
        return result


class TimeInterpolator:
    """Interpolator za racunanje vremena za sve skorove"""
    
    @staticmethod
    def interpolate_times(chunks: List[ChunkData]) -> List[Dict]:
        """
        Racuna TIME i SEC za sve skorove
        
        Args:
            chunks: Lista chunk-ova (od najstarijeg ka najnovijem nakon reverse)
            
        Returns:
            Lista {'score', 'time', 'sec'}
        """
        results = []
        
        # Izdvoj chunk-ove sa timestamp-om
        chunks_with_ts = [c for c in chunks if c.timestamp is not None]
        
        if not chunks_with_ts:
            raise ValueError("Nema chunk-ova sa timestamp-om!")
        
        # Izracunaj prosecno vreme po skoru
        first_ts = chunks_with_ts[0].timestamp
        last_ts = chunks_with_ts[-1].timestamp
        total_seconds = (last_ts - first_ts).total_seconds()
        
        total_scores = sum(len(c.scores) for c in chunks_with_ts)
        avg_seconds_per_score = total_seconds / total_scores if total_scores > 0 else 0
        
        print(f"\n  Prosečno vreme po skoru: {avg_seconds_per_score:.2f} sec")
        print(f"  Ukupno vreme: {total_seconds:.0f} sec")
        print(f"  Ukupno skorova sa timestamp-om: {total_scores}")
        
        current_time = first_ts
        current_sec = 0
        
        for chunk in chunks:
            if chunk.timestamp is None:
                # Ekstrapolacija unazad pre prvog timestamp-a
                for score in chunk.scores:
                    current_time -= timedelta(seconds=avg_seconds_per_score)
                    current_sec -= avg_seconds_per_score
                    
                    results.append({
                        'score': score,
                        'time': current_time,
                        'sec': int(round(current_sec))
                    })
                
                # Reset na prvi timestamp
                current_time = first_ts
                current_sec = 0
            else:
                # Chunk sa timestamp-om
                for i, score in enumerate(chunk.scores):
                    results.append({
                        'score': score,
                        'time': current_time,
                        'sec': int(round(current_sec))
                    })
                    
                    current_time += timedelta(seconds=avg_seconds_per_score)
                    current_sec += avg_seconds_per_score
        
        return results


class DataExtractorV2:
    """Ekstraktor podataka iz txt fajla sa Break timestamp-ima"""
    
    BREAK_PATTERN = r'Break - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(self, logs_dir: str = "documentation/logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_txt_file(self, filename: str) -> List[ChunkData]:
        """
        Parsira txt fajl i izvlaci chunk-ove
        
        Args:
            filename: Ime fajla (sa ili bez ekstenzije)
            
        Returns:
            Lista ChunkData objekata (od najnovijeg ka najstarijem)
        """
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        txt_path = self.logs_dir / filename
        
        if not txt_path.exists():
            raise FileNotFoundError(f"Text file not found: {txt_path}")
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        current_scores = []
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Proveri da li je Break linija
            match = re.match(self.BREAK_PATTERN, line)
            
            if match:
                # Sacuvaj prethodni chunk ako postoji
                if current_scores:
                    chunks.append(ChunkData(None, current_scores))
                    current_scores = []
                
                # Parsiraj timestamp
                timestamp_str = match.group(1)
                timestamp = datetime.strptime(timestamp_str, self.TIMESTAMP_FORMAT)
                
                # Kreiraj novi chunk sa timestamp-om
                chunks.append(ChunkData(timestamp, []))
            else:
                # Parsiraj score-ove iz linije
                score_strings = line.split()
                
                for score_str in score_strings:
                    try:
                        score = ScoreParser.parse(score_str)
                        
                        if chunks:
                            chunks[-1].scores.append(score)
                        else:
                            current_scores.append(score)
                    except ValueError:
                        print(f"  ⚠ Ne mogu parsirati: '{score_str}'")
        
        # Dodaj preostale skorove ako postoje
        if current_scores:
            chunks.append(ChunkData(None, current_scores))
        
        return chunks
    
    def process_file(self, filename: str) -> pd.DataFrame:
        """
        Kompletna obrada fajla
        
        Args:
            filename: Ime fajla bez ekstenzije
            
        Returns:
            DataFrame sa kolonama SCORE, TIME, SEC
        """
        print("=" * 84)
        print("DATA EXTRACTOR V2 - Chunk Overlap & Time Interpolation")
        print("=" * 84)
        
        # 1. Parse txt fajl
        print(f"\n1. Parsiram: {filename}.txt...")
        chunks = self.parse_txt_file(filename)
        print(f"  ✓ Učitano {len(chunks)} chunk-ova")
        
        for i, chunk in enumerate(chunks):
            print(f"    Chunk {i}: {chunk}")
        
        # 2. Ukloni preklapanja
        print(f"\n2. Uklanjam preklapanja...")
        chunks_trimmed = OverlapDetector.remove_overlaps(chunks)
        
        total_before = sum(len(c.scores) for c in chunks)
        total_after = sum(len(c.scores) for c in chunks_trimmed)
        print(f"  ✓ Uklonjeno {total_before - total_after} skorova")
        print(f"  ✓ Preostalo {total_after} skorova")
        
        # 3. Reverse chunk-ove (najstariji prvi)
        print(f"\n3. Reverse-ujem chunk-ove (najstariji → najnoviji)...")
        chunks_reversed = list(reversed(chunks_trimmed))
        
        for i, chunk in enumerate(chunks_reversed):
            print(f"    Chunk {i}: {chunk}")
        
        # 4. Interpoliraj vremena
        print(f"\n4. Računam vremena za sve skorove...")
        data_with_times = TimeInterpolator.interpolate_times(chunks_reversed)
        
        # 5. Kreiraj DataFrame
        print(f"\n5. Kreiram DataFrame...")
        df = pd.DataFrame(data_with_times)
        
        # Formatiraj TIME kolonu
        df['time'] = df['time'].dt.strftime(self.TIMESTAMP_FORMAT)
        
        # Preimenovanje kolona (uppercase)
        df.columns = ['SCORE', 'TIME', 'SEC']
        
        print(f"  ✓ DataFrame kreiran: {len(df)} redova")
        
        # 6. Sacuvaj CSV
        output_path = self.logs_dir / f"{filename}_processed.csv"
        df.to_csv(output_path, index=False)
        print(f"\n✓ Sačuvan CSV: {output_path.name}")
        
        print("\n" + "=" * 84)
        print("✓ Procesiranje završeno!")
        print("=" * 84)
        
        return df


def main():
    """Glavna funkcija"""
    filename = input('Unesi naziv txt fajla (bez ekstenzije, default: extracted_numbers): ')
    filename = filename.strip() or 'extracted_numbers'
    
    extractor = DataExtractorV2()
    df = extractor.process_file(filename)
    
    print(f"\nPregled prvih 10 redova:")
    print(df.head(10))
    print(f"\nPregled poslednjih 10 redova:")
    print(df.tail(10))


if __name__ == '__main__':
    main()