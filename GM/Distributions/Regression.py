import numpy as np
from Base import Exponential
from Normal import Normal
from MatrixNormalInverseWishart import MatrixNormalInverseWishart


class Regression( Exponential ):

    priorClass = MatrixNormalInverseWishart

    def __init__( self, A=None, sigma=None, prior=None, hypers=None ):
        super( Regression, self ).__init__( A, sigma, prior=prior, hypers=hypers )

    ##########################################################################

    @classmethod
    def standardToNat( cls, A, sigma ):

        sigInv = np.linalg.inv( sigma )

        n1 = -0.5 * sigInv
        n2 = -0.5 * A.T @ sigInv @ A
        n3 = A.T @ sigInv

        return n1, n2, n3

    @classmethod
    def natToStandard( cls, n1, n2, n3 ):
        sigma = -0.5 * np.linalg.inv( n1 )
        A = sigma @ n3.T
        return A, sigma

    ##########################################################################

    @classmethod
    def sufficientStats( cls, x, forPost=False ):
        # Compute T( x )

        x, y = x

        if( x.ndim == 1 ):
            x = x.reshape( ( 1, -1 ) )
        if( y.ndim == 1 ):
            y = y.reshape( ( 1, -1 ) )

        t1 = y.T.dot( y )
        t2 = x.T.dot( x )
        t3 = x.T.dot( y )

        if( forPost ):
            # This for when we add to the MNIW natural params
            t4 = x.shape[ 0 ]
            t5 = x.shape[ 0 ]
            return t1, t2, t3, t4, t5
        return t1, t2, t3

    @classmethod
    def log_partition( cls, x=None, params=None, natParams=None, split=False ):
        # Compute A( Ѳ ) - log( h( x ) )
        assert ( params is None ) ^ ( natParams is None )

        A, sigma = params if params is not None else cls.natToStandard( *natParams )

        p = sigma.shape[ 0 ]

        A1 = 0.5 * np.linalg.slogdet( sigma )[ 1 ]
        A2 = p / 2 * np.log( 2 * np.pi )

        if( split ):
            return A1, A2
        return A1 + A2

    ##########################################################################

    @classmethod
    def sample( cls, x=None, params=None, natParams=None, size=1 ):
        # Sample from P( x | Ѳ; α )
        assert ( params is None ) ^ ( natParams is None )
        A, sigma = params if params is not None else cls.natToStandard( *natParams )
        D = A.shape[ 1 ]
        if( x is None ):
            x = Normal.sample( params=( np.zeros( D ), np.eye( D ) ), size=1 )
            y = Normal.sample( params=( A.dot( x ), sigma ), size=size )
            return ( x, y )
        return Normal.sample( params=( A.dot( x ), sigma ), size=size )

    ##########################################################################

    @classmethod
    def log_likelihood( cls, x, params=None, natParams=None ):
        # Compute P( x | Ѳ; α )
        assert ( params is None ) ^ ( natParams is None )
        A, sigma = params if params is not None else cls.natToStandard( *natParams )

        x, y = x
        assert x.ndim == 1 and y.ndim == 1
        return Normal.log_likelihood( y, ( A.dot( x ), sigma ) )