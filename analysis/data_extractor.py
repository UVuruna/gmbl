"""
Data Extractor - Excel/CSV Parser
Konvertuje Excel (.xlsx) u CSV i parsira podatke iz raznih formata
"""

import re
import pandas as pd
from pathlib import Path
from typing import List, Union


class ScoreParser:
    """Parser za rezultate u različitim formatima"""
    
    @staticmethod
    def parse(score: Union[str, float, None]) -> float:
        """
        Parsira string sa rezultatom u razlicitim formatima i vraca float.
        Podrzava formate:
          - '1.28', '1,28', '1:28'
          - sufiks 'x' ili '%' (bice uklonjen)
          - thousands separators: '1,000.23' i '1.000,23'
        
        Args:
            score: String ili broj za parsiranje
            
        Returns:
            float: Parsiran rezultat
            
        Raises:
            ValueError: Ako se rezultat ne može parsirati
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
                # Zarez je decimalni separator
                s = s.replace('.', '').replace(',', '.')
            else:
                # Tacka je decimalni separator
                s = s.replace(',', '')
        else:
            # Samo zarez - tretiraj kao decimalnu tacku
            if ',' in s:
                s = s.replace(',', '.')
        
        # Ukloni sve sto nije broj, tacka, znak ili exponent
        s = re.sub(r'[^0-9\.\+\-eE]', '', s)
        
        # Validacija
        if s in ('', '.', '+', '-', '+.', '-.'):
            raise ValueError(f"Cannot parse score from '{score}'")
        
        return float(s)


class DataExtractor:
    """Ekstraktor podataka iz fajlova"""
    
    def __init__(self, logs_dir: str = "documentation/logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def convert_excel_to_csv(self, filename: str) -> str:
        """
        Konvertuje Excel (.xlsx) fajl u CSV
        
        Args:
            filename: Ime fajla bez ekstenzije
            
        Returns:
            str: Putanja do kreiranog CSV fajla
        """
        excel_path = self.logs_dir / f"{filename}.xlsx"
        csv_path = self.logs_dir / f"{filename}.csv"
        
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        # Učitaj Excel i sačuvaj kao CSV
        df = pd.read_excel(excel_path)
        df.to_csv(csv_path, index=False)
        
        print(f"✓ Converted: {excel_path.name} → {csv_path.name}")
        return str(csv_path)
    
    def extract_from_text(self, filename: str) -> List[float]:
        """
        Ekstraktuje brojeve iz text fajla
        
        Args:
            filename: Ime fajla bez ekstenzije
            
        Returns:
            List[float]: Lista parsiranih brojeva
        """
        txt_path = self.logs_dir / f"{filename}.txt"
        
        if not txt_path.exists():
            raise FileNotFoundError(f"Text file not found: {txt_path}")
        
        data_list = []
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            raw_data = f.readlines()
        
        for raw_row in raw_data:
            row = raw_row.split()
            parsed_row = [ScoreParser.parse(item) for item in row]
            data_list.extend(parsed_row)
        
        return data_list
    
    @staticmethod
    def split_into_chunks(data: List) -> List[List]:
        """Podeli listu na delove određene dužine"""
        return [data[i:i + 60] for i in range(0, len(data), 60)]
    
    @staticmethod
    def fix_collection_order(
        data: List[float],
        first_to_last: bool
    ) -> List[float]:
        """
        Prilagođava redosled podataka na osnovu načina prikupljanja
        
        Args:
            data: Lista svih podataka
            first_to_last: Da li su screenshot-ovi od prvog ka poslednjem
            
        Returns:
            List[float]: Podaci u ispravnom redosledu
        """

        chunks = DataExtractor.split_into_chunks(data)
        print(chunks)
        
        if first_to_last:
            # Obrni svaki chunk pojedinačno
            result = []
            for chunk in chunks:
                chunk.reverse()
                result.extend(chunk)
            return result
        else:
            # Obrni redosled chunk-ova
            chunks.reverse()
            return [item for chunk in chunks for item in chunk]
    
    def process_file(
        self,
        filename: str,
        first_to_last: bool
    ) -> List[float]:
        """
        Kompletna obrada fajla
        
        Args:
            filename: Ime fajla bez ekstenzije
            first_to_last: Redosled screenshot-ova
            
        Returns:
            List[float]: Obrađeni podaci
        """
        data = self.extract_from_text(filename)
        return self.fix_collection_order(data, first_to_last)


def interactive_mode():
    """Interaktivni mod za ekstrakciju podataka"""
    print("=" * 84)
    print("DATA EXTRACTOR - Excel/CSV/Text Parser")
    print("=" * 84)
    
    # Pitaj korisnika za parametre
    first_to_last_input = input('Da li je od prvog screenshota (enter ako nije): ')
    first_to_last = True if first_to_last_input.strip() != '' else False
    
    # Kreiraj ekstraktor
    extractor = DataExtractor()
    
    # Pokušaj konverziju Excel → CSV ako postoji
    try:
        extractor.convert_excel_to_csv('extracted_numbers')
    except FileNotFoundError:
        print("Excel file not found, using existing text file...")
    
    # Ekstraktuj podatke
    data = extractor.process_file('extracted_numbers', first_to_last)
    
    # Prikaži rezultate
    print()
    print(f"BROJ PODATAKA: {len(data)}")
    print('*' * 84)
    for value in data:
        print(value)
    print('*' * 84)


def main():
    """Glavna funkcija"""
    interactive_mode()


if __name__ == '__main__':
    main()
