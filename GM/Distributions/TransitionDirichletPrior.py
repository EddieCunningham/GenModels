import numpy as np
from GenModels.GM.Distributions.Base import ExponentialFam
from scipy.special import gammaln
from GenModels.GM.Distributions import Dirichlet, Transition

__all__ = [ 'TransitionDirichletPrior' ]

class TransitionDirichletPrior( ExponentialFam ):

    def __init__( self, alpha=None, prior=None, hypers=None ):
        super( TransitionDirichletPrior, self ).__init__( alpha, prior=prior, hypers=hypers )

    ##########################################################################

    @property
    def alpha( self ):
        return self._params[ 0 ]

    ##########################################################################

    @classmethod
    def dataN( cls, x ):
        if( isinstance( x, tuple ) ):
            assert len( x ) == 1
            x = x[ 0 ]
        cls.checkShape( x )
        if( x.ndim == 3 ):
            return x.shape[ 0 ]
        return 1

    @classmethod
    def unpackSingleSample( cls, x ):
        return x[ 0 ]

    @classmethod
    def sampleShapes( cls ):
        # ( Sample #, dim1, dim2 )
        return ( None, None, None )

    def isampleShapes( cls ):
        return ( None, self.D_in, self.D_out )

    @classmethod
    def checkShape( cls, x ):
        if( isinstance( x, tuple ) ):
            assert len( x ) == 1
            x = x[ 0 ]
        assert isinstance( x, np.ndarray )
        assert x.ndim == 3 or x.ndim == 2

    ##########################################################################

    @classmethod
    def standardToNat( cls, alpha ):
        return ( alpha - 1, )

    @classmethod
    def natToStandard( cls, n ):
        return ( n + 1, )

    ##########################################################################

    @property
    def constParams( self ):
        return None

    ##########################################################################

    @classmethod
    def sufficientStats( cls, x, constParams=None ):
        # Compute T( x )
        if( cls.dataN( x ) > 1 ):
            t = ( 0, 0 )
            for _x in x:
                t = np.add( t, cls.sufficientStats( _x ) )
            return t

        t1, = Transition.standardToNat( x )
        t2, = Transition.log_partition( params=( x, ), split=True )
        return t1, -t2

    @classmethod
    def log_partition( cls, x=None, params=None, natParams=None, split=False ):
        # Compute A( Ѳ ) - log( h( x ) )
        assert ( params is None ) ^ ( natParams is None )
        ( alpha, ) = params if params is not None else cls.natToStandard( *natParams )
        return sum( [ Dirichlet.log_partition( params=( a, ) ) for a in alpha ] )

    @classmethod
    def log_partitionGradient( cls, params=None, natParams=None ):
        # Derivative w.r.t. natural params
        assert ( params is None ) ^ ( natParams is None )
        n, = natParams if natParams is not None else cls.standardToNat( *params )

        d = np.vstack( [ Dirichlet.log_partitionGradient( natParams=( _n, ) ) for _n in n ] )
        return d

    def _testLogPartitionGradient( self ):

        import autograd.numpy as anp
        import autograd.scipy as asp
        from autograd import jacobian

        n, = self.natParams
        def part( _n ):
            ans = 0.0
            for __n in _n:
                ans = ans + anp.sum( asp.special.gammaln( ( __n + 1 ) ) ) - asp.special.gammaln( anp.sum( __n + 1 ) )
            return ans

        d = self.log_partitionGradient( natParams=self.natParams )
        _d = jacobian( part )( n )

        assert np.allclose( d, _d )

    ##########################################################################

    @classmethod
    def generate( cls, D_in=3, D_out=2, size=1 ):
        params = ( np.ones( ( D_in, D_out ) ), )
        samples = cls.sample( params=params, size=size )
        return samples if size > 1 else cls.unpackSingleSample( samples )

    @classmethod
    def sample( cls, params=None, natParams=None, size=1 ):
        # Sample from P( x | Ѳ; α )
        assert ( params is None ) ^ ( natParams is None )

        # if( params is not None ):
        #     if( not isinstance( params, tuple ) or \
        #         not isinstance( params, list ) ):
        #         params = ( params, )

        ( alpha, ) = params if params is not None else cls.natToStandard( *natParams )

        # Quick fix for the moment
        # if( isinstance( alpha, tuple ) ):
        #     assert len( alpha ) == 1
        #     alpha, = alpha

        ans = np.swapaxes( np.array( [ Dirichlet.sample( params=( a, ), size=size ) for a in alpha ] ), 0, 1 )
        cls.checkShape( ans )
        return ans

    ##########################################################################

    @classmethod
    def log_likelihood( cls, x, params=None, natParams=None ):
        # Compute P( x | Ѳ; α )
        assert ( params is None ) ^ ( natParams is None )
        ( alpha, ) = params if params is not None else cls.natToStandard( *natParams )
        if( isinstance( x, tuple ) ):
            assert len( x ) == 1
            x, = x
        assert isinstance( x, np.ndarray )
        if( x.ndim == 3 ):
            return sum( [ TransitionDirichletPrior.log_likelihood( _x, params=( alpha, ) ) for _x in x ] )

        assert isinstance( x, np.ndarray ) and x.ndim == 2, x
        return sum( [ Dirichlet.log_likelihood( _x, params=( a, ) ) for _x, a in zip( x, alpha ) ] )
