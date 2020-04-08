import random
import json
from simulation_engine.simulation_objects.flood import Flood
from simulation_engine.simulation_objects.photo import Photo
from simulation_engine.simulation_objects.victim import Victim
from simulation_engine.simulation_objects.water_sample import WaterSample

from simulation_engine.simulation_objects.social_asset_marker import SocialAssetMarker
from simulation_engine.generator.genarator_base import GeneratorBase

class Loader(GeneratorBase):
    """Class that generate all the events step, by step or separated if needed."""

    def __init__(self, config, map, path_to_events):
        super(Loader, self).__init__(config, map)
        self.events = json.load(open(path_to_events, 'r'))

    def generate_events(self, map) -> list:
        events: list = [0] * len(self.events['matchs'][0]['steps'])
        
        for idx, step in enumerate(self.events['matchs'][0]['steps']):
            sim_step = dict(flood=None, victims=[], photos=[], water_samples=[])

            if step is not None:
                # sim_step['flood'] = Flood(step['flood'])
                # print("Teste: ", sim_step['flood'].__dict__)
                # sim_step['flood'] = Flood(step['flood']['identifier'], step['flood']['period'], step['flood']['keeped'],
                #                           step['flood']['dimensions'], step['flood']['list_of_nodes'])
                nodes = self.get_nodes(step['flood']['dimensions']['location'],step['flood']['dimensions']['shape'],step['flood']['dimensions']['radius'])
                (max_propagation, propagation_per_step, nodes_propagation, propagation) = self.generate_propagation(step['flood']['propagation2'], step['flood']['dimensions'], nodes, map)
                
                sim_step['step'] = step['step']
                sim_step['flood'] = Flood(step['flood']['identifier'], step['flood']['period'], step['flood']['keeped'],
                                          step['flood']['dimensions'], nodes, max_propagation, propagation_per_step, step['flood']['propagation2']['victimProbability'], nodes_propagation)
                # sim_step['propagation'] = propagation
                self.flood_id += 1

                sim_step['victims'] = [Victim(victim['flood_id'], victim['identifier'], victim['size'], victim['lifetime'],
                                              victim['location'], victim['in_photo']) for victim in step['victims']]
                self.victim_id += len(sim_step['victims'])

                sim_step['propagation']: [Victim(victim['flood_id'], victim['identifier'], victim['size'], victim['lifetime'],
                                              victim['location'], victim['in_photo']) for victim in step['propagation']]
                self.victim_id += len(sim_step['victims'])

                photos = []
                for photo in step['photos']:
                    victims_in_photo = [Victim(victim['flood_id'], victim['identifier'], victim['size'],
                                               victim['lifetime'], victim['location'], victim['in_photo'])
                                        for victim in photo['victims']]
                    self.victim_id += len(victims_in_photo)

                    photos.append(Photo(photo['flood_id'], photo['identifier'], photo['size'], victims_in_photo,
                                        photo['location']))

                sim_step['photos'] = photos
                self.photo_id += len(photos)

                sim_step['water_samples'] = [WaterSample(sample['flood_id'], sample['identifier'], sample['size'],
                                             sample['location']) for sample in step['water_samples']]
                self.water_sample_id += len(sim_step['water_samples'])

            events[idx] = sim_step

        return events

    def generate_social_assets(self) -> list:
        social_assets: list = [0] * len(self.events['matchs'][0]['social_assets'])

        for idx, asset in enumerate(self.events['matchs'][0]['social_assets']):
            social_assets[idx] = SocialAssetMarker(asset['identifier'], asset['location'],
                                                   asset['profession'], asset['abilities'], asset['resources'])

        return social_assets
