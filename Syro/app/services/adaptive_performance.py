from __future__ import annotations

from collections import deque
from typing import Optional

from ..config import settings

class AdaptivePerformanceManager:
    def __init__(self):
        self._latency_history: deque[float] = deque(maxlen=settings.adaptive_window_size)
        self._current_mode: str = "quality"
        self._mode_lock = False
    
    def record_latency(self, latency_ms: float) -> None:
        if settings.performance_mode != "adaptive":
            return
        
        self._latency_history.append(latency_ms)
        
        if len(self._latency_history) < settings.adaptive_window_size:
            return
        
        if self._mode_lock:
            return
        
        avg_latency = sum(self._latency_history) / len(self._latency_history)
        
        if avg_latency > settings.adaptive_fast_threshold_ms and self._current_mode == "quality":
            self._current_mode = "fast"
            settings.performance_mode = "fast"
            settings.apply_performance_mode()
            print(f"Adaptive mode: Switched to FAST (avg latency: {avg_latency:.0f}ms)")
        
        elif avg_latency < settings.adaptive_quality_threshold_ms and self._current_mode == "fast":
            self._current_mode = "quality"
            settings.performance_mode = "quality"
            settings.apply_performance_mode()
            print(f"Adaptive mode: Switched to QUALITY (avg latency: {avg_latency:.0f}ms)")
    
    def get_current_mode(self) -> str:
        if settings.performance_mode != "adaptive":
            return settings.performance_mode
        return self._current_mode
    
    def lock_mode(self, mode: str) -> None:
        self._current_mode = mode
        self._mode_lock = True
    
    def unlock_mode(self) -> None:
        self._mode_lock = False
    
    def reset(self) -> None:
        self._latency_history.clear()
        self._current_mode = "quality"
        self._mode_lock = False

# Global instance
_adaptive_manager: Optional[AdaptivePerformanceManager] = None

def get_adaptive_manager() -> AdaptivePerformanceManager:
    global _adaptive_manager
    if _adaptive_manager is None:
        _adaptive_manager = AdaptivePerformanceManager()
    return _adaptive_manager

