import random
import simulation_engine.simulation_helpers.events_formatter as formatter

# from simulation_engine.simulation_objects.flood import Flood
# from simulation_engine.simulation_objects.photo import Photo
# from simulation_engine.simulation_objects.victim import Victim
# from simulation_engine.simulation_objects.water_sample import WaterSample
# from simulation_engine.simulation_objects.social_asset_marker import SocialAssetMarker

from abc import ABCMeta, abstractmethod

class GeneratorBase(object):
    __metaclass__ = ABCMeta
    
    def __init__(self, config, map):
        self.general_map_variables: dict = config['map']
        self.current_map_variables: dict = config['map']['maps'][0]
        self.generate_variables: dict = config['generate']
        self.generate_assets_variables: dict = config['socialAssets']
        self.map = map
        self.flood_id: int = 0
        self.victim_id: int = 0
        self.photo_id: int = 0
        self.water_sample_id: int = 0
        self.social_asset_id = 0
        self.measure_unit = 100000
        self.max_steps =  config['map']['steps']
        random.seed(config['map']['randomSeed'])

    @abstractmethod
    def generate_events(self, map) -> list:
        raise NotImplementedError("Must override to generate events")

    @abstractmethod
    def generate_social_assets(self) -> list:
        raise NotImplementedError("Must override to social assets options")

    # TODO: fix this to any shape 
    def get_nodes(self, position, shape, radius)-> list:
        if shape == 'circle':
            list_of_nodes: list = self.map.nodes_in_radius(position, radius)
        return list_of_nodes

    # def generate_propagation(self, prop, dimension, nodes, map) -> (float,float,list,list):
    #     if prop['perStep'] == 0:
    #         return (0.0,0.0,[],[])
        
    #     propagation: list = []
    #     nodes_propagation: list = []
    #     max_propagation: float = 0.0
    #     propagation_per_step: float = 0.0
        
    #     max_propagation = (prop['max'] / 100) * dimension['radius'] + dimension['radius']
    #     propagation_per_step = prop['perStep'] / 100 * dimension['radius']

    #     prob_victim: int = prop['victimProbability']
    #     old_nodes: list = nodes

    #     for prop in range(int(((prop['max'] / 100) * dimension['radius'] / propagation_per_step))):
    #         new_nodes = map.nodes_in_radius(dimension['location'],
    #                                                 dimension['radius'] + propagation_per_step * prop)
    #         difference = self.get_difference(old_nodes, new_nodes)

    #         # if random.randint(0, 100) < prob_victim:
    #         #     if difference:
    #         #         propagation.append(self.generate_victims_in_propagation(difference))
    #         #     else:
    #         #         propagation.append(self.generate_victims_in_propagation(new_nodes))

    #         nodes_propagation.append(difference)
    #         old_nodes = new_nodes
    #     return (max_propagation, propagation_per_step, nodes_propagation, propagation)
    def generate_propagation(self, epicentre, radius, maximum, perStep, nodes, map) -> (float,float,list,list):
        if (perStep == 0):
            return []
        nodes_propagation: list = []        
        old_nodes: list = nodes

        maximun_radius = ((maximum / 100)+1) * radius
        increase_perStep = perStep / 100 * radius

        until = range(int(maximum / perStep))
        for prop in until:
            new_nodes = map.nodes_in_radius(epicentre, radius + increase_perStep * prop)
            difference = self.get_difference(old_nodes, new_nodes)

            nodes_propagation.append(difference)
            old_nodes = new_nodes
        return nodes_propagation

    def get_difference(self, node_list1, node_list2):
        return [node for node in node_list1 if node in node_list2]

    @staticmethod
    def get_json_events(events):
        json_events = []

        for event in events:
            events_dict = None

            if event['flood'] is not None:
                events_dict = dict()
                events_dict['step'] = event['step']
                events_dict['flood'] = formatter.format_flood(event['flood'])
                events_dict['victims'] = formatter.format_victims(event['victims'])
                events_dict['photos'] = formatter.format_photos(event['photos'])
                events_dict['water_samples'] = formatter.format_water_samples(event['water_samples'])

            json_events.append(events_dict)

        return json_events

    @staticmethod
    def get_json_social_assets(social_assets):
        return formatter.format_assets(social_assets)
