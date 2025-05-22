from abc import ABC, abstractmethod

class SwitchAdapter(ABC):
    @abstractmethod
    def switchPort(self, port_no: int):
        pass

    @abstractmethod
    def close(self):
        pass