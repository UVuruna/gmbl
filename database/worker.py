# database/worker.py
"""
Database Worker - Asynchronous Batch Database Writer
Version: 3.0
Implements high-performance batch insert system with queue management
"""

import queue
import sqlite3
import threading
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

from config import app_config, performance_config
from logger import AviatorLogger, log_exception


@dataclass
class WorkerStats:
    """Statistics for database worker performance"""
    total_processed: int = 0
    total_batches: int = 0
    total_errors: int = 0
    queue_warnings: int = 0
    max_queue_size_seen: int = 0
    total_processing_time: float = 0.0
    last_batch_size: int = 0
    last_batch_time: float = 0.0
    
    @property
    def average_batch_size(self) -> float:
        """Calculate average items per batch"""
        if self.total_batches == 0:
            return 0.0
        return self.total_processed / self.total_batches
    
    @property
    def average_batch_time(self) -> float:
        """Calculate average processing time per batch"""
        if self.total_batches == 0:
            return 0.0
        return self.total_processing_time / self.total_batches
    
    @property
    def items_per_second(self) -> float:
        """Calculate throughput"""
        if self.total_processing_time == 0:
            return 0.0
        return self.total_processed / self.total_processing_time


class DatabaseWorker(threading.Thread):
    """
    High-performance database worker with batch processing
    
    Key features:
    - Batch inserts for 10-50x performance improvement
    - Automatic queue management with warnings
    - Graceful shutdown with data preservation
    - Performance statistics tracking
    """
    
    def __init__(
        self,
        db_path: Path = None,
        batch_size: int = None,
        batch_timeout: float = None,
        max_queue_size: int = None
    ):
        """
        Initialize database worker
        
        Args:
            db_path: Path to database file
            batch_size: Number of items to batch before insert
            batch_timeout: Maximum time to wait before forcing batch
            max_queue_size: Maximum queue size before warning
        """
        super().__init__(name="DatabaseWorker", daemon=False)
        
        # Configuration
        self.db_path = db_path or app_config.main_database
        self.batch_size = batch_size or app_config.batch_size
        self.batch_timeout = batch_timeout or app_config.batch_timeout
        self.max_queue_size = max_queue_size or app_config.max_queue_size
        
        # Queue and synchronization
        self.db_queue = queue.Queue(maxsize=self.max_queue_size * 2)
        self.shutdown_event = threading.Event()
        self.is_running = False
        
        # Batch management
        self._pending_batch = []
        self._batch_timer = None
        self._last_batch_time = time.time()
        
        # Statistics
        self._stats = WorkerStats()
        self._stats_lock = threading.Lock()
        
        # Database connection (created in thread)
        self._conn = None
        self._cursor = None
        
        # Logging
        self.logger = AviatorLogger.get_logger("DatabaseWorker")
    
    def run(self) -> None:
        """Main worker thread loop"""
        self.logger.info(f"Database worker started - Batch size: {self.batch_size}, "
                        f"Timeout: {self.batch_timeout}s")
        self.is_running = True
        
        try:
            # Initialize database connection in thread
            self._initialize_database()
            
            # Main processing loop
            self._process_loop()
            
        except Exception as e:
            log_exception(self.logger, e, "Worker thread")
        finally:
            self._cleanup()
    
    def _initialize_database(self) -> None:
        """Initialize database connection with optimal settings"""
        try:
            self._conn = sqlite3.connect(str(self.db_path))
            self._cursor = self._conn.cursor()
            
            # Optimize for batch inserts
            self._cursor.execute("PRAGMA journal_mode = WAL")
            self._cursor.execute("PRAGMA synchronous = OFF")
            self._cursor.execute("PRAGMA cache_size = -64000")
            self._cursor.execute("PRAGMA temp_store = MEMORY")
            self._cursor.execute("PRAGMA mmap_size = 268435456")
            self._conn.commit()
            
            self.logger.info("Database connection initialized with optimizations")
            
        except sqlite3.Error as e:
            self.logger.critical(f"Failed to initialize database: {e}")
            raise
    
    def _process_loop(self) -> None:
        """Main processing loop with batch collection"""
        last_stats_time = time.time()
        
        while self.is_running or not self.db_queue.empty():
            try:
                # Monitor queue size
                self._check_queue_health()
                
                # Try to get item with short timeout
                item = self._get_queue_item(timeout=0.01)
                
                if item:
                    self._add_to_batch(item)
                    
                    # Process batch if full
                    if len(self._pending_batch) >= self.batch_size:
                        self._process_batch()
                
                # Process partial batch if timeout exceeded
                elif self._should_process_batch():
                    self._process_batch()
                
                # Log statistics periodically
                if time.time() - last_stats_time >= performance_config.stats_report_interval:
                    self._log_periodic_stats()
                    last_stats_time = time.time()
                    
            except Exception as e:
                self._handle_worker_error(e)
        
        # Process any remaining items
        if self._pending_batch:
            self.logger.info("Processing final batch before shutdown...")
            self._process_batch()
    
    def _get_queue_item(self, timeout: float) -> Optional[Tuple[str, Dict]]:
        """Get item from queue with timeout"""
        try:
            return self.db_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _add_to_batch(self, item: Tuple[str, Dict]) -> None:
        """Add item to pending batch"""
        try:
            bookmaker_name, data = item
            
            # Validate data
            if not isinstance(data, dict):
                raise ValueError(f"Invalid data format: expected dict, got {type(data)}")
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = time.time()
            
            # Add to batch
            self._pending_batch.append({
                'bookmaker': bookmaker_name,
                'data': data
            })
            
            # Mark task done
            self.db_queue.task_done()
            
        except Exception as e:
            self.logger.error(f"Error adding item to batch: {e}")
            self.db_queue.task_done()
            with self._stats_lock:
                self._stats.total_errors += 1
    
    def _should_process_batch(self) -> bool:
        """Check if batch should be processed due to timeout"""
        if not self._pending_batch:
            return False
        
        time_since_last = time.time() - self._last_batch_time
        return time_since_last >= self.batch_timeout
    
    def _process_batch(self) -> None:
        """Process pending batch with transaction"""
        if not self._pending_batch:
            return
        
        batch_start = time.time()
        batch_size = len(self._pending_batch)
        
        try:
            # Begin transaction
            self._conn.execute("BEGIN TRANSACTION")
            
            # Group by table type for efficient batch insert
            rounds_batch = []
            snapshots_batch = []
            earnings_batch = []
            
            for item in self._pending_batch:
                bookmaker = item['bookmaker']
                data = item['data']
                
                # Prepare round data
                if 'main' in data:
                    main_data = data['main']
                    main_data['bookmaker'] = bookmaker
                    rounds_batch.append(main_data)
                
                # Prepare snapshot data
                if 'snapshots' in data:
                    for snapshot in data['snapshots']:
                        snapshot['bookmaker'] = bookmaker
                        snapshots_batch.append(snapshot)
                
                # Prepare earnings data
                if 'earnings' in data:
                    earnings = data['earnings']
                    earnings['bookmaker'] = bookmaker
                    earnings_batch.append(earnings)
            
            # Execute batch inserts
            if rounds_batch:
                self._batch_insert_rounds(rounds_batch)
            
            if snapshots_batch:
                self._batch_insert_snapshots(snapshots_batch)
            
            if earnings_batch:
                self._batch_insert_earnings(earnings_batch)
            
            # Commit transaction
            self._conn.commit()
            
            # Update statistics
            batch_time = time.time() - batch_start
            self._update_stats(batch_size, batch_time, success=True)
            
            # Log success
            self.logger.debug(f"✅ Batch processed: {batch_size}/{self.batch_size} items "
                            f"in {batch_time*1000:.1f}ms")
            
            # Clear batch and reset timer
            self._pending_batch.clear()
            self._last_batch_time = time.time()
            
        except sqlite3.Error as e:
            # Rollback on error
            self._conn.rollback()
            self.logger.error(f"Batch insert failed: {e}")
            
            # Update error statistics
            self._update_stats(batch_size, time.time() - batch_start, success=False)
            
            # Clear failed batch (data loss prevention could be added here)
            self._pending_batch.clear()
            self._last_batch_time = time.time()
    
    def _batch_insert_rounds(self, rounds: List[Dict]) -> None:
        """Batch insert round data"""
        if not rounds:
            return
        
        self._cursor.executemany("""
            INSERT INTO rounds (timestamp, bookmaker, score, total_win, total_players)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (r.get('timestamp'), r.get('bookmaker'), r.get('score'), 
             r.get('total_win'), r.get('total_players'))
            for r in rounds
        ])
    
    def _batch_insert_snapshots(self, snapshots: List[Dict]) -> None:
        """Batch insert snapshot data"""
        if not snapshots:
            return
        
        self._cursor.executemany("""
            INSERT INTO snapshots (round_ID, current_score, current_players, current_players_win)
            VALUES (?, ?, ?, ?)
        """, [
            (s.get('round_ID'), s.get('current_score'), 
             s.get('current_players'), s.get('current_players_win'))
            for s in snapshots
        ])
    
    def _batch_insert_earnings(self, earnings: List[Dict]) -> None:
        """Batch insert earnings data"""
        if not earnings:
            return
        
        self._cursor.executemany("""
            INSERT INTO earnings (round_ID, bet_amount, auto_stop, balance)
            VALUES (?, ?, ?, ?)
        """, [
            (e.get('round_ID'), e.get('bet_amount'), 
             e.get('auto_stop'), e.get('balance'))
            for e in earnings
        ])
    
    def _check_queue_health(self) -> None:
        """Monitor queue size and warn if needed"""
        current_size = self.db_queue.qsize()
        
        # Track maximum
        with self._stats_lock:
            self._stats.max_queue_size_seen = max(
                self._stats.max_queue_size_seen, 
                current_size
            )
        
        # Warn if queue is getting full
        if current_size > performance_config.queue_warning_size:
            if current_size > performance_config.queue_critical_size:
                self.logger.critical(f"⚠️ Queue size critical: {current_size} items")
            else:
                self.logger.warning(f"Queue size high: {current_size} items")
            
            with self._stats_lock:
                self._stats.queue_warnings += 1
    
    def _update_stats(self, batch_size: int, batch_time: float, success: bool) -> None:
        """Update performance statistics"""
        with self._stats_lock:
            if success:
                self._stats.total_processed += batch_size
                self._stats.total_batches += 1
                self._stats.total_processing_time += batch_time
                self._stats.last_batch_size = batch_size
                self._stats.last_batch_time = batch_time
            else:
                self._stats.total_errors += 1
    
    def _log_periodic_stats(self) -> None:
        """Log performance statistics periodically"""
        with self._stats_lock:
            stats = self._stats
        
        self.logger.info(
            f"📊 Stats: {stats.total_processed:,} processed, "
            f"{stats.items_per_second:.1f} items/sec, "
            f"avg batch: {stats.average_batch_size:.1f} items, "
            f"queue: {self.db_queue.qsize()}"
        )
    
    def _handle_worker_error(self, error: Exception) -> None:
        """Handle errors in worker thread"""
        log_exception(self.logger, error, "Worker loop")
        with self._stats_lock:
            self._stats.total_errors += 1
        
        # Sleep briefly to prevent rapid error loops
        time.sleep(0.1)
    
    def _cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up database worker...")
        
        # Close database connection
        if self._conn:
            try:
                # Final checkpoint
                self._cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._conn.close()
                self.logger.info("Database connection closed")
            except sqlite3.Error as e:
                self.logger.error(f"Error closing database: {e}")
        
        # Log final statistics
        self._log_final_stats()
    
    def _log_final_stats(self) -> None:
        """Log final statistics on shutdown"""
        with self._stats_lock:
            stats = self._stats
        
        self.logger.info("="*60)
        self.logger.info("DATABASE WORKER - FINAL STATISTICS")
        self.logger.info("="*60)
        self.logger.info(f"Total processed:     {stats.total_processed:,}")
        self.logger.info(f"Total batches:       {stats.total_batches:,}")
        self.logger.info(f"Total errors:        {stats.total_errors:,}")
        self.logger.info(f"Queue warnings:      {stats.queue_warnings:,}")
        self.logger.info(f"Max queue size:      {stats.max_queue_size_seen:,}")
        
        if stats.total_batches > 0:
            self.logger.info(f"Avg batch size:      {stats.average_batch_size:.1f} items")
            self.logger.info(f"Avg batch time:      {stats.average_batch_time*1000:.1f} ms")
            self.logger.info(f"Throughput:          {stats.items_per_second:.1f} items/sec")
            
            # Calculate efficiency
            theoretical_max = stats.total_processing_time * (self.batch_size / self.batch_timeout)
            efficiency = (stats.total_processed / theoretical_max * 100) if theoretical_max > 0 else 0
            self.logger.info(f"Efficiency:          {efficiency:.1f}%")
        
        self.logger.info("="*60)
    
    # Public interface methods
    
    def add_data(self, bookmaker: str, data: Dict) -> bool:
        """
        Add data to queue for processing
        
        Args:
            bookmaker: Bookmaker name
            data: Data dictionary
            
        Returns:
            True if added successfully, False if queue full
        """
        try:
            self.db_queue.put((bookmaker, data), timeout=1.0)
            return True
        except queue.Full:
            self.logger.warning(f"Queue full! Dropping data for {bookmaker}")
            return False
    
    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop worker gracefully
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        self.logger.info("Stopping database worker...")
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for thread to finish
        self.join(timeout=timeout)
        
        if self.is_alive():
            self.logger.warning("Worker did not stop gracefully, forcing termination")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        with self._stats_lock:
            return {
                'total_processed': self._stats.total_processed,
                'total_batches': self._stats.total_batches,
                'total_errors': self._stats.total_errors,
                'queue_size': self.db_queue.qsize(),
                'queue_warnings': self._stats.queue_warnings,
                'avg_batch_size': self._stats.average_batch_size,
                'items_per_second': self._stats.items_per_second
            }
    
    @contextmanager
    def managed_worker(self):
        """Context manager for automatic start/stop"""
        try:
            self.start()
            yield self
        finally:
            self.stop()


# Singleton instance management
_worker_instance = None
_worker_lock = threading.Lock()


def get_worker() -> DatabaseWorker:
    """Get or create singleton database worker"""
    global _worker_instance
    
    with _worker_lock:
        if _worker_instance is None or not _worker_instance.is_alive():
            _worker_instance = DatabaseWorker()
            _worker_instance.start()
    
    return _worker_instance


def stop_worker() -> None:
    """Stop the singleton database worker"""
    global _worker_instance
    
    with _worker_lock:
        if _worker_instance is not None:
            _worker_instance.stop()
            _worker_instance = None


# Export main components
__all__ = [
    'DatabaseWorker',
    'WorkerStats',
    'get_worker',
    'stop_worker'
]