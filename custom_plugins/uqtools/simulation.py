import numpy
import re
import logging
import csv
import copy

from parameter import Parameter
from basics import coordinate_concat
from measurement import Measurement, ResultDict

class Constant(Measurement):
    '''
    Convert ndarray into a Measurement.
    '''
    def __init__(self, data, coordinates=None, value=None, **kwargs):
        '''
        Input:
            data (ndarray) - value returned by Constant.
                a coordinate is generated for each dimension of arr.
            coordinates (list of Parameter) - coordinate corresponding
                to each dimension
            value (Parameter) - value dimension
        '''
        super(Constant, self).__init__(**kwargs)
        self.data = numpy.array(data)
        # generate coordinate and value dimensions
        if coordinates is None:
            coordinates = [Parameter(name='dim{0}'.format(i)) for i in range(data.ndim)]
        if len(coordinates) != self.data.ndim:
            raise ValueError('number of dimensions of data must be equal '+
                             'to the number of coordinates passed')
        self.add_coordinates(coordinates)
        self.add_values(value if value is not None else Parameter('val'))
        # determine range of each coordinate
        self.ranges = []
        for i, n in enumerate(self.data.shape):
            cv = coordinates[i].get()
            if (cv is None) or (numpy.isscalar(cv) and (n!=1)):
                self.ranges.append(range(n))
            else:
                if len(cv) != n:
                    raise ValueError('length of each coordinate vector must equal '+
                                     'the length of corresponding dimension of data')
                self.ranges.append(cv)
        
    def _measure(self, **kwargs):
        cs = [ResultDict([(c, self.ranges[i])]) 
              for i, c in enumerate(self.get_coordinates())]
        return (
            coordinate_concat(*cs),
            ResultDict(zip(self.get_values(), (self.data,)))
        )

    def _create_data_files(self):
        ''' Constant never creates data files '''
        pass
    
class Function(Measurement):
    '''
    Generate measurement data by calling a function
    '''
    def __init__(self, f, coordinates=[], **kwargs):
        '''
        Input:
            f (callable) - f(*cs.values()) is called with the matrices for all 
                coordinates as arguments and must return a single ndarray of 
                the same shape as the coordinate matrices
            coordinates (Parameter) - iterable of Parameter objects that have 
                the points for each coordinate set as their value
        '''
        super(Function, self).__init__(**kwargs)
        self.f = f
        self.add_coordinates(coordinates)
        self.add_values(Parameter('val'))
    
    def _measure(self, **kwargs):
        cs = coordinate_concat(*[ResultDict([(c, c.get())]) for c in self.get_coordinates()])
        d = self.f(*cs.values())
        return cs, ResultDict(zip(self.get_values(), (d,)))

    def _create_data_files(self):
        ''' Function never creates data files '''
        pass


class DatReader(Measurement):
    '''
    Simple .dat file reader.
    Returns the entire contents of a file in one go.
    '''
    def __init__(self, filepath, **kwargs):
        '''
        Create a .dat file reader instance.
        
        Input:
            filepath - path to the file to read
        '''
        super(DatReader, self).__init__(**kwargs)
        # load and reshape data file
        self._cs, self._d = self._load(filepath)
        # add coordinates and values from data file to self
        for p in self._cs.keys():
            self.add_coordinates(p)
        for p in self._d.keys():
            self.add_values(p)
        
    
    def _load(self, filepath):
        '''
        Read .dat file.
        
        Input:
            filepath - path to the file to read
        '''
        # support file:// urls
        if filepath.startswith('file:///'):
            filepath = filepath[8:]
        # parse comments
        comments = []
        column = None
        columns = []
        with open(filepath, 'r') as f:
            for line in f:
                # filter everything that is not a comment, stop parsing when data starts
                if line.startswith('\n'):
                    continue
                if not line.startswith('#'):
                    break
                # remove # and newline from comments
                line = line[1:-1]
                # parse columns
                m = re.match(' Column ([0-9]+):', line)
                if m:
                    # start of a new column
                    column = {}
                    columns.append(column)
                    if len(columns) != int(m.group(1)):
                        logging.warning(__name__+': got column #{0}, expected #{1}'.
                            format(int(m.group(1)), len(columns))
                        )
                elif column is not None:
                    # currently in column
                    m = re.match('\t([^:]+): (.*)', line)
                    if m:
                        # add parameter to column
                        column[m.group(1)] = m.group(2)
                    else:
                        # end column
                        column = None
                else:
                    # regular comment
                    comments.append(line)
            
        # read data
        #data = numpy.loadtxt(filepath, unpack=True, ndmin=2)
        #with open(filepath, 'r') as f:
            #reader = csv.reader(f, dialect='excel-tab')
            #data = numpy.array([l for l in reader if len(l) and (l[0][0] != '#')], dtype=numpy.float64).transpose()
        with open(filepath, 'r') as f:
            data = numpy.loadtxt(f, unpack=False)
        if not data.shape[0]:
            # file is empty
            logging.warning(__name__+': no data found in file "{0}".'.format(filepath))
        if data.shape[1] != len(columns):
            logging.warning(__name__+': number of columns does not match the '+
                'definition in the file header of file #{0}.'.format(filepath))
        # reassemble complex columns
        data_cols = []
        for col_idx, column in enumerate(columns):
            if ((col_idx < len(columns)) and 
                column['name'].startswith('real(') and 
                column['name'].endswith(')') and
                columns[col_idx+1]['name'].startswith('imag(') and 
                columns[col_idx+1]['name'].endswith(')') and
                (column['name'][5:-1] == columns[col_idx+1]['name'][5:-1])
            ):
                columns.pop(col_idx+1)
                column['name'] = column['name'][5:-1]
                data_cols.append(data[:, col_idx]+1j*data[:, col_idx+1])
            else:
                data_cols.append(data[:, col_idx])
        # separate coordinate from value dimensions
        coord_dims = [(i, c) for i, c in enumerate(columns) if c['type']=='coordinate']
        value_dims = [(i, c) for i, c in enumerate(columns) if c['type']=='value']
        coords = ResultDict(zip([Parameter(**c) for _, c in coord_dims], [data_cols[i] for i, _ in coord_dims]))
        values = ResultDict(zip([Parameter(**c) for _, c in value_dims], [data_cols[i] for i, _ in value_dims]))
        # reshape data
        shape, order = self._detect_dimensions_size(coords)
        if (shape is not None) and (order is not None):
            nrows = numpy.prod(shape)
            for rd in (coords, values):
                for k in rd.keys():
                    rd[k] = numpy.reshape(rd[k][:nrows], shape, order='C').transpose(order)
        return coords, values


    def _detect_dimensions_size(self, coords):
        '''
        Detect shape of data and return results
        (this is the same logic that is also implemented by data.Data) 
        '''
        # no data...
        if not len(coords):
            return None, None
    
        # find change period of all coordinates
        # assumes that coordinate dimensions will appear before value dimensions
        periods = [numpy.sum(numpy.cumprod(coord==coord[0])) for coord in coords.values()]
        # using stable sort so the correct coordinate is discarded in case of dependent coordinates, see below
        loopdims = numpy.argsort(periods, kind='mergesort')[::-1]
        # determine axis indices that will undo sorting of the axes by period length
        undodims = list(numpy.argsort(loopdims))
        # sort periods in descending order
        periods = numpy.sort(periods, kind='mergesort')[::-1]
    
        # assume two coordinate columns with the same period are dependent.
        # export only the last one found in the file 
        for idx in range(1, len(periods)):
            if periods[idx] == periods[idx-1]:
                logging.info('coordinates with equal change periods found in file.')
                periods[idx] = 1
        # calculate and block sizes for reshape
        nrows = len(coords.values()[0])
        sizes = []
        for period in periods:
            # divide file into blocks, blocks into subblocks and so on
            size = 1.*nrows/numpy.prod(sizes)/period
            # check if shape is ok
            if(int(size) != size):
                if (numpy.prod(sizes)==1):
                    logging.warning('last block of the data file is incomplete. discarding.')
                    nrows -= nrows % period
                else:
                    # additional checks are needed to make sure the data is rectangular. 
                    # this just covers the cases where reshape would fail
                    logging.error('data is not of a rectangular shape')
                    return None, None
            sizes.append(int(size))
        
        # store metadata
        return sizes, undodims

        
    def _reshape(self, coords, values):
        '''
        More powerful reshape data.
        
        TODO: not implemented
        '''
        # nothing to do
        if len(coords) in (0, 1):
            return coords, values
        for c_name, c in coords.iteritems():
            c_vals, c_blocks = numpy.unique(c, unique_inverse=True)
            # check if the points are on a regular grid 
            c_blocklens, c_blocklenidxs = numpy.unique((len(c_block) for c_block in c_blocks), unique_indices=True)
            if len(c_blocklens) == 1:
                # all blocks have the same length
                pass
            elif len(c_blocklens) == 2:
                # most likely the measurement was aborted
                #c_blocklenidxs[numpy.argmin(c_blocklen)]
                pass

    def set_parent_coordinates(self, dimensions = []):
        if len(dimensions):
            logging.warning(__name__+': DatReader does not honour inherited coordinates.')
            
    def _create_data_files(self):
        ''' DatReader never creates data files '''
        pass
    
    def __call__(self, **kwargs):
        ''' return data loaded from file '''
        return copy.copy(self._cs), copy.copy(self._d)            
    
