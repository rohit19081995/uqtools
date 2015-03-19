# return sub-modules when module is reloaded
#import logging
#import types
#for k, v in locals().items():
#    if isinstance(v, types.ModuleType) and v.__name__.startswith(__name__):
#        reload(v)
#        logging.debug(__name__ + ': reloading {0}'.format(v.__name__))
#del logging, types, k, v

# reload sub-modules in fixed order
import logging
import sys
for key in ('config', 'helpers', 'parameter', 'context', 'data', 'progress', 
            'measurement', 'basics', 'buffer', 'process', 'fpga', 'fsv',
            'simulation', 'calibrate', 'pulselib', 'awg', 'plot'):
    #if key in locals():
    key = 'uqtools.'+key
    if key in sys.modules:
        logging.debug(__name__ + ': forcing reload of {0}'.format(key))
        del(sys.modules[key])
        #reload(locals()[key])
del key


from . import config
from . import helpers

from . import parameter
from .parameter import (Parameter, OffsetParameter, ScaledParameter, LinkedParameter,
                        TypedList, ParameterList, ParameterDict)

from . import context
from .context import NullContextManager, SimpleContextManager
from .context import SetInstrument, RevertInstrument, SetParameter, RevertParameter

from . import data

from . import progress
from .progress import ContinueIteration, BreakIteration, Flow

from . import measurement
from .measurement import Measurement

from . import basics
from .basics import Delay, ParameterMeasurement 
from .basics import MeasurementArray, Sweep, MultiSweep

from . import buffer
from .buffer import Buffer

from . import process
from .process import apply_decorator, Apply, Add, Multiply, Divide
from .process import Reshape, Integrate, Accumulate

from . import fpga
from .fpga import CorrelatorMeasurement, TvModeMeasurement, HistogramMeasurement
from .fpga import FPGAStart, FPGAStop
from .fpga import AveragedTvModeMeasurement

from . import fsv 
from .fsv import FSVTrace, FSVMeasurement as FSVWait

from . import simulation
from .simulation import Constant, Function, DatReader

from . import calibrate
from .calibrate import FittingMeasurement, CalibrateResonator, Minimize, MinimizeIterative
from .calibrate import Interpolate

from . import plot
from .plot import Plot, FigureWidget

try:
    import pulselib
except ImportError:
    # pulselib already generates a log entry
    pass

try:
    from . import awg
    from .awg import ProgramAWG, ProgramAWGParametric
    from .awg import ProgramAWGSweep, MeasureAWGSweep, MultiAWGSweep, NormalizeAWG
except ImportError:
    # awg already generates a log entry
    pass