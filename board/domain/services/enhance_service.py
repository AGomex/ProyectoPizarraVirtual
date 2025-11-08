from abc import ABC, abstractmethod

class EnhanceServicePort(ABC):
    @abstractmethod
    def enhance_stroke(self, points):
        pass
