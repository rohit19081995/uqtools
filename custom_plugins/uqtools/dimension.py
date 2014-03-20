import numpy

class Parameter(object):
    '''
        a parameter of a data object
        
        by making parameter objects it becomes possible to store them inside nested measurement
        functions/objects. when a nested measurement is run, it can retrieve the current point
        on the coordinate axes by accessing its stored parameter objects.
        
        additional properties like the parameter name can be automatically added to new data files
        created by nested measurements. 
    '''
    def __init__(self, name, set_func=None, get_func=None, value=None, dtype=None, inheritable=True, **info):
        '''
            initialize parameter.
            
            Input:
                name - frieldy name of the parameter
                set_func - function called when set(value) is called
                get_func - function called when get() is called, returns stored value if not given
                value - stored value. not necessarily scalar.
                dtype - data type
                inheritable - (deprecataed) if False, Parameter is not passed to nested measurements if used as a coordinate
                **info - extra keyword arguments are descriptive information and may be stored in data files
        '''
        self.name = name
        self.set_func = set_func
        self.get_func = get_func
        if(value is not None):
            self.set(value)
        else:
            self._value = None
        self.dtype = dtype
        self.info = info
        self.inheritable = inheritable
    
    def set(self, value):
        ''' store value and call set_func if defined '''
        if(self.set_func):
            self.set_func(value)
        self._value = value
    
    def get(self):
        ''' return result of get_func or stored value if no get_func was defined '''
        if(self.get_func):
            return self.get_func()
        return self._value
    
    def iscomplex(self):
        ''' check if self.dtype is a complex type '''
        return callable(self.dtype) and numpy.iscomplexobj(self.dtype())
        
    def __repr__(self):
        r = super(Parameter, self).__repr__()
        # <object Parameter "name" at 0x...>
        r_parts = r.split(' ')
        r_parts.insert(2, '"{0}"'.format(self.name))
        return ' '.join(r_parts)