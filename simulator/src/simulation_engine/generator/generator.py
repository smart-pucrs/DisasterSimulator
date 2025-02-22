import random
import simulation_engine.simulation_helpers.events_formatter as formatter

from ..simulation_objects.flood import Flood
from ..simulation_objects.photo import Photo
from ..simulation_objects.victim import Victim
from ..simulation_objects.water_sample import WaterSample
from ..simulation_objects.social_asset_marker import SocialAssetMarker
from ..simulation_objects.event import Event
from .genarator_base import GeneratorBase


class Generator(GeneratorBase):
    """Class that generate all the events step, by step or separated if needed."""

    def __init__(self, config, map):
        self.steps = config['map']['steps']
        self.area = {attr:config['map']['maps'][0][attr] for attr in ['minLat','maxLat','minLon','maxLon']} 
        self.generate_variables: dict = config['generate']
        self.generate_assets_variables: dict = config['socialAssets']
        self.map = map
        self.flood_id: int = 0
        self.victim_id: int = 0
        self.photo_id: int = 0
        self.water_sample_id: int = 0
        self.social_asset_id = 0
        self.measure_unit = 100000
        random.seed(config['map']['randomSeed'])

    def generate_events(self, map) -> list:
        """Generate all the events based on probabilities.

        If the probability of a flood to occur is bigger than the drawn number, an event is created. Except the first
        step which will always have a flood.

        :return list: All the steps containing either a dictionary with the event or a dictionary with a None flood."""

        events = [0] * self.steps

        flood, propagation = self.generate_event(0)
        flood.affect_map(map, self)
        nodes: list = flood.nodes
        event: dict = {
            'step': 0, 
            'flood': flood,
            'victims': self.generate_victims(nodes),
            'water_samples': self.generate_water_samples(nodes),
            'photos': self.generate_photos(nodes),
            'propagation': propagation
        }

        events[0] = event

        flood_probability: int = self.generate_variables['flood']['probability']
        i: int = 1
        while i < self.steps:
            event: dict = {'step': -1, 'flood': None, 'victims': [], 'water_samples': [], 'photos': [], 'propagation': []}

            if random.randint(1, 100) <= flood_probability:
                event['step'] = i
                event['flood'], propagation = self.generate_event(i)
                event['flood'].affect_map(map, self)
                nodes: list = event['flood'].nodes
                event['victims']: list = self.generate_victims(nodes)
                event['water_samples']: list = self.generate_water_samples(nodes)
                event['photos']: list = self.generate_photos(nodes)
                event['propagation']: list = propagation

            events[i] = event
            i += 1

        from simulation_engine.simulation_helpers.report import Report 
        report = Report()
        report.total_events = self.flood_id
        report.total_victims = self.victim_id
        report.total_photos = self.photo_id
        report.total_samples = self.water_sample_id

        return events

    def generate_event(self, step) -> Event:
        """Generate one flood.

        Note: The only shape available currently is the circle.

        :return Flood: Flood event with dimensions gotten from the configuration file."""

        dimensions: dict = {'shape': 'circle', 'radius': (
            random.uniform(self.generate_variables['flood']['circle']['minRadius'],
                           self.generate_variables['flood']['circle']['maxRadius']) / self.measure_unit
        )}

        flood_lat: float = random.uniform(self.area['minLat'], self.area['maxLat'])
        flood_lon: float = random.uniform(self.area['minLon'], self.area['maxLon'])

        dimensions['location']: tuple = self.map.align_coords(flood_lat, flood_lon)

        if dimensions['shape'] == 'circle':
            list_of_nodes: list = self.map.nodes_in_radius(dimensions['location'], dimensions['radius'])

        else:
            if dimensions['height'] < dimensions['length']:
                list_of_nodes: list = self.map.nodes_in_radius(dimensions['location'], dimensions['height'])
            else:
                list_of_nodes: list = self.map.nodes_in_radius(dimensions['location'], dimensions['length'])

        if self.generate_variables['flood']['minPeriod']:
            period: int = int((random.randint(self.generate_variables['flood']['minPeriod'],
                                              self.generate_variables['flood']['maxPeriod']) / self.generate_variables[
                                   'step_unit']))

            keeped = False
        else:
            period = 0
            keeped = True

        propagation: list = []
        nodes_propagation: list = []
        max_propagation: float = 0.0
        propagation_per_step: float = 0.0
        victim_probability: int = 0

        self.flood_id = self.flood_id + 1

        d_prop: dict = None
        if self.generate_variables['flood']['propagation']:
            d_prop = {}
            prop_info = self.generate_variables['flood']['propagationInfo']
            d_prop['max'] = (prop_info['maxPropagation'] / 100) * dimensions['radius'] + dimensions['radius']
            d_prop['perStep'] = prop_info['propagationPerStep'] / 100 * dimensions['radius']

            victim_probability = prop_info['victimsPerPropagationProbability']
            old_nodes: list = list_of_nodes

            until = range(int(((prop_info['maxPropagation'] / 100) * dimensions['radius'] / d_prop['perStep'])))
            for prop in until:
                new_nodes = self.map.nodes_in_radius(dimensions['location'],
                                                     dimensions['radius'] + d_prop['perStep'] * prop)
                difference = self.get_difference(old_nodes, new_nodes)

                if random.randint(0, 100) < victim_probability:
                    if difference:
                        propagation.append(self.generate_victims_in_propagation(difference))
                    else:
                        propagation.append(self.generate_victims_in_propagation(new_nodes))

                nodes_propagation.append(difference)
                old_nodes = new_nodes

            d_prop['max'] = prop_info['maxPropagation']
            d_prop['perStep'] = prop_info['propagationPerStep']
        
        return Event(self.flood_id, step, step+period, dimensions, d_prop), propagation

    def generate_photos(self, nodes: list) -> list:
        """Generate a list of photo events inside the flood location.

        Note: Each photo can have N victims.

        :return list: List with all the photos generated."""

        victim_probability: int = self.generate_variables['photo']['victimProbability']
        photo_min_size: int = self.generate_variables['photo']['minSize']
        photo_max_size: int = self.generate_variables['photo']['maxSize']

        amount: int = random.randint(self.generate_variables['photo']['minAmount'],
                                     self.generate_variables['photo']['maxAmount'])
        photos: list = [0] * amount
        i: int = 0
        while i < amount:
            photo_location: tuple = self.map.get_node_coord(random.choice(nodes))
            photo_size: int = random.randint(photo_min_size, photo_max_size)
            photo_victims: list = []
            if random.randint(0, 100) <= victim_probability:
                photo_victims = self.generate_photo_victims(photo_location)

            photos[i] = Photo(self.flood_id, self.photo_id, photo_size, photo_location, photo_victims)
            self.photo_id = self.photo_id + 1
            i += 1

        return photos

    def generate_victims(self, nodes: list) -> list:
        """Generate a list of victims.

        :return list: List of all the victims generated"""

        victim_min_size: int = self.generate_variables['victim']['minSize']
        victim_max_size: int = self.generate_variables['victim']['maxSize']

        victim_min_lifetime: int = self.generate_variables['victim']['minLifetime']
        victim_max_lifetime: int = self.generate_variables['victim']['maxLifetime']

        amount: int = random.randint(self.generate_variables['victim']['minAmount'],
                                     self.generate_variables['victim']['maxAmount'])
        victims: list = [0] * amount
        i: int = 0
        while i < amount:
            victim_size: int = random.randint(victim_min_size, victim_max_size)
            victim_lifetime: int = int(random.randint(victim_min_lifetime, victim_max_lifetime)
                                       / self.generate_variables['step_unit'])

            victim_location: tuple = self.map.get_node_coord(random.choice(nodes))

            victims[i] = Victim(self.flood_id, self.victim_id, victim_size, victim_lifetime, victim_location, False)
            self.victim_id = self.victim_id + 1
            i += 1

        return victims

    def generate_victims_in_propagation(self, nodes: list) -> list:
        victim_min_size: int = self.generate_variables['victim']['minSize']
        victim_max_size: int = self.generate_variables['victim']['maxSize']

        victim_min_lifetime: int = self.generate_variables['victim']['minLifetime']
        victim_max_lifetime: int = self.generate_variables['victim']['maxLifetime']

        amount: int = random.randint(self.generate_variables['flood']['propagationInfo']['minVictimsPerPropagation'],
                                     self.generate_variables['flood']['propagationInfo']['maxVictimsPerPropagation'])
        victims: list = [0] * amount
        i: int = 0
        while i < amount:
            victim_size: int = random.randint(victim_min_size, victim_max_size)
            victim_lifetime: int = int(random.randint(victim_min_lifetime, victim_max_lifetime)
                                       / self.generate_variables['step_unit'])

            victim_location: tuple = self.map.get_node_coord(random.choice(nodes))

            victims[i] = Victim(self.flood_id, self.victim_id, victim_size, victim_lifetime, victim_location, False)
            self.victim_id = self.victim_id + 1
            i += 1

        return victims

    def generate_photo_victims(self, location: tuple) -> list:
        """Generate list of victims for photos.

        Note: the victims will be generated on the same location as the photo.

        :return list: List with all the generated Victims."""

        victim_min_size: int = self.generate_variables['victim']['minSize']
        victim_max_size: int = self.generate_variables['victim']['maxSize']

        victim_min_lifetime: int = self.generate_variables['victim']['minLifetime']
        victim_max_lifetime: int = self.generate_variables['victim']['maxLifetime']

        amount: int = random.randint(self.generate_variables['victim']['minAmount'],
                                     self.generate_variables['victim']['maxAmount'])
        victims: list = [0] * amount
        i: int = 0
        while i < amount:
            victim_size: int = random.randint(victim_min_size, victim_max_size)
            victim_lifetime: int = int(random.randint(victim_min_lifetime, victim_max_lifetime)
                                       / self.generate_variables['step_unit'])

            victims[i] = Victim(self.flood_id, self.victim_id, victim_size, victim_lifetime, location, True)
            self.victim_id = self.victim_id + 1
            i += 1

        return victims

    def generate_water_samples(self, nodes: list) -> list:
        """Generate list of water samples.

        :return list: List with all the generated water samples."""

        water_sample_min_size: int = self.generate_variables['waterSample']['minSize']
        water_sample_max_size: int = self.generate_variables['waterSample']['maxSize']

        amount: int = random.randint(self.generate_variables['waterSample']['minAmount'],
                                     self.generate_variables['waterSample']['maxAmount'])
        water_samples: list = [0] * amount
        i: int = 0
        while i < amount:
            water_sample_location: tuple = self.map.get_node_coord(random.choice(nodes))
            water_sample_size: int = random.randint(water_sample_min_size, water_sample_max_size)
            water_samples[i] = WaterSample(self.flood_id, self.water_sample_id, water_sample_size,
                                           water_sample_location)
            self.water_sample_id = self.water_sample_id + 1
            i += 1

        return water_samples

    def generate_social_assets(self):
        amount: int = self.generate_variables['socialAsset']['amount']

        social_assets: list = [0] * amount

        i: int = 0
        while i < amount:
            location: list = [random.uniform(self.area['minLat'], self.area['maxLat']),
                              random.uniform(self.area['minLon'], self.area['maxLon'])]
            profession: str = random.choice(self.generate_variables['socialAsset']['professions'])
            abilities = self.generate_assets_variables[profession]['abilities']
            resources = self.generate_assets_variables[profession]['resources']

            social_assets[i] = SocialAssetMarker(self.social_asset_id, location, profession,
                                                 abilities, resources)
            self.social_asset_id += 1
            i += 1

        return social_assets

    @staticmethod
    def get_json_social_assets(social_assets):
        return formatter.format_assets(social_assets)
