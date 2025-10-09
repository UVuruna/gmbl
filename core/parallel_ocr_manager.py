# core/parallel_ocr_manager.py
# VERSION: 1.4 - OPTIMIZED PARALLEL OCR EXECUTION
# Manages multiple bookmakers with multiprocessing

import cv2
import numpy as np
import pytesseract
from multiprocessing import Process, Queue, Value, Lock
from threading import Thread
from queue import Queue as ThreadQueue, Empty
from typing import Dict, Optional, Callable, Tuple
from dataclasses import dataclass
import time
from pathlib import Path

from core.aviator_preprocessor import AviatorPreprocessor
from core.screen_reader import ScreenReader


@dataclass
class OCRResult:
    """Rezultat OCR čitanja"""
    bookmaker_id: str
    region_name: str
    value: Optional[float]
    raw_text: str
    confidence: float
    timestamp: float
    processing_time_ms: float


@dataclass
class BookmakerConfig:
    """Konfiguracija za jedan bookmaker"""
    bookmaker_id: str
    
    # Screen regions (x, y, width, height)
    score_region: Tuple[int, int, int, int]
    money_region: Optional[Tuple[int, int, int, int]] = None
    bet_button_region: Optional[Tuple[int, int, int, int]] = None
    
    # OCR frekvencija
    score_read_hz: float = 4.5  # Koliko puta/sec čitaš score
    money_read_hz: float = 0.5  # Koliko puta/sec čitaš money
    
    # Priority (viši = važniji)
    priority: int = 1


class BookmakerOCRProcess:
    """
    JEDAN proces za JEDAN bookmaker.
    Radi u beskonačnoj petlji i čita regione prema frekvencijama.
    """
    
    def __init__(
        self,
        config: BookmakerConfig,
        result_queue: Queue,
        stop_flag: Value,
    ):
        self.config = config
        self.result_queue = result_queue
        self.stop_flag = stop_flag
        
        # OCR komponente (inicijalizuj u procesu!)
        self.preprocessor = None
        self.screen_reader = None
        
        # Timing
        self.last_score_read = 0.0
        self.last_money_read = 0.0
    
    def init_ocr(self):
        """Initialize OCR components INSIDE the process"""
        self.preprocessor = AviatorPreprocessor()
        # Screen reader za ovaj bookmaker
        x, y, w, h = self.config.score_region
        self.screen_reader = ScreenReader(
            region=(x, y, w, h),
            ocr_type='score',
            logger_name=f"OCR_{self.config.bookmaker_id}"
        )
    
    def read_score(self) -> OCRResult:
        """Brzo čitanje SCORE regiona"""
        start = time.perf_counter()
        
        # Capture
        img = self.screen_reader.capture_image()
        
        # Preprocess
        processed = self.preprocessor.preprocess_score(img)
        
        # OCR - samo Tesseract (bez fallback za brzinu)
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,x'
        raw_text = pytesseract.image_to_string(processed, config=config).strip()
        
        # Parse
        value = self._parse_score(raw_text)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        return OCRResult(
            bookmaker_id=self.config.bookmaker_id,
            region_name='score',
            value=value,
            raw_text=raw_text,
            confidence=0.9 if value else 0.0,
            timestamp=time.time(),
            processing_time_ms=elapsed_ms
        )
    
    def read_money(self) -> Optional[OCRResult]:
        """Čitanje MONEY regiona (sporije, ređe)"""
        if not self.config.money_region:
            return None
        
        start = time.perf_counter()
        
        # Capture money region
        x, y, w, h = self.config.money_region
        import mss
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)[:, :, :3]  # Remove alpha
        
        # Preprocess
        processed = self.preprocessor.preprocess_money(img)
        
        # OCR
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,'
        raw_text = pytesseract.image_to_string(processed, config=config).strip()
        
        # Parse
        value = self._parse_money(raw_text)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        return OCRResult(
            bookmaker_id=self.config.bookmaker_id,
            region_name='money',
            value=value,
            raw_text=raw_text,
            confidence=0.8 if value else 0.0,
            timestamp=time.time(),
            processing_time_ms=elapsed_ms
        )
    
    def _parse_score(self, text: str) -> Optional[float]:
        """Parse score text to float"""
        try:
            # Remove 'x'
            text = text.lower().replace('x', '').replace('X', '').strip()
            
            # Handle common OCR errors
            text = text.replace('O', '0').replace('o', '0')
            text = text.replace('l', '1').replace('I', '1')
            
            # Fix decimal
            if ',' in text:
                text = text.replace(',', '.')
            
            num = float(text)
            
            # Validate range (Aviator score: 1.00 - 10000.00)
            if 1.0 <= num <= 10000.0:
                return num
        except:
            pass
        
        return None
    
    def _parse_money(self, text: str) -> Optional[float]:
        """Parse money text to float"""
        try:
            # Clean
            text = text.replace(',', '').replace('$', '').replace('€', '').strip()
            
            num = float(text)
            if num >= 0:
                return num
        except:
            pass
        
        return None
    
    def run(self):
        """Main loop - runs in separate process"""
        # Initialize OCR inside process
        self.init_ocr()
        
        print(f"[{self.config.bookmaker_id}] OCR Process started")
        
        # Izračunaj intervale
        score_interval = 1.0 / self.config.score_read_hz
        money_interval = 1.0 / self.config.money_read_hz if self.config.money_region else 999
        
        while not self.stop_flag.value:
            current_time = time.time()
            
            # Check if need to read SCORE
            if current_time - self.last_score_read >= score_interval:
                try:
                    result = self.read_score()
                    self.result_queue.put(result)
                    self.last_score_read = current_time
                except Exception as e:
                    print(f"[{self.config.bookmaker_id}] Score read error: {e}")
            
            # Check if need to read MONEY
            if current_time - self.last_money_read >= money_interval:
                try:
                    result = self.read_money()
                    if result:
                        self.result_queue.put(result)
                    self.last_money_read = current_time
                except Exception as e:
                    print(f"[{self.config.bookmaker_id}] Money read error: {e}")
            
            # Spavaj kratko da ne troši CPU (busy wait je loš!)
            time.sleep(0.01)  # 10ms sleep između checks
        
        print(f"[{self.config.bookmaker_id}] OCR Process stopped")


class ParallelOCRManager:
    """
    Manager za više bookmaker procesa.
    Jedan proces po bookmaker-u.
    """
    
    def __init__(self):
        self.bookmaker_configs: Dict[str, BookmakerConfig] = {}
        self.processes: Dict[str, Process] = {}
        self.result_queue = Queue(maxsize=1000)  # Shared queue
        self.stop_flag = Value('i', 0)  # Shared stop flag
        
        # Thread za procesiranje rezultata
        self.result_processor_thread: Optional[Thread] = None
        self.result_callback: Optional[Callable] = None
        
        self.running = False
    
    def add_bookmaker(self, config: BookmakerConfig):
        """Dodaj bookmaker za monitoring"""
        if self.running:
            raise RuntimeError("Cannot add bookmaker while running")
        
        self.bookmaker_configs[config.bookmaker_id] = config
        print(f"Added bookmaker: {config.bookmaker_id}")
    
    def set_result_callback(self, callback: Callable[[OCRResult], None]):
        """
        Postavi callback koji se poziva za svaki OCR rezultat.
        Ovo je mesto gde šalješ u database ili logiku.
        """
        self.result_callback = callback
    
    def _result_processor_loop(self):
        """Thread koji procesira rezultate iz queue-a"""
        print("Result processor started")
        
        while self.running:
            try:
                # Timeout da može da proveri running flag
                result = self.result_queue.get(timeout=0.5)
                
                # Call callback
                if self.result_callback:
                    try:
                        self.result_callback(result)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
            except Empty:
                continue
            except Exception as e:
                print(f"Result processor error: {e}")
        
        print("Result processor stopped")
    
    def start(self):
        """Start all bookmaker processes"""
        if self.running:
            print("Already running!")
            return
        
        if not self.bookmaker_configs:
            print("No bookmakers configured!")
            return
        
        self.running = True
        self.stop_flag.value = 0
        
        # Start result processor thread
        self.result_processor_thread = Thread(
            target=self._result_processor_loop,
            daemon=True
        )
        self.result_processor_thread.start()
        
        # Start process for each bookmaker
        for bookmaker_id, config in self.bookmaker_configs.items():
            worker = BookmakerOCRProcess(
                config=config,
                result_queue=self.result_queue,
                stop_flag=self.stop_flag
            )
            
            process = Process(target=worker.run, daemon=True)
            process.start()
            
            self.processes[bookmaker_id] = process
            print(f"Started process for: {bookmaker_id}")
        
        print(f"✅ Started {len(self.processes)} OCR processes")
    
    def stop(self):
        """Stop all processes"""
        if not self.running:
            return
        
        print("Stopping OCR Manager...")
        
        # Signal stop
        self.stop_flag.value = 1
        self.running = False
        
        # Wait for processes
        for bookmaker_id, process in self.processes.items():
            process.join(timeout=2.0)
            if process.is_alive():
                print(f"Force terminating: {bookmaker_id}")
                process.terminate()
        
        # Wait for result processor
        if self.result_processor_thread:
            self.result_processor_thread.join(timeout=2.0)
        
        self.processes.clear()
        print("✅ OCR Manager stopped")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Callback za rezultate
    def handle_result(result: OCRResult):
        print(f"[{result.bookmaker_id}] {result.region_name}: "
              f"{result.value} ({result.processing_time_ms:.1f}ms)")
    
    # Create manager
    manager = ParallelOCRManager()
    manager.set_result_callback(handle_result)
    
    # Add bookmakers
    manager.add_bookmaker(BookmakerConfig(
        bookmaker_id='bookmaker_1',
        score_region=(100, 100, 300, 80),
        money_region=(100, 200, 200, 50),
        score_read_hz=4.5,
        money_read_hz=0.5
    ))
    
    manager.add_bookmaker(BookmakerConfig(
        bookmaker_id='bookmaker_2',
        score_region=(500, 100, 300, 80),
        money_region=(500, 200, 200, 50),
        score_read_hz=4.5,
        money_read_hz=0.5
    ))
    
    # Start
    try:
        manager.start()
        
        # Run for 30 seconds
        print("\nRunning for 30 seconds...")
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\nInterrupted!")
    finally:
        manager.stop()
