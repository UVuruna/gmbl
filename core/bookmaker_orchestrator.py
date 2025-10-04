# bookmaker_orchestrator.py
# VERSION: 3.0 - OPTIMIZED BATCH PROCESSING
# CHANGES: Batch queue system, better shutdown, performance monitoring

from main.gui_controller import GUIController
from main.bookmaker_process import BookmakerProcess
from database.worker import DatabaseWorker
from root.logger import AviatorLogger

from multiprocessing import Manager
from typing import List, Tuple, Optional, Dict
import time


class BookmakerOrchestrator:
    """
    Main orchestrator managing all processes with optimized batch processing.
    
    OPTIMIZATIONS:
    - Batch database inserts (50-100 items)
    - Larger queue sizes to prevent data loss
    - Performance monitoring
    
    Responsibilities:
    1. Coordinate parallel bookmaker processes
    2. Manage centralized GUI controller (single mouse/keyboard access)
    3. Handle database worker with batch processing
    4. Ensure graceful shutdown with proper resource cleanup
    """
    
    def __init__(self, num_bookmakers: int = 4):
        self.manager = Manager()
        
        # Queues with appropriate sizes
        # For 4 bookmakers @ 0.2s: ~20 items/sec = need buffer for ~500 items
        self.betting_queue = self.manager.Queue(maxsize=100)
        self.db_queue = self.manager.Queue(maxsize=10000)  # Large buffer
        self.shutdown_event = self.manager.Event()
        
        self.num_bookmakers = num_bookmakers
        self.gui_controller: Optional[GUIController] = None
        self.db_worker: Optional[DatabaseWorker] = None
        self.bookmaker_processes: List[BookmakerProcess] = []
        self.logger = AviatorLogger.get_logger("Orchestrator")
        
        # Performance tracking
        self._start_time = None
        self._stats_interval = 60.0  # Log stats every 60s
        self._last_stats_time = 0
    
    def add_bookmaker(
        self,
        name: str,
        auto_stop: float,
        target_money: float,
        play_amount_coords: Tuple[int, int],
        play_button_coords: Tuple[int, int],
        bet_sequence: List[int],
        score_region: Dict[str, int],
        my_money_region: Dict[str, int],
        other_count_region: Dict[str, int],
        other_money_region: Dict[str, int],
        phase_region: Dict[str, int]
    ) -> None:
        """Add bookmaker process."""
        process = BookmakerProcess(
            bookmaker_name=name,
            target_money=target_money,
            bet_sequence=bet_sequence,
            auto_stop=auto_stop,
            
            betting_queue=self.betting_queue,
            db_queue=self.db_queue,
            shutdown_event=self.shutdown_event,
            
            play_amount_coords=play_amount_coords,
            play_button_coords=play_button_coords,
            
            score_region=score_region,
            my_money_region=my_money_region,
            other_count_region=other_count_region,
            other_money_region=other_money_region,
            phase_region=phase_region
        )
        
        self.bookmaker_processes.append(process)
        self.logger.info(f"Added bookmaker: {name}")
    
    def start(self) -> None:
        """Start all components in proper order."""
        self.logger.info("=" * 60)
        self.logger.info("STARTING ORCHESTRATOR")
        self.logger.info("=" * 60)
        
        self._start_time = time.time()
        
        # 1. Start GUI controller (handles betting)
        self.gui_controller = GUIController(self.betting_queue)
        self.gui_controller.start()
        self.logger.info("✅ GUI Controller started")
        
        # 2. Start database worker with BATCH processing
        batch_size = min(50, max(10, self.num_bookmakers * 10))
        batch_timeout = 1.0  # 1 second max wait
        
        self.db_worker = DatabaseWorker(
            db_queue=self.db_queue,
            batch_size=batch_size,
            batch_timeout=batch_timeout,
            max_queue_size=5000
        )
        self.db_worker.start()
        self.logger.info(
            f"✅ Database Worker started "
            f"(batch_size={batch_size}, timeout={batch_timeout}s)"
        )
        
        # 3. Start all bookmaker processes
        for process in self.bookmaker_processes:
            process.start()
            self.logger.info(f"✅ Started: {process.name}")
        
        self.logger.info("=" * 60)
        self.logger.info(
            f"🚀 ORCHESTRATOR RUNNING - {len(self.bookmaker_processes)} bookmakers"
        )
        self.logger.info(f"Expected throughput: ~{len(self.bookmaker_processes) * 5} items/sec")
        self.logger.info("=" * 60)
    
    def stop(self) -> None:
        """
        Graceful shutdown with proper sequencing.
        
        SHUTDOWN ORDER (CRITICAL):
        1. Signal all processes to stop
        2. Stop GUI controller FIRST (release mouse/keyboard)
        3. Wait for bookmaker processes to finish
        4. Stop database worker LAST (process remaining data)
        5. Clean up manager resources
        """
        self.logger.info("=" * 60)
        self.logger.info("INITIATING GRACEFUL SHUTDOWN")
        self.logger.info("=" * 60)
        
        # 1. Signal shutdown to all processes
        self.logger.info("1/5 Signaling shutdown to all processes...")
        self.shutdown_event.set()
        time.sleep(0.5)  # Give processes time to see the signal
        
        # 2. Stop GUI controller first (release input devices)
        if self.gui_controller:
            self.logger.info("2/5 Stopping GUI controller...")
            self.gui_controller.stop()
            self.logger.info("✅ GUI controller stopped")
        
        # 3. Wait for bookmaker processes to finish
        self.logger.info("3/5 Waiting for bookmaker processes...")
        for process in self.bookmaker_processes:
            if process.is_alive():
                self.logger.info(f"Waiting for {process.name}...")
                process.join(timeout=5.0)
                
                if process.is_alive():
                    self.logger.warning(f"⚠️  {process.name} didn't stop, terminating...")
                    process.terminate()
                    process.join(timeout=2.0)
                
                if not process.is_alive():
                    self.logger.info(f"✅ {process.name} stopped")
        
        # 4. Stop database worker (processes remaining queue)
        if self.db_worker:
            self.logger.info("4/5 Stopping database worker...")
            queue_size = self.db_queue.qsize()
            if queue_size > 0:
                self.logger.info(f"Processing {queue_size} remaining items...")
            self.db_worker.stop()
            self.logger.info("✅ Database worker stopped")
        
        # 5. Clean up manager
        self.logger.info("5/5 Cleaning up resources...")
        self.manager.shutdown()
        self.logger.info("✅ Manager cleaned up")
        
        # Final statistics
        self._log_final_stats()
        
        self.logger.info("=" * 60)
        self.logger.info("🛑 ORCHESTRATOR STOPPED SUCCESSFULLY")
        self.logger.info("=" * 60)
    
    def _log_final_stats(self) -> None:
        """Log final orchestrator statistics."""
        runtime = time.time() - self._start_time if self._start_time else 0
        
        self.logger.info("=" * 60)
        self.logger.info("ORCHESTRATOR - FINAL STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Runtime:           {runtime/3600:.2f} hours")
        self.logger.info(f"Bookmakers:        {len(self.bookmaker_processes)}")
        
        # Get database worker stats
        if self.db_worker:
            db_stats = self.db_worker.get_stats()
            self.logger.info(f"Items processed:   {db_stats['total_processed']:,}")
            self.logger.info(f"Avg throughput:    {db_stats['items_per_second']:.1f} items/sec")
            self.logger.info(f"DB batches:        {db_stats['total_batches']:,}")
            self.logger.info(f"DB errors:         {db_stats['total_errors']:,}")
        
        self.logger.info("=" * 60)
    
    def monitor_performance(self) -> Dict[str, any]:
        """
        Get current performance metrics.
        
        Returns:
            Dict with current performance data
        """
        if not self.db_worker:
            return {}
        
        db_stats = self.db_worker.get_stats()
        
        return {
            'runtime_hours': db_stats['runtime_hours'],
            'total_processed': db_stats['total_processed'],
            'items_per_second': db_stats['items_per_second'],
            'queue_size': db_stats['queue_size'],
            'avg_batch_size': db_stats['avg_batch_size'],
            'total_errors': db_stats['total_errors']
        }