import time
import threading

class RateLimiter:
    """
    The Gatekeeper (Phase 8).
    Prevents API Bans by enforcing a strict Request Per Second (RPS) limit.
    Singleton pattern to be shared across modules.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(RateLimiter, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
        
    def __init__(self, max_calls=2, period=1.0):
        if self._initialized: return
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self._lock = threading.Lock()
        self._initialized = True
        print(f"  🛑 [RateLimiter] Initialized (Limit: {max_calls} reqs/{period}s)")

    def wait_for_token(self):
        """
        Blocks until a token is available.
        """
        with self._lock:
            while True:
                now = time.time()
                # Remove old calls
                self.calls = [t for t in self.calls if t > now - self.period]
                
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return # Go ahead
                
                # Wait needed
                sleep_time = self.calls[0] + self.period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)

# Usage Global Instance
limiter = RateLimiter()

def protected_download(func, *args, **kwargs):
    """Wrapper for API calls"""
    limiter.wait_for_token()
    return func(*args, **kwargs)
