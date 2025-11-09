"""
Mock simplificado de torch para tests sin dependencias pesadas
"""

class MockTensor:
    def __init__(self, *args, **kwargs):
        self.shape = args[0] if args else (1,)
    
    def cuda(self):
        return self
    
    def cpu(self):
        return self
    
    def to(self, device):
        return self
    
    def item(self):
        return 0.0

class MockCuda:
    @staticmethod
    def is_available():
        return False
    
    @staticmethod
    def device_count():
        return 0

class MockModule:
    def __init__(self):
        pass
    
    def eval(self):
        return self
    
    def train(self):
        return self
    
    def to(self, device):
        return self
    
    def parameters(self):
        return []

cuda = MockCuda()

def tensor(*args, **kwargs):
    return MockTensor(*args, **kwargs)

def no_grad():
    class NoGrad:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    return NoGrad()

# Simular atributos principales
device = lambda x: x
nn = type('nn', (), {
    'Module': MockModule,
    'Linear': MockModule,
    'Embedding': MockModule,
})()
