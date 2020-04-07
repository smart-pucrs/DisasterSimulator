class Flood:
    """Class that represents a flood inside the simulation."""

    def __init__(self, identifier: int, period: int, keeped: bool, dimensions: dict, list_of_nodes: list,
                 max_propagation: float, propagation_per_step: float, nodes_per_propagation: list):
        self.identifier: int = identifier
        self.active: bool = False
        self.type: str = 'flood'
        self.dimensions: dict = dimensions
        self.list_of_nodes: list = list_of_nodes
        self.period: int = period
        self.keeped: bool = keeped
        self.max_propagation = max_propagation
        self.propagation_per_step = propagation_per_step
        self.nodes_per_propagation = nodes_per_propagation
      
    # def __init__(self, flood):
    #     self.identifier: int = flood['identifier']
    #     self.active: bool = False
    #     self.type: str = 'flood'
    #     self.initial_position = initial_position
    #     self.dimensions: dict = dimensions
    #     self.list_of_nodes: list = list_of_nodes
    #     self.period: int = flood['period']
    #     self.keeped: bool = flood['keeped']
    #     self.max_propagation = flood['dimensions']
    #     self.propagation_per_step = flood['list_of_nodes']
    #     self.nodes_per_propagation = nodes_per_propagation
    
    # def __init__(self, *flood, **kwargs):
    #     for attr in flood:
    #         for key in attr:
    #             setattr(self, key, attr[key])
    #     for key in kwargs:
    #         setattr(self, key, kwargs[key])

    def update_state(self):
        if not self.keeped:
            self.period -= 1
            if not self.period:
                self.active = False

        if self.dimensions['radius'] < self.max_propagation:
            self.dimensions['radius'] = min(self.dimensions['radius'] + self.propagation_per_step, self.max_propagation)

        if self.nodes_per_propagation:
            self.list_of_nodes.extend(self.nodes_per_propagation.pop(0))
