# based on https://github.com/agentcontest/massim/blob/master/server/src/main/java/massim/scenario/city/util
# /Generator.java

import random
from src.simulation.data.events.flood import Flood
from src.simulation.data.events.photo import Photo
from src.simulation.data.events.victim import Victim
from src.simulation.data.events.water_sample import WaterSample
from pyroutelib3 import Router  # Import the router
import math
import json

class Generator:

    total_photos = 0
    total_water_samples = 0
    total_victims = 0
    def __init__(self, config):

        self.config = config
        random.seed(config['map']['randomSeed'])
        self.router = Router("car", config['map']['map'])  # Initialise router object from pyroutelib3

    def generate_events(self):

        global total_photos, total_water_samples, total_victims
        events = [None for x in range(self.config['map']['steps'])]
        events[0] = self.generate_flood()
        for step in range(len(events) - 1):

            # generate floods (index 0) and photo events (index 1)

            if random.randint(0, 100) <= self.config['generate']['floodProbability'] * 10:
                events[step + 1] = self.generate_flood()

        data = {}
        data['photos'] = [{
            'total': total_photos,
            'done': 0
        }]
        data['victims'] = [{
            'total': total_victims,
            'done': 0
        }]
        data['water_sample'] = [{
            'total': total_water_samples,
            'done': 0
        }]

        with open('results.txt', 'w') as outfile:
            json.dump(data, outfile)

        return events

    def generate_flood(self):

        # flood period

        period = random.randint(self.config['generate']['flood']['minPeriod'],
                                self.config['generate']['flood']['maxPeriod'])

        # flood dimensions

        dimensions = dict()

        dimensions['shape'] = 'circle' if random.randint(0, 1) == 0 else 'rectangle'

        if dimensions['shape'] == 'circle':

            dimensions['radius'] = (
                random.randint(self.config['generate']['flood']['circle']['minRadius'],
                               self.config['generate']['flood']['circle']['maxRadius'])
            )


        else:

            dimensions['height'] = (
                random.randint(self.config['generate']['flood']['rectangle']['minHeight'],
                               self.config['generate']['flood']['rectangle']['maxHeight'])
            )

            dimensions['length'] = (
                random.randint(self.config['generate']['flood']['rectangle']['minLength'],
                               self.config['generate']['flood']['rectangle']['maxLength'])
            )

        flood_lat = random.uniform(self.config['map']['minLat'], self.config['map']['maxLat'])
        flood_lon = random.uniform(self.config['map']['minLon'], self.config['map']['maxLon'])
        dimensions['coord'] = flood_lat, flood_lon

        # generate the list of nodes that are in the flood
        if dimensions['shape'] == 'circle':
            list_of_nodes = self.nodes_in_radius(dimensions.get('coord'), dimensions.get('radius'))

        else:
            if dimensions.get('height')<dimensions.get('length'):
                list_of_nodes = self.nodes_in_radius(dimensions.get('coord'), dimensions.get('height'))
            else:
                list_of_nodes = self.nodes_in_radius(dimensions.get('coord'), dimensions.get('length'))

        photos = self.generate_photos(list_of_nodes)
        water_samples = self.generate_water_samples(list_of_nodes)
        victims = self.generate_victims(list_of_nodes)

        return Flood(period, dimensions, photos, water_samples, victims)

    def generate_photos(self, nodes):

        global total_photos
        photos = [None for x in range(random.randint(
            self.config['generate']['photo']['minAmount'],
            self.config['generate']['photo']['maxAmount']
        ))]

        total_photos += len(photos)
        for x in range(len(photos)):
            node = random.choice(nodes)
            photo_size = self.config['generate']['photo']['size']

            if random.randint(0, 100) <= self.config['generate']['photo']['victimProbability'] * 100:

                photo_victims = self.generate_victims(node)

            photos[x] = Photo(photo_size, photo_victims, node)

        return photos

    def generate_victims(self, nodes):

        global total_victims
        photo_victims = [None for x in range(random.randint(
                    self.config['generate']['victim']['minAmount'],
                    self.config['generate']['victim']['maxAmount']
        ))]
        
        total_victims += len(photo_victims)
        for y in range(len(photo_victims)):
            node = random.choice(nodes)
            victim_size = random.randint(
                self.config['generate']['victim']['minSize'],
                self.config['generate']['victim']['maxSize']
                #
            )

            victim_lifetime = random.randint(
                self.config['generate']['victim']['minLifetime'],
                self.config['generate']['victim']['maxLifetime']
            )

            photo_victims[y] = Victim(victim_size, victim_lifetime, node)

        return photo_victims

    def generate_water_samples(self, nodes):

        global total_water_samples
        water_samples = [None for x in range(random.randint(
            self.config['generate']['waterSample']['minAmount'],
            self.config['generate']['waterSample']['maxAmount']
        ))]

        total_water_samples += len(water_samples)
        for x in range(len(water_samples)):
            node = random.choice(nodes)
            water_samples[x] = WaterSample(self.config['generate']['waterSample']['size'], node)

        return water_samples

    def nodes_in_radius(self, coord, radius):
        # radius in kilometers
        result = []
        for node in self.router.rnodes:
            if self.router.distance(self.node_to_radian(node), self.coords_to_radian(coord)) <= radius:
                result.append(node)
        return result

    def node_to_radian(self, node):
        """Returns the radian coordinates of a given OSM node"""
        return self.coords_to_radian(self.router.nodeLatLon(node))

    def coords_to_radian(self, coords):
        """Maps a coordinate from degrees to radians"""
        return list(map(math.radians, coords))