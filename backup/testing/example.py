# Umesto 100 pojedinačnih INSERT-a
for data in data_list:
    db.insert_round(data)

# Sada: 1 batch od 100 INSERT-a u jednoj transakciji
db.insert_batch_rounds(data_list)

"""
DATABASE WORKER - Asynchronous batch database writer
- Groups inserts by bookmaker
"""


# Pokretanje sistema
worker = DatabaseWorker(batch_size=5, batch_timeout=1.0)
worker.start()

# Celina 1 dodaje podatke
db_queue.put(("bookmaker1", round_data))

# Celina 2 dodaje podatke
db_queue.put(("bookmaker2", round_data))

# Celina 3 dodaje podatke
db_queue.put(("bookmaker1", another_round_data))

# Worker automatski:
# 1. Grupiše po bookmaker-ima
# 2. Pravi batch insert-e
# 3. Oslobađa main thread

# Graceful shutdown
worker.stop()


"""
Example of use
"""

# Enhanced config.py additions
"""
Add these to your config.py for better queue management:
"""

# Queue configuration
DB_QUEUE_MAX_SIZE = 1000  # Prevent memory issues
DB_WORKER_BATCH_SIZE = 10  # Items per batch
DB_WORKER_BATCH_TIMEOUT = 2.0  # Seconds to wait before processing partial batch

# Create queue with size limit
import queue
import threading

gui_lock = threading.Lock()
db_queue = queue.Queue(maxsize=DB_QUEUE_MAX_SIZE)
shutdown_event = threading.Event()


# usage_example.py
"""
Example of how to use the improved DatabaseWorker
"""

def main():
    # Option 1: Manual management
    worker = DatabaseWorker(
        batch_size=10, 
        batch_timeout=2.0
    )
    
    try:
        worker.start()
        
        # Your main application logic here
        # The worker will process database operations in background
        
        # Check stats periodically
        stats = worker.get_stats()
        print(f"Database stats: {stats}")
        
    finally:
        worker.stop()
    
    # Option 2: Context manager (recommended)
    with DatabaseWorker().managed_worker() as worker:
        # Your application logic
        # Worker automatically starts and stops
        pass


def add_data_to_queue(bookmaker_name: str, data: dict):
    """Helper function to add data to queue safely."""
    try:
        db_queue.put((bookmaker_name, data), timeout=1.0)
        print(f"[Queue] Added data for {bookmaker_name}")
    except queue.Full:
        print(f"[Queue] Queue full! Dropping data for {bookmaker_name}")


if __name__ == "__main__":
    main()