
import obspy
import numpy as np
import warnings

from copy import copy
from obspy import Stream
from obspy.geodetics import gps2dist_azimuth



class Dataset(list):
    """ Seismic data container

    A list of ObsPy streams in which each stream corresponds to a single
    seismic station

    .. note::

        Each supported file format has a corresponding reader that creates an
        Dataset (see ``mtuq.io.readers``).

    """
    def __init__(self, streams=[], id=None, tags=[]):
        """ Constructor
        """
        self.id = id

        for _i, stream in enumerate(streams):
            self.append(stream)

        for tag in copy(tags):
            self.add_tag(tag)



    def append(self, stream):
        """ Appends stream to dataset
        """
        assert issubclass(type(stream), Stream),\
            ValueError("Only Streams can be appended to a Dataset")

        # create unique identifier
        try:
            stream.id = '.'.join([
                stream.station.network,
                stream.station.station,
                stream.station.location])
        except:
            stream.id = '.'.join([
                stream[0].stats.network,
                stream[0].stats.station,
                stream[0].stats.location])

        if not hasattr(stream, 'tags'):
            stream.tags = list()

        if not hasattr(stream, 'station'):
            warnings.warn("Stream lacks station metadata")
        elif not hasattr(stream, 'origin'):
            warnings.warn("Stream lacks origin metadata")
        else:
            (stream.distance_in_m, stream.azimuth, _) =\
                gps2dist_azimuth(
                    stream.origin.latitude,
                    stream.origin.longitude,
                    stream.station.latitude,
                    stream.station.longitude)

        super(Dataset, self).append(stream)


    def apply(self, function, *args, **kwargs):
        """ Applies function to all streams in the dataset

        Applies a function to each Stream, similar to the Python built-in
        ``apply``.
        """
        processed = []
        for stream in self:
            processed += [function(stream, *args, **kwargs)]

        return self.__class__(
            processed, id=self.id)


    def map(self, function, *sequences):
        """ Maps function to all streams in the dataset

        Applies a function to each Stream. If one or more optional sequences 
        are given, the function is called with an argument list consisting of
        corresponding items of each sequence. Similar to the Python built-in
        ``map``.
        """
        processed = []
        for _i, stream in enumerate(self):
            args = [sequence[_i] for sequence in sequences]
            processed += [function(stream, *args)]

        return self.__class__(
            processed, id=self.id)


    def max(self):
        """ Returns maximum absolute amplitude over all traces
        """
        max_all = -np.inf
        for stream in self:
            for trace in stream:
                if not getattr(trace, 'weight', 1.):
                    continue
                if trace.data.max() > max_all:
                    max_all = abs(trace.data).max()
        return max_all


    def sort_by_distance(self, reverse=False):
        """ Sorts in-place by hypocentral distance
        """
        self.sort_by_function(lambda data: data.distance_in_m,
            reverse=reverse)


    def sort_by_azimuth(self, reverse=False):
        """ Sorts in-place by source-receiver azimuth
        """
        self.sort_by_function(lambda data: data.azimuth,
            reverse=reverse)


    def sort_by_function(self, function, reverse=False):
        """ Sorts in-place by user-supplied function
        """
        self.sort(key=function, reverse=reverse)


    def get_stations(self):
        """ Extracts station metadata from all streams in list
        """
        stations = []
        for stream in self:
            stations += [stream.station]
        return stations


    def get_origins(self):
        """ Returns origin location and time

        The origin attribute can be used to hold preliminary origin information
        (e.g. catalog event locations)
        """
        origins = []
        for stream in self:
            origins += [stream.origin]

            if getattr(self, '_warnings', True):
                if stream.origin!=self[0].origin:
                    warnings.warn(
                        "Different streams in the Dataset correpond to "
                        "different events.\n\n"
                        "If this is expected, feel free to disable this warning "
                        "warning by setting Dataset._warnings=False")

        return origins


    def add_tag(self, tag):
       """ Appends string to tags list
       
       Tags can be used to support customized uses, such as storing metdata not
       included in mtuq.Station
       """
       if type(tag) not in [str, unicode]:
           raise TypeError

       for stream in self:
           stream.tags.append(tag)


    def remove_tag(self, tag):
       """ Removes string from tags list
       """
       for stream in self:
           stream.tags.remove(tag)


    #
    # the remaining methods can be used to speed up trace data access in cases
    # where the time discretization is the same for all traces
    #
    def _check_time_sampling(self):
        """ Checks that time discretization is the same for all stations
        """
        pass


    def as_array(self):
        """ Returns time series from all stations in a single multidimensional
        array 

        .. warning:

            This method requires that all tensors have the same time 
            discretization.

        .. note:

            Compared with iterating over obspy traces, this method provides a
            a potentially faster way of accessing numeric trace data.

        .. note:

            This method is used to supply input arrays for the C extension
            module `mtuq.grid_search._extensions`.

        """
        try:
            return self._array
        except:
            self._allocate_array()
            return self._array


    def _allocate_array(self):
        # count number of nonempty streams
        ns = 0
        for stream in self:
            if len(stream)==0:
                ns += 1
        nt = self[0][0].stats.npts

        # allocate array
        self._array = np.zeros((3, ns, nt))
        array = self._array

        _i = 0
        for stream in self:
            if len(stream)==0:
                continue
            try:
                trace = stream.select(component='Z')
                array[0, _i, :] = trace.data
            except:
                pass
            try:
                trace = stream.select(component='R')
                array[1, _i, :] = trace.data
            except:
                pass
            try:
                trace = stream.select(component='T')
                array[2, _i, :] = trace.data
            except:
                pass
            _i += 1



