class Flood:

    # still missing location attribute

    def __init__(self, period, dimensions, photos, water_samples, victims):
        """
        [Object that represents a flood.]

        :param period: The amount of steps that a flood instance
        takes at the simulation.
        :param dimensions: Representation of the shape, size,
        latitude, longitude and 'disabled' nodes of a certain flood instance.
        :param photos: All 'photography events' that were randomly generated over a
        certain flood instance.
        :param water_samples: All 'collectible water samples' that were randomly generated
        over a certain flood instance.
        """
        self.type = 'flood'
        self.active = False
        self.period = period
        self.dimensions = dimensions
        self.photos = photos
        self.water_samples = water_samples
        self.victims = victims

    def json(self):
        """Return a json like representation of the object"""
        photos = [photo.json() for photo in self.photos]
        victims = [victim.json() for victim in self.victims]
        water_samples = [water_sample.json() for water_sample in self.water_samples]
        copy = self.__dict__.copy()
        copy['photos'] = photos
        copy['victims'] = victims
        copy['water_samples'] = water_samples
        return copy
