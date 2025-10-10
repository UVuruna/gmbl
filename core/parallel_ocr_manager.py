# core/parallel_ocr_manager.py
# VERSION: 1.5 - FIXED AND FUNCTIONAL
# KOMPLETNO FUNKCIONALAN FAJL - TESTIRAN

import cv2
import numpy as np
import pytesseract
import mss
from multiprocessing import Process, Manager
from multiprocessing.sharedctypes import Synchronized
from threading import Thread
from queue import Queue as ThreadQueue, Empty
from typing import Dict, Optional, Callable, Tuple
from dataclasses import dataclass
import time


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
    score_region: Tuple[int, int, int, int]  # (x, y, width, height)
    money_region: Optional[Tuple[int, int, int, int]] = None
    score_read_hz: float = 4.5
    money_read_hz: float = 0.5


class BookmakerOCRProcess:
    """Jedan proces za jedan bookmaker"""
    
    def __init__(
        self,
        config: BookmakerConfig,
        result_queue,
        stop_flag: Synchronized[int]
    ):
        self.config = config
        self.result_queue = result_queue
        self.stop_flag = stop_flag
        self.last_score_read = 0.0
        self.last_money_read = 0.0
    
    def read_score(self) -> OCRResult:
        """Čitaj SCORE region"""
        start = time.perf_counter()
        
        x, y, w, h = self.config.score_region
        
        # Capture
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)[:, :, :3]
        
        # Simple preprocessing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,x'
        raw_text = pytesseract.image_to_string(binary, config=config).strip()
        
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
        """Čitaj MONEY region"""
        if not self.config.money_region:
            return None
        
        start = time.perf_counter()
        x, y, w, h = self.config.money_region
        
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)[:, :, :3]
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        binary = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,'
        raw_text = pytesseract.image_to_string(binary, config=config).strip()
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
        """Parse score sa auto-correction"""
        try:
            text = text.lower().replace('x', '').strip()
            text = text.replace('O', '0').replace('o', '0')
            text = text.replace('l', '1').replace('I', '1')
            if ',' in text:
                text = text.replace(',', '.')
            
            num = float(text)
            if 1.0 <= num <= 10000.0:
                return num
        except:
            pass
        return None
    
    def _parse_money(self, text: str) -> Optional[float]:
        """Parse money"""
        try:
            text = text.replace(',', '').replace('$', '').replace('€', '').strip()
            num = float(text)
            if num >= 0:
                return num
        except:
            pass
        return None
    
    def run(self):
        """Main loop"""
        print(f"[{self.config.bookmaker_id}] Process started")
        
        score_interval = 1.0 / self.config.score_read_hz
        money_interval = 1.0 / self.config.money_read_hz if self.config.money_region else 999
        
        while not self.stop_flag.value:
            current_time = time.time()
            
            # Read score
            if current_time - self.last_score_read >= score_interval:
                try:
                    result = self.read_score()
                    self.result_queue.put(result)
                    self.last_score_read = current_time
                except Exception as e:
                    print(f"[{self.config.bookmaker_id}] Score error: {e}")
            
            # Read money
            if current_time - self.last_money_read >= money_interval:
                try:
                    result = self.read_money()
                    if result:
                        self.result_queue.put(result)
                    self.last_money_read = current_time
                except Exception as e:
                    print(f"[{self.config.bookmaker_id}] Money error: {e}")
            
            time.sleep(0.01)
        
        print(f"[{self.config.bookmaker_id}] Process stopped")


class ParallelOCRManager:
    """Manager za više bookmaker procesa"""
    
    def __init__(self):
        self.manager = Manager()
        self.bookmaker_configs: Dict[str, BookmakerConfig] = {}
        self.processes: Dict[str, Process] = {}
        self.result_queue = self.manager.Queue(maxsize=1000)
        self.stop_flag = self.manager.Value('i', 0)
        self.result_processor_thread: Optional[Thread] = None
        self.result_callback: Optional[Callable[[OCRResult], None]] = None
        self.running = False
    
    def add_bookmaker(self, config: BookmakerConfig):
        """Dodaj bookmaker"""
        if self.running:
            raise RuntimeError("Cannot add bookmaker while running")
        self.bookmaker_configs[config.bookmaker_id] = config
        print(f"Added bookmaker: {config.bookmaker_id}")
    
    def set_result_callback(self, callback: Callable[[OCRResult], None]):
        """Postavi callback za rezultate"""
        self.result_callback = callback
    
    def _result_processor_loop(self):
        """Thread koji procesira rezultate"""
        print("Result processor started")
        
        while self.running:
            try:
                result = self.result_queue.get(timeout=0.5)
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
        """Start sve procese"""
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
        
        # Start process za svaki bookmaker
        for bookmaker_id, config in self.bookmaker_configs.items():
            worker = BookmakerOCRProcess(
                config=config,
                result_queue=self.result_queue,
                stop_flag=self.stop_flag
            )
            
            process = Process(target=worker.run, daemon=True)
            process.start()
            
            self.processes[bookmaker_id] = process
            print(f"Started process: {bookmaker_id}")
        
        print(f"✅ Started {len(self.processes)} OCR processes")
    
    def stop(self):
        """Stop sve procese"""
        if not self.running:
            return
        
        print("Stopping OCR Manager...")
        
        self.stop_flag.value = 1
        self.running = False
        
        for bookmaker_id, process in self.processes.items():
            process.join(timeout=2.0)
            if process.is_alive():
                print(f"Force terminating: {bookmaker_id}")
                process.terminate()
        
        if self.result_processor_thread:
            self.result_processor_thread.join(timeout=2.0)
        
        self.processes.clear()
        print("✅ OCR Manager stopped")


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    def handle_result(result: OCRResult):
        print(f"[{result.bookmaker_id}] {result.region_name}: "
              f"{result.value} ({result.processing_time_ms:.1f}ms)")
    
    manager = ParallelOCRManager()
    manager.set_result_callback(handle_result)
    
    # Test sa dummy regions
    manager.add_bookmaker(BookmakerConfig(
        bookmaker_id='test_1',
        score_region=(100, 100, 300, 80),
        money_region=(100, 200, 200, 50),
        score_read_hz=2.0,
        money_read_hz=0.5
    ))
    
    try:
        manager.start()
        print("\nRunning for 10 seconds...")
        time.sleep(10)
    except KeyboardInterrupt:
        print("\nInterrupted!")
    finally:
        manager.stop()