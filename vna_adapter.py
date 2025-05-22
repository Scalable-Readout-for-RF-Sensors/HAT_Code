from abc import ABC, abstractmethod
import numpy as np
import skrf as sk

class VNAAdapter(ABC):
    @abstractmethod
    def open(self): pass

    @abstractmethod
    def close(self): pass

    @abstractmethod
    def is_ready(self) -> bool: pass

    @abstractmethod
    def restart(self): pass

    @abstractmethod
    def pause(self): pass

    @abstractmethod
    def resume(self): pass

    @abstractmethod
    def set_frequencies(self, start: float, stop: float, points: int): pass

    @abstractmethod
    def fetch_frequencies(self): pass

    @abstractmethod
    def get_frequencies(self) -> np.typing.NDArray | None: pass

    @abstractmethod
    def data(self, array: int) -> np.typing.NDArray: pass

    @abstractmethod
    def scan(self) -> tuple[np.typing.NDArray, np.typing.NDArray]: pass

    @abstractmethod
    def logmag(self, x: np.typing.NDArray): pass

    @abstractmethod
    def skrf_network(self, x: np.typing.NDArray) -> sk.Network: pass