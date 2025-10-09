# core/smart_validator.py
# VERSION: 1.2 - INTELLIGENT OCR ERROR CORRECTION
# Fixes common Tesseract mistakes specific to Aviator numbers

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation + correction"""
    is_valid: bool
    original_text: str
    corrected_text: str
    value: Optional[float]
    confidence: float
    corrections_applied: List[str]


class SmartOCRValidator:
    """
    Inteligentni validator koji:
    1. Detektuje common OCR greške
    2. Pokušava da ih automatski ispravi
    3. Validira range (1.00 - 10000.00)
    4. Vraća confidence score
    """
    
    # Common OCR character confusions
    CHAR_REPLACEMENTS = {
        'O': '0', 'o': '0',  # Letter O -> zero
        'I': '1', 'l': '1',  # Letter I/l -> one
        'S': '5', 's': '5',  # Letter S -> five (rijetko)
        'Z': '2',            # Letter Z -> two (rijetko)
        'B': '8',            # Letter B -> eight (rijetko)
        'g': '9',            # Letter g -> nine
        'G': '6',            # Letter G -> six
    }
    
    # Patterns that indicate OCR errors
    SUSPICIOUS_PATTERNS = [
        (r'(\d+)l(\d+)', r'\g<1>1\g<2>'),  # 1l3 -> 113
        (r'(\d+)O(\d+)', r'\g<1>0\g<2>'),  # 1O3 -> 103
        (r'x$', ''),                        # Remove trailing x
        (r'^x', ''),                        # Remove leading x
    ]
    
    def __init__(self, min_value: float = 1.0, max_value: float = 10000.0):
        self.min_value = min_value
        self.max_value = max_value
    
    def validate_score(self, text: str) -> ValidationResult:
        """
        Validate and correct Aviator SCORE reading.
        
        Args:
            text: Raw OCR output
            
        Returns:
            ValidationResult with corrections
        """
        original = text
        corrections = []
        
        # Step 1: Basic cleanup
        text = text.strip()
        
        # Remove common noise
        text = text.replace(' ', '')
        text = text.replace('\n', '')
        text = text.replace('\t', '')
        
        # Step 2: Apply character replacements
        for old_char, new_char in self.CHAR_REPLACEMENTS.items():
            if old_char in text:
                text = text.replace(old_char, new_char)
                corrections.append(f"'{old_char}' -> '{new_char}'")
        
        # Step 3: Apply pattern fixes
        for pattern, replacement in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text)
                corrections.append(f"Pattern fix: {pattern}")
        
        # Step 4: Fix decimal separators
        text, decimal_fix = self._fix_decimal_separator(text)
        if decimal_fix:
            corrections.append(decimal_fix)
        
        # Step 5: Try to parse
        value = self._try_parse_float(text)
        
        # Step 6: Advanced fixes if parse failed
        if value is None and len(text) > 0:
            text, advanced_fixes = self._apply_advanced_fixes(text)
            corrections.extend(advanced_fixes)
            value = self._try_parse_float(text)
        
        # Step 7: Range validation
        is_valid = False
        confidence = 0.0
        
        if value is not None:
            if self.min_value <= value <= self.max_value:
                is_valid = True
                
                # Calculate confidence based on corrections
                if len(corrections) == 0:
                    confidence = 0.95  # No corrections needed
                elif len(corrections) <= 2:
                    confidence = 0.85  # Minor corrections
                else:
                    confidence = 0.70  # Many corrections (suspicious)
            else:
                # Out of range
                confidence = 0.1
        
        return ValidationResult(
            is_valid=is_valid,
            original_text=original,
            corrected_text=text,
            value=value,
            confidence=confidence,
            corrections_applied=corrections
        )
    
    def _fix_decimal_separator(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Fix decimal separator issues.
        
        Aviator uses dot (.) but OCR might see comma (,)
        Multiple dots/commas indicate thousands separator confusion
        """
        dot_count = text.count('.')
        comma_count = text.count(',')
        
        correction = None
        
        # Case 1: Multiple dots (e.g., "1.234.56")
        if dot_count > 1:
            # Last dot is decimal, others are thousands
            parts = text.split('.')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
            correction = "Fixed multiple dots"
        
        # Case 2: Multiple commas (e.g., "1,234,56")
        elif comma_count > 1:
            # Last comma is decimal, others are thousands
            parts = text.split(',')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
            correction = "Fixed multiple commas"
        
        # Case 3: Mix of dots and commas (e.g., "1.234,56" or "1,234.56")
        elif dot_count >= 1 and comma_count >= 1:
            last_dot = text.rfind('.')
            last_comma = text.rfind(',')
            
            if last_dot > last_comma:
                # Dot is decimal, comma is thousands
                text = text.replace(',', '')
                correction = "Removed comma (thousands)"
            else:
                # Comma is decimal, dot is thousands
                text = text.replace('.', '').replace(',', '.')
                correction = "Comma -> dot (decimal)"
        
        # Case 4: Only comma (might be decimal)
        elif comma_count == 1 and dot_count == 0:
            # Check if it looks like decimal (2 digits after comma)
            parts = text.split(',')
            if len(parts) == 2 and len(parts[1]) == 2:
                text = text.replace(',', '.')
                correction = "Comma -> dot (decimal)"
            else:
                # Probably thousands separator
                text = text.replace(',', '')
                correction = "Removed comma (thousands)"
        
        return text, correction
    
    def _try_parse_float(self, text: str) -> Optional[float]:
        """Try to parse text as float"""
        try:
            return float(text)
        except (ValueError, TypeError):
            return None
    
    def _apply_advanced_fixes(self, text: str) -> Tuple[str, List[str]]:
        """
        Advanced fixes when basic parsing fails.
        These are more aggressive and might cause false positives.
        """
        fixes = []
        
        # Fix 1: Remove ALL non-numeric except dot
        clean = re.sub(r'[^\d.]', '', text)
        if clean != text:
            text = clean
            fixes.append("Removed all non-numeric")
        
        # Fix 2: If starts with dot, add leading zero
        if text.startswith('.'):
            text = '0' + text
            fixes.append("Added leading zero")
        
        # Fix 3: If ends with dot, remove it
        if text.endswith('.'):
            text = text[:-1]
            fixes.append("Removed trailing dot")
        
        # Fix 4: If multiple dots remain, keep only last
        if text.count('.') > 1:
            parts = text.split('.')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
            fixes.append("Kept only last dot")
        
        return text, fixes
    
    def validate_money(self, text: str) -> ValidationResult:
        """
        Validate money amount.
        Similar to score but different range (0 - 999999+)
        """
        original = text
        corrections = []
        
        # Basic cleanup
        text = text.strip()
        text = text.replace(' ', '')
        text = text.replace('$', '')
        text = text.replace('€', '')
        text = text.replace('£', '')
        
        # Character fixes
        for old_char, new_char in self.CHAR_REPLACEMENTS.items():
            if old_char in text:
                text = text.replace(old_char, new_char)
                corrections.append(f"'{old_char}' -> '{new_char}'")
        
        # Decimal fix
        text, decimal_fix = self._fix_decimal_separator(text)
        if decimal_fix:
            corrections.append(decimal_fix)
        
        # Try parse
        value = self._try_parse_float(text)
        
        # Advanced fixes if needed
        if value is None:
            text, advanced_fixes = self._apply_advanced_fixes(text)
            corrections.extend(advanced_fixes)
            value = self._try_parse_float(text)
        
        # Validation (money is non-negative)
        is_valid = value is not None and value >= 0
        
        confidence = 0.0
        if is_valid:
            if len(corrections) == 0:
                confidence = 0.95
            elif len(corrections) <= 2:
                confidence = 0.85
            else:
                confidence = 0.70
        
        return ValidationResult(
            is_valid=is_valid,
            original_text=original,
            corrected_text=text,
            value=value,
            confidence=confidence,
            corrections_applied=corrections
        )
    
    def validate_player_count(self, text: str) -> ValidationResult:
        """
        Validate player count (integer, 0-999999)
        """
        original = text
        corrections = []
        
        # Cleanup
        text = text.strip()
        text = re.sub(r'[^\d]', '', text)  # Only digits
        
        if text != original:
            corrections.append("Removed non-digits")
        
        # Character fixes
        for old_char, new_char in self.CHAR_REPLACEMENTS.items():
            if old_char in text:
                text = text.replace(old_char, new_char)
                corrections.append(f"'{old_char}' -> '{new_char}'")
        
        # Try parse
        try:
            value = int(text) if text else None
        except:
            value = None
        
        # Validate (player count: 0 - 999999)
        is_valid = value is not None and 0 <= value <= 999999
        
        confidence = 0.9 if is_valid and len(corrections) == 0 else 0.7
        
        return ValidationResult(
            is_valid=is_valid,
            original_text=original,
            corrected_text=text,
            value=float(value) if value is not None else None,
            confidence=confidence,
            corrections_applied=corrections
        )


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    validator = SmartOCRValidator()
    
    print("SMART OCR VALIDATOR TESTS")
    print("="*70)
    
    # Test cases with common OCR errors
    test_cases = [
        # (input, expected_value, description)
        ("2.47x", 2.47, "Normal with trailing x"),
        ("l.23", 1.23, "Letter l -> 1"),
        ("1O.45", 10.45, "Letter O -> 0"),
        ("5.Oo", 5.00, "Multiple O -> 0"),
        ("l23.45", 123.45, "Leading l -> 1"),
        ("1,234.56", 1234.56, "Thousands separator (dot decimal)"),
        ("1.234,56", 1234.56, "Thousands separator (comma decimal)"),
        ("2,45", 2.45, "Comma as decimal"),
        ("I5.67", 15.67, "Letter I -> 1"),
        ("8g9", 889, "Letter g -> 9"),  # Should fail (not in range)
        ("0.99", None, "Below minimum"),
        ("10001.0", None, "Above maximum"),
    ]
    
    for i, (input_text, expected, description) in enumerate(test_cases, 1):
        result = validator.validate_score(input_text)
        
        status = "✅" if result.value == expected else "❌"
        
        print(f"\n{i}. {description}")
        print(f"   Input:       '{input_text}'")
        print(f"   Corrected:   '{result.corrected_text}'")
        print(f"   Value:       {result.value}")
        print(f"   Valid:       {result.is_valid}")
        print(f"   Confidence:  {result.confidence:.2f}")
        if result.corrections_applied:
            print(f"   Corrections: {', '.join(result.corrections_applied)}")
        print(f"   {status} Expected: {expected}")
    
    print("\n" + "="*70)
    print("VALIDATOR TEST COMPLETE")
