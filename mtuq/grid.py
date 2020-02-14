

import numpy as np

from builtins import object
from numpy import pi as PI
from numpy.random import uniform as random
from mtuq.util import AttribDict, asarray
from mtuq.util.math import open_interval as regular
from mtuq.util.lune import to_mij, to_rtp, to_rho



class Grid(object):
    """
    A regularly-spaced grid defined by values along axes

    .. rubric:: Examples

    To cover the unit square with an `N`-by-`N` rectangular grid:

    .. code ::

       x = np.linspace(0., 1., N)
       y = np.linspace(0., 1., N)
       grid = Grid(dims=('x','y'), coords=(x, y))


    To parameterize the surface of the Earth with an `N`-by-`2N` Mercator grid:

    .. code::          

       lat = np.linspace(-90., 90., N)
       lon = np.linspace(-90., 90., N)
       grid = Grid(dims=('lat', 'lon'), coords=(lat, lon))


    .. rubric:: Iterating over grids

    Iterating over a grid is similar to iterating over a multidimensional 
    NumPy array.  The order of grid points is determined by the order of axes
    used to create the grid.  For instance, in the unit square example above, 
    ``'x'`` is the fast axis and ``'y'`` is the slow axis.

    If ``start`` and ``stop`` arguments are given when creating a grid,
    iteration will begin and end at these indices.  Otherwise, iteration will
    begin at the first index (`i=0`) and stop at the last index.


    .. rubric:: Accessing individual grid points

    Individual grid points can be accessed through the ``get`` and ``get_dict``
    methods.  

    ``get(i)`` returns the i-th grid point as a NumPy array.

    If a ``callback`` function is given when creating a grid, then ``get`` 
    returns the result of applying the callback to the i-th grid point.  This
    behavior can be overridden by supplying a callback function as a keyword
    argument to ``get`` itself.  If ``callback`` is ``None``, then no function 
    is applied.

    ``get_dict(i)`` returns the i-th grid point as a dictionary of coordinate
    axis names and coordinate values without applying any callback.

    """
    def __init__(self, dims=None, coords=None, start=0, stop=None, callback=None):
        # list of axis names
        self.dims = dims
        
        # corresponding list of axis coordinates
        self.coords = list(map(asarray, coords))

        # what is the length along each axis?
        shape = []
        for array in self.coords:
            shape += [len(array)]

        # what attributes would the grid have if stored as a numpy array?
        self.ndim = len(shape)
        self.shape = shape

        # what part of the grid do we want to iterate over?
        self.start = start
        if stop:
            self.stop = stop
            self.size = stop-start
        else:
            self.stop = np.product(shape)
            self.size = np.product(shape)-start
        self.index = start

        self.callback = callback

 
    def as_array(self, **kwargs):
        """ Returns the entire set of grid points as a multidimensional 
        Numpy array

        .. rubric:: callback functions

        If a ``callback`` function was given when creating a grid, then 
        ``as_array`` returns the result of applying the callback to the 
        i-th grid point.  This behavior can be overridden by supplying a 
        callback function as a keyword argument to ``as_array`` itself.  
        If ``callback`` is ``None``, then no function is applied.

        """
        # optionally override default callback
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = self.callback

        array = np.zeros((self.size, self.ndim))
        for _i in range(self.size):
            array[_i, :] = self.get(_i, callback=callback)
        return array


    def as_xarray(self, values):
        """ Returns a set of values defined on grid as an xarray DataArray
        """
        try:
            from xarray import DataArray
        except ImportError:
            raise ImportError("xarray not installed")

        return DataArray(values, dims=self.dims, coords=self.coords)


    def get(self, i, **kwargs):
        """ Returns `i-th` grid point

        .. rubric:: callback functions

        If a ``callback`` function was given when creating a grid, then 
        ``geet`` returns the result of applying the callback to the 
        i-th grid point.  This behavior can be overridden by supplying a 
        callback function as a keyword argument to ``geet`` itself.  
        If ``callback`` is ``None``, then no function is applied.
        """
        # optionally override default callback
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = self.callback

        vals = self.coords
        array = np.zeros(self.ndim)

        for _k in range(self.ndim):
            val = vals[_k]
            array[_k] = val[int(i%len(val))]
            i/=len(val)

        if callback:
            return callback(*array)
        else:
            return array


    def get_dict(self, i):
        """ Returns `i-th` grid point grid as a dictionary of parameter names 
        and values
        """
        keys = self.dims
        vals = self.get(i, callback=None)

        return dict(zip(keys, vals))


    def partition(self, nproc):
        """ Partitions grid for parallel processing
        """
        if self.start!=0:
            raise Exception

        subsets = []
        for iproc in range(nproc):
            start=int(iproc*self.size/nproc)
            stop=(iproc+1)*int(self.size/nproc)
            subsets += [Grid(self.axes, start, stop, callback=self.callback)]
        return subsets


    def save(self, filename, items={}):
        """ Saves a set of values defined on grid
        """
        import h5py
        with h5py.File(filename, 'w') as hf:
            for key, val in zip(self.dims, self.coords):
                hf.create_dataset(key, data=val)

            for key, val in items.items():
                hf.create_dataset(key, data=val)


    def __len__(self):
        return self.size



    # the next two methods make it possible to iterate over the grid
    def __next__(self): 
        """ Advances iteration index
        """
        if self.index < self.stop:
           # get the i-th point in grid
           p = self.get(self.index)
        else:
            self.index = self.start
            raise StopIteration
        self.index += 1
        return p


    def __iter__(self):
        return self




class UnstructuredGrid(object):
    """ 
    An unstructured grid is defined by lists of individual coordinate points, 
    which can be irregularly spaced

    .. rubric:: Example

    Unstructured grid consisting of `N` randomly-chosen points within the unit 
    square:

    .. code ::

       x = np.random.rand(N)
       y = np.random.rand(N)
       grid = Grid(dims=('x','y'), coords=(x, y))


    .. rubric:: Iterating over grids

    Iterating over an unstructured grid is similar to iterating over a list.

    If ``start`` and ``stop`` arguments are given when creating an unstructured
    grid, iteration will begin and end at these indices.  Otherwise, iteration
    will begin at the first index (`i=0`) and stop at the last index.


    .. rubric:: Accessing individual grid points

    Individual grid points can be accessed through the ``get`` and ``get_dict``
    methods.  

    ``get(i)`` returns the i-th grid point as a NumPy array.

    If a ``callback`` function is given when creating an unstructured grid, then
    ``get`` returns the result of applying the callback to the i-th grid point.
    This behavior can be overridden by supplying a callback function as a
    keyword argument to ``get`` itself.  If ``callback`` is ``None``, then no 
    function is applied.

    ``get_dict(i)`` returns the i-th grid point as a dictionary of coordinate
    axis names and coordinate values without applying any callback.


    """
    def __init__(self, dims=None, coords=None, start=0, stop=None, callback=None):
        # list of parameter names
        self.dims = dims

        # corresponding list of parameter values
        self.coords = list(map(asarray, coords))

        # there is no shape attribute because it is an unstructured grid,
        # however, ndim and size still make sense
        self.ndim = len(self.dims)
        size = len(self.coords[0])

        # check consistency
        for array in self.coords:
            assert len(array) == size

        # what part of the grid do we want to iterate over?
        self.start = start
        if stop:
            self.stop = stop
            self.size = stop-start
        else:
            self.stop = size
            self.size = size-start

        self.index = start

        # optional map from one parameterization to another
        self.callback = callback


    def as_array(self, **kwargs):
        """ Returns the entire set of grid points as a multidimensional 
        Numpy array

        .. rubric:: callback functions

        If a ``callback`` function was given when creating a grid, then 
        ``as_array`` returns the result of applying the callback to the 
        i-th grid point.  This behavior can be overridden by supplying a 
        callback function as a keyword argument to ``as_array`` itself.  
        If ``callback`` is ``None``, then no function is applied.

        """

        # optionally override default callback
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = self.callback

        array = np.zeros((self.size, self.ndim))
        for _i in range(self.size):
            array[_i, :] = self.get(_i+self.start, callback=callback)
        return array


    def get(self, i, **kwargs):
        """ Returns `i-th` grid point

        .. rubric:: callback functions

        If a ``callback`` function was given when creating a grid, then 
        ``geet`` returns the result of applying the callback to the 
        i-th grid point.  This behavior can be overridden by supplying a 
        callback function as a keyword argument to ``geet`` itself.  
        If ``callback`` is ``None``, then no function is applied.

        """
        # optionally override default callback
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = self.callback

        i -= self.start
        vals = self.coords
        array = np.zeros(self.ndim)

        for _k in range(self.ndim):
            array[_k] = vals[_k][i]

        if callback:
            return callback(*array)
        else:
            return array


    def get_dict(self, i):
        """ Returns `i-th` grid point as a dictionary of parameter names and
        values
        """
        keys = self.dims
        vals = self.get(i, callback=None)

        return dict(zip(keys, vals))


    def partition(self, nproc):
        """ Partitions grid for parallel processing
        """
        subsets = []
        for iproc in range(nproc):
            start=iproc*int(self.size/nproc)
            stop=(iproc+1)*int(self.size/nproc)
            coordinate_points = []
            for key, val in self.coordinate_points:
                coordinate_points += [[key, val[start:stop]]]
            subsets += [UnstructuredGrid(coordinate_points, start, stop, callback=self.callback)]
        return subsets


    def save(self, filename, items={}):
        """ Saves a set of values defined on grid
        """
        import h5py
        with h5py.File(filename, 'w') as hf:
            for key, val in zip(self.dims, self.coords):
                hf.create_dataset(key, data=val)

            for key, val in items.items():
                hf.create_dataset(key, data=val)


    def __len__(self):
        return self.size


    # the next two methods make it possible to iterate over the grid
    def __next__(self): 
        """ Advances iteration index
        """
        if self.index < self.stop:
           # get the i-th point in grid
           p = self.get(self.index)
        else:
            self.index = self.start
            raise StopIteration
        self.index += 1
        return p


    def __iter__(self):
        return self


def FullMomentTensorGridRandom(magnitudes=None, npts=1000000):
    """ Full moment tensor grid with randomly-spaced values

    Given input parameters ``magnitudes`` (`list`) and ``npts`` (`int`), 
    returns an ``UnstructuredGrid`` of size `npts*len(magnitudes)`.

    Moment tensors are drawn from the uniform distribution defined by 
    `Tape2015` (https://doi.org/10.1093/gji/ggv262)

    .. rubric :: Usage

    Use ``get(i)`` to return the i-th moment tensor as a vector
    `Mrr, Mtt, Mpp, Mrp, Mrt, Mtp`

    Use ``get_dict(i)`` to return the i-th moment tensor as dictionary
    of Tape2015 parameters `rho, v, w, kappa, sigma, h`
    """

    v = random(-1./3., 1./3., npts)
    w = random(-3./8.*PI, 3./8.*PI, npts)
    kappa = random(0., 360, npts)
    sigma = random(-90., 90., npts)
    h = random(0., 1., npts)
    rho = list(map(to_rho, asarray(magnitudes)))

    v = np.tile(v, len(magnitudes))
    w = np.tile(w, len(magnitudes))
    kappa = np.tile(kappa, len(magnitudes))
    sigma = np.tile(sigma, len(magnitudes))
    h = np.tile(h, len(magnitudes))
    rho = np.repeat(rho, npts)
    
    return UnstructuredGrid(
        dims=('rho', 'v', 'w', 'kappa', 'sigma', 'h'),
        coords=(rho, v, w, kappa, sigma, h),
        callback=to_mij)



def FullMomentTensorGridRegular(magnitudes=None, npts_per_axis=20):
    """ Full moment tensor grid with regularly-spaced values

    Given input parameters ``magnitudes`` (`list`) and ``npts`` (`int`), 
    returns a ``Grid`` of size `len(magnitudes)*npts_per_axis^5`.

    Grid discretization based on the uniform distribution defined by `Tape2015`
    (https://doi.org/10.1093/gji/ggv262)

    .. rubric :: Usage

    Use ``get(i)`` to return the i-th moment tensor as a vector
    `Mrr, Mtt, Mpp, Mrp, Mrt, Mtp`

    Use ``get_dict(i)`` to return the i-th moment tensor as dictionary
    of Tape2015 parameters `rho, v, w, kappa, sigma, h`

    """
    v = regular(-1./3., 1./3., npts_per_axis)
    w = regular(-3./8.*PI, 3./8.*PI, npts_per_axis)
    kappa = regular(0., 360, npts_per_axis)
    sigma = regular(-90., 90., npts_per_axis)
    h = regular(0., 1., npts_per_axis)
    rho = list(map(to_rho, asarray(magnitudes)))

    return Grid(
        dims=('rho', 'v', 'w', 'kappa', 'sigma', 'h'),
        coords=(rho, v, w, kappa, sigma, h),
        callback=to_mij)


def DoubleCoupleGridRandom(magnitudes=None, npts=50000):
    """ Double-couple moment tensor grid with randomly-spaced values

    Given input parameters ``magnitudes`` (`list`) and ``npts`` (`int`), 
    returns an ``UnstructuredGrid`` of size `npts*len(magnitudes)`.

    .. rubric :: Usage

    Use ``get(i)`` to return the i-th moment tensor as a vector
    `Mrr, Mtt, Mpp, Mrp, Mrt, Mtp`

    Use ``get_dict(i)`` to return the i-th moment tensor as dictionary
    of Tape2015 parameters `rho, v, w, kappa, sigma, h`

    """
    v = np.zeros(npts)
    w = np.zeros(npts)
    kappa = random(0., 360, npts)
    sigma = random(-90., 90., npts)
    h = random(0., 1., npts)
    rho = list(map(to_rho, asarray(magnitudes)))

    v = np.tile(v, len(magnitudes))
    w = np.tile(w, len(magnitudes))
    kappa = np.tile(kappa, len(magnitudes))
    sigma = np.tile(sigma, len(magnitudes))
    h = np.tile(h, len(magnitudes))
    rho = np.repeat(rho, npts)

    return UnstructuredGrid(
        dims=('rho', 'v', 'w', 'kappa', 'sigma', 'h'),
        coords=(rho, v, w, kappa, sigma, h),
        callback=to_mij)


def DoubleCoupleGridRegular(magnitudes=None, npts_per_axis=40):
    """ Double-couple moment tensor grid with regularly-spaced values

    Given input parameters ``magnitudes`` (`list`) and ``npts`` (`int`), 
    returns a ``Grid`` of size `len(magnitudes)*npts_per_axis^3`.

    .. rubric :: Usage

    Use ``get(i)`` to return the i-th moment tensor as a vector
    `Mrr, Mtt, Mpp, Mrp, Mrt, Mtp`

    Use ``get_dict(i)`` to return the i-th moment tensor as dictionary
    of Tape2015 parameters `rho, v, w, kappa, sigma, h`
    """ 
    v = 0.
    w = 0.

    kappa = regular(0., 360, npts_per_axis)
    sigma = regular(-90., 90., npts_per_axis)
    h = regular(0., 1., npts_per_axis)
    rho = list(map(to_rho, asarray(magnitudes)))

    return Grid(
        dims=('rho', 'v', 'w', 'kappa', 'sigma', 'h'),
        coords=(rho, v, w, kappa, sigma, h),
        callback=to_mij)


def ForceGridRegular(magnitude_in_N=1., npts_per_axis=80):
    """ Force grid with regularly-spaced values
    """
    theta = regular(0., 360., npts)
    h = regular(-1., 1., npts)
    F0 = asarray(mangitude_in_N)

    theta = np.tile(theta, len(magnitudes))
    h = np.tile(h, len(magnitudes))
    F0 = np.repeat(F0, npts)

    return Grid(
        dims=('F0', 'theta', 'h'),
        coords=(F0, theta, h),
        callback=to_rtp)

def ForceGridRandom(magnitude_in_N=1., npts=10000):
    """ Force grid with randomly-spaced values
    """
    theta = np.random(0., 360., npts)
    h = np.random(-1., 1., npts)
    F0 = asarray(mangitude_in_N)

    theta = np.tile(theta, len(magnitudes))
    h = np.tile(h, len(magnitudes))
    F0 = np.repeat(F0, npts)

    return UnstructuredGrid(
        dims=('F0', 'theta', 'h'),
        coords=(F0, theta, h),
        callback=to_rtp)

