
import numpy as np
import warnings

from copy import copy, deepcopy
from mtuq.event import Origin
from mtuq.station import Station
from mtuq.dataset import Dataset
from mtuq.util.signal import check_time_sampling
from obspy.core import Stream, Trace
from obspy.geodetics import gps2dist_azimuth
from scipy.signal import fftconvolve


class GreensTensor(Stream):
    """ Holds multiple time series corresponding to the independent elements 
    of an elastic Green's tensor

    .. note::

        Besides the methods below, `GreensTensor` includes many useful
        data processing methods inherited from ``obspy.core.Stream``. See
        `ObsPy documentation <https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.html>`_
        for more information. 

    """
    def __init__(self, 
            traces=None, 
            station=None, 
            origin=None,
            id=None, 
            tags=[],
            include_mt=True,
            include_force=False):
        """ Constructor method
        """

        # argument checking starts now
        for trace in traces:
            assert isinstance(trace, Trace)

        assert check_time_sampling(traces), NotImplementedError(
            "Time sampling differs from trace to trace.")

        super(GreensTensor, self).__init__(traces)

        if not isinstance(station, Station):
            raise TypeError

        if not isinstance(origin, Origin):
            raise TypeError

        # the main work of the constructor starts now
        if id:
            self.id = id
        else:
            self.id = station.id

        self.station = station.copy()
        self.origin = origin.copy()
        self.tags = tags
        self.include_mt = include_mt
        self.include_force = include_force

        self.distance_in_m, self.azimuth, _ = gps2dist_azimuth(
            origin.latitude,
            origin.longitude,
            station.latitude,
            station.longitude)


    def _set_components(self, components):
        """ Gets called before or during `get_synthetics` to specify which
        components are returned

        .. note:

          Sometimes it makes sense to call this method partway through a 
          script. For example, if all three componets are originally present 
          at a particular station but the transerve component is later 
          discovered to be bad, calling ``_set_components(['Z', 'R'])``
          would remove it

        """
        if components==getattr(self, 'components', None):
            return

        if components is None:
            components = []

        for component in components:
            assert component in ['Z', 'R', 'T']

        self.components = components

        self._preallocate()
        self._precompute()


    def _preallocate(self):
        """ Preallocates structures used by `get_synthetics`

        .. note:

            Every time ``get_synthetics(inplace=True)`` is called, the numeric 
            trace data get overwritten. Every time ``_set_components`` is 
            called, the traces get overwritten.  The stream itself never gets
            overwritten.
        """
        nc, nr, nt = self._get_shape()

        # allocate NuPy array to hold Green's function time series
        self._array = np.zeros((nc, nr, nt))

        # allocate ObsPy structures to hold synthetics
        self._synthetics = self._allocate_stream()


    def _precompute(self):
        """ Precomputes NumPy array used by `get_synthetics`
        """
        # the formulas relating the original time series to the linear
        # combination array vary depending on the scheme being used, so
        # are deferred to the subclass
        raise NotImplementedError("Must be implemented by subclass.")


    def _get_shape(self):
        """ Returns shape of NumPy array used by `get_synthetics`
        """
        nt = len(self[0].data)
        nc = len(self.components)
        nr = 0

        if self.include_mt:
            nr += 6
        if self.include_force:
            nr+= 3

        return nc, nr, nt


    def _allocate_stream(self):
        """ Allocates ObsPy stream used by `get_synthetics`
        """
        nc, nr, nt = self._get_shape()

        stream = Stream()
        for component in self.components:
            # add stats object
            stats = self.station.copy()
            stats.update({'npts': nt, 'channel': component})
            # add trace object
            stream += Trace(np.zeros(nt), stats)

        return stream



    def get_synthetics(self, source, components=None, inplace=False):
        """ Generates synthetics through a linear combination of time series

        Returns an ObsPy stream

        .. rubric :: Input arguments

        ``source`` (`MomentTensor`, `Force` or `CompositeSource`):
        Source object

        ``components`` (`list`):
        List containing zero or more of the following components: 
        ``Z``, ``R``, ``T``. (Defaults to ``['Z', 'R', 'T']``.)
        
        """

        if components is None:
            # Components argument was not given, so check that attribute is
            # already set
            assert(hasattr(self, 'components'))

        else:
            self._set_components(components)

        # arrays used in linear combination
        source = source.as_vector()
        array = self._array

        if inplace:
            synthetics = self._synthetics
        else:
            synthetics = self._allocate_stream()

        for _i, component in enumerate(self.components):
            # Even with careful attention to index order, np.dot is very slow.
            # For some reason the following is faster
            data = synthetics[_i].data
            data[:] = 0.
            for _j in range(len(source)):
                data += source[_j]*array[_i, _j, :]
        return synthetics


    def convolve(self, wavelet):
        """ Convolves time series with given wavelet

        Returns MTUQ `GreensTensor`

        .. rubric :: Input arguments

        ``wavelet`` (`Wavelet` object):
        Source wavelet

        """
        for trace in self:
            wavelet.convolve(trace)


    def select(self, component=None, channel=None):
        """ Selects time series that match the supplied metadata criteria
        """
        return Stream([trace for trace in self]).select(
            component=component, channel=channel)


    def __add__(self, *args):
        raise Exception("Adding time series to an existing GreensTensor is "
           " not currently supported")


    def __iadd__(self, *args):
        raise Exception("Adding time series to an existing GreensTensor is "
           " not currently supported")



class GreensTensorList(list):
    """ Container for one or more `GreensTensor` objects
    """

    def __init__(self, tensors=[], id=None, tags=[]):
        # typically the id is the event name or origin time
        self.id = id

        for tensor in tensors:
            self.append(tensor)

        for tag in copy(tags):
            self.tag_add(tag)


    def append(self, tensor):
        """ Appends `GreensTensor` to the container
        """
        if not hasattr(tensor, 'station'):
            raise Exception("GreensTensor lacks station metadata")

        elif not hasattr(tensor, 'origin'):
            raise Exception("GreensTensor lacks origin metadata")

        super(GreensTensorList, self).append(tensor)


    def select(self, selector):
        """ Selects `GreensTensors` that match the given station or origin
        """
        if type(selector) is Station:
            selected = self.__class__(id=self.id, tensors=filter(
                lambda tensor: tensor.station==selector, self))

        elif type(selector) is Origin:
            selected = self.__class__(id=self.id, tensors=filter(
                lambda tensor: tensor.origin==selector, self))

        else:
            raise TypeError("Bad selector: %s" % type(selector).__name__)

        if len(selected)==0:
            if len(self) > 0:
                warnings.warn("Nothing found matching given selector "
                    "(%s)\n"  % type(selector).__name__)

        return selected


    def get_synthetics(self, *args, **kwargs):
        """ Generates synthetics through a linear combination of time series

        Returns an MTUQ `Dataset`

        .. rubric :: Input arguments

        ``source`` (`MomentTensor`, `Force` or `CompositeSource`):
        Source object

        ``components`` (`list`):
        List containing zero or more of the following components: 
        ``Z``, ``R``, ``T``. (Defaults to ``['Z', 'R', 'T']``.)
        
        """

        synthetics = Dataset()
        for tensor in self:
            synthetics.append(tensor.get_synthetics(*args, **kwargs))
        return synthetics


    # the next three methods can be used to apply signal processing or other
    # operations to all time series in all GreensTensors
    def apply(self, function, *args, **kwargs):
        """ Applies function to all `GreensTensors`
 
        Applies a function to each `GreensTensor` in the list, similar to the 
        Python built-in ``apply``.  

        .. warning ::

            Although ``apply`` returns a new `GreensTensorList`, contents of the
            original `GreensTensorList` may still be overwritten, depending on
            the function. To preserve the original, consider making a 
            `copy` first.

        """
        processed = []
        for tensor in self:
            processed +=\
                [function(tensor, *args, **kwargs)]
        return self.__class__(processed)


    def map(self, function, *sequences):
        """ Maps function to all `GreensTensors`

        Maps a function to each `GreensTensor` in the list. If one or more 
        optional sequences are given, the function is called with an argument 
        list consisting of the corresponding item of each sequence, similar
        to the Python built-in ``map``.

        .. warning ::

            Although ``map`` returns a new `GreensTensorList`, contents of the
            original `GreensTensorList` may still be overwritten, depending on
            the function. To preserve the original, consider making a 
            `copy` first.

        """
        processed = []
        for _i, tensor in enumerate(self):
            args = [sequence[_i] for sequence in sequences]
            processed +=\
                [function(tensor, *args)]
        return self.__class__(processed)


    def convolve(self, wavelet):
        """ Convolves time series with given wavelet

        Returns MTUQ `GreensTensorList`

        .. rubric :: Input arguments

        ``wavelet`` (`Wavelet` object):
        Source wavelet

        """
        for tensor in self:
            tensor.convolve(wavelet)


    def tag_add(self, tag):
       """ Appends string to tags list
       
       Tags can be used to support customized uses, such as storing metdata not
       included in ``mtuq.Station``
       """
       if type(tag) not in [str, unicode]:
           raise TypeError

       for tensor in self:
           if tag not in tensor.tags:
               tensor.tags.append(tag)


    def tag_remove(self, tag):
       """ Removes string from tags list
       """
       for tensor in self:
           if tag in tensor.tags:
               tensor.tags.remove(tag)


    def sort_by_distance(self, reverse=False):
        """ Sorts in-place by hypocentral distance
        """
        self.sort_by_function(lambda stream: stream.distance,
            reverse=reverse)


    def sort_by_azimuth(self, reverse=False):
        """ Sorts in-place by source-receiver azimuth
        """
        self.sort_by_function(lambda stream: stream.azimuth,
            reverse=reverse)


    def sort_by_function(self, function, reverse=False):
        """ Sorts in-place using the python built-in "sort"
        """
        self.sort(key=function, reverse=reverse)


    def __copy__(self):
        try:
            new_id = self.id+'_copy'
        except:
            new_id = None

        new_ds = type(self)(id=new_id)
        for stream in self:
            new_ds.append(deepcopy(stream))
        return new_ds


