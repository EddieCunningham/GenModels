from GenModels.GM.States.GraphicalMessagePassing import DataGraph, GroupGraph, GraphHMMFBS, GraphHMMFBSGroup
import numpy as np
from functools import reduce
from scipy.sparse import coo_matrix
from collections import Iterable
from GenModels.GM.Utility import fbsData
import copy

__all__ = [ 'Pedigree',
            'PedigreeSexMatters',
            'PedigreeHMMFilter',
            'PedigreeHMMFilterSexMatters',
            'setGraphRootStates' ]

######################################################################

class _pedigreeMixin():

    def __init__( self ):
        super().__init__()
        self.attrs = {}
        self.studyID = None
        self.pedigree_obj = None

    def useDiagnosisImplication( self, ip_type ):
        addLatentStateFromDiagnosis( self, ip_type )

    def useSingleCarrierRoot( self, ip_type ):
        setGraphRootStates( self, ip_type )

    def toNetworkX( self ):
        graph = super().toNetworkX()

        for node, attr in self.attrs.items():
            graph.nodes[ node ][ 'sex' ] = attr[ 'sex' ]
            graph.nodes[ node ][ 'affected' ] = attr[ 'affected' ]

        return graph

    def setNodeAttrs( self, nodes, attrs ):
        if( isinstance( nodes, int ) ):
            if( nodes not in self.attrs ):
                self.attrs[ nodes ] = {}
            self.attrs[ nodes ].update( attrs )
        else:
            for node, attr in zip( nodes, attrs ):
                if( node not in self.attrs ):
                    self.attrs[ node ] = {}
                self.attrs[ node ].update( attr )

    def draw( self, render=True, **kwargs ):

        male_style = dict( shape='square' )
        female_style = dict( shape='circle' )
        unknown_style = dict( shape='diamond' )
        affected_male_style = dict( shape='square', fontcolor='black', style='bold', color='blue' )
        affected_female_style = dict( shape='circle', fontcolor='black', style='bold', color='blue' )
        affected_unknown_style = dict( shape='diamond', fontcolor='black', style='bold', color='blue' )
        styles = { 0: male_style, 1: female_style, 2: unknown_style, 3: affected_male_style, 4: affected_female_style, 5: affected_unknown_style }

        unaffected_males = []
        unaffected_females = []
        unaffected_unknowns = []
        affected_males = []
        affected_females = []
        affected_unknowns = []

        for n in self.nodes:
            attrs = self.attrs[ n ]
            if( attrs[ 'sex' ] == 'male' ):
                if( attrs[ 'affected' ] == True ):
                    affected_males.append( n )
                else:
                    unaffected_males.append( n )
            elif( attrs[ 'sex' ] == 'female' ):
                if( attrs[ 'affected' ] == True ):
                    affected_females.append( n )
                else:
                    unaffected_females.append( n )
            else:
                if( attrs[ 'affected' ] == True ):
                    affected_unknowns.append( n )
                else:
                    unaffected_unknowns.append( n )

        node_to_style_key =       dict( [ ( n, 0 ) for n in unaffected_males ] )
        node_to_style_key.update( dict( [ ( n, 1 ) for n in unaffected_females ] ) )
        node_to_style_key.update( dict( [ ( n, 2 ) for n in unaffected_unknowns ] ) )
        node_to_style_key.update( dict( [ ( n, 3 ) for n in affected_males ] ) )
        node_to_style_key.update( dict( [ ( n, 4 ) for n in affected_females ] ) )
        node_to_style_key.update( dict( [ ( n, 5 ) for n in affected_unknowns ] ) )

        kwargs.update( dict( styles=styles, node_to_style_key=node_to_style_key) )

        return super().draw( render=render, **kwargs )

class Pedigree( _pedigreeMixin, DataGraph ):

    @staticmethod
    def fromPedigreeSexMatters( pedigree, deep_copy=True ):
        deepcopy = copy.deepcopy if deep_copy else lambda x: x
        new_pedigree = PedigreeSexMatters()
        new_pedigree.pedigree_obj = pedigree.pedigree_obj
        new_pedigree.nodes = deepcopy( pedigree.nodes )
        new_pedigree.edge_children = deepcopy( pedigree.edge_children )
        new_pedigree.edge_parents = deepcopy( pedigree.edge_parents )
        new_pedigree.data = deepcopy( pedigree.data )
        new_pedigree.possible_latent_states = deepcopy( pedigree.possible_latent_states )
        new_pedigree.attrs = deepcopy( pedigree.attrs )
        return new_pedigree

class PedigreeSexMatters( _pedigreeMixin, GroupGraph ):

    @staticmethod
    def fromPedigree( pedigree, deep_copy=True ):
        deepcopy = copy.deepcopy if deep_copy else lambda x: x
        new_pedigree = PedigreeSexMatters()
        new_pedigree.pedigree_obj = pedigree.pedigree_obj
        new_pedigree.nodes = deepcopy( pedigree.nodes )
        new_pedigree.edge_children = deepcopy( pedigree.edge_children )
        new_pedigree.edge_parents = deepcopy( pedigree.edge_parents )
        new_pedigree.data = deepcopy( pedigree.data )
        new_pedigree.possible_latent_states = deepcopy( pedigree.possible_latent_states )
        new_pedigree.attrs = deepcopy( pedigree.attrs )
        sex_to_index = lambda x: [ 'female', 'male', 'unknown' ].index( x )
        for node, attr in pedigree.attrs.items():
            new_pedigree.setGroups( node, sex_to_index( attr[ 'sex' ] ) )

        return new_pedigree

    def setNodeAttrs( self, nodes, attrs ):
        super().setNodeAttrs( nodes, attrs )

        sex_to_index = lambda x: [ 'female', 'male', 'unknown' ].index( x )
        self.setGroups( nodes, sex_to_index( attrs[ 'sex' ] ) )

######################################################################

class _pedigreeFilterMixin():

    def preprocessData( self, data_graphs ):
        if( isinstance( self, GraphHMMFBSGroup ) ):
            updated_graphs = []
            for graph, fbs in data_graphs:
                if( not isinstance( graph, PedigreeSexMatters ) ):
                    updated_graphs.append( ( PedigreeSexMatters.fromPedigree( graph ), fbs ) )
                else:
                    updated_graphs.append( ( graph, fbs ) )
            data_graphs = updated_graphs

        super().preprocessData( data_graphs )
        self.node_attrs = []
        total_nodes = 0
        for graph, fbs in data_graphs:
            for node in graph.nodes:
                self.node_attrs.append( graph.attrs[ node ] )
            total_nodes += len( graph.nodes )

    def draw( self, render=True, **kwargs ):

        male_style = dict( shape='square' )
        female_style = dict( shape='circle' )
        unknown_style = dict( shape='diamond' )
        affected_male_style = dict( shape='square', fontcolor='black', style='bold', color='blue' )
        affected_female_style = dict( shape='circle', fontcolor='black', style='bold', color='blue' )
        affected_unknown_style = dict( shape='diamond', fontcolor='black', style='bold', color='blue' )
        styles = { 0: male_style, 1: female_style, 2: unknown_style, 3: affected_male_style, 4: affected_female_style, 5: affected_unknown_style }

        unaffected_males = []
        unaffected_females = []
        unaffected_unknowns = []
        affected_males = []
        affected_females = []
        affected_unknowns = []

        for n in self.nodes:
            attrs = self.node_attrs[ n ]
            if( attrs[ 'sex' ] == 'male' ):
                if( attrs[ 'affected' ] == True ):
                    affected_males.append( n )
                else:
                    unaffected_males.append( n )
            elif( attrs[ 'sex' ] == 'female' ):
                if( attrs[ 'affected' ] == True ):
                    affected_females.append( n )
                else:
                    unaffected_females.append( n )
            else:
                if( attrs[ 'affected' ] == True ):
                    affected_unknowns.append( n )
                else:
                    unaffected_unknowns.append( n )

        node_to_style_key =       dict( [ ( n, 0 ) for n in unaffected_males ] )
        node_to_style_key.update( dict( [ ( n, 1 ) for n in unaffected_females ] ) )
        node_to_style_key.update( dict( [ ( n, 2 ) for n in unaffected_unknowns ] ) )
        node_to_style_key.update( dict( [ ( n, 3 ) for n in affected_males ] ) )
        node_to_style_key.update( dict( [ ( n, 4 ) for n in affected_females ] ) )
        node_to_style_key.update( dict( [ ( n, 5 ) for n in affected_unknowns ] ) )

        kwargs.update( dict( styles=styles, node_to_style_key=node_to_style_key) )

        return self.toGraph().draw( render=render, **kwargs )

######################################################################

class PedigreeHMMFilter( _pedigreeFilterMixin, GraphHMMFBS ):
    pass

class PedigreeHMMFilterSexMatters( _pedigreeFilterMixin, GraphHMMFBSGroup ):
    pass

######################################################################

def addLatentStateFromDiagnosis( graph, ip_type ):

    if( ip_type == 'AD' ):
        for node in graph.nodes:
            if( graph.data[ node ] == 1 ):
                # Affected
                graph.setPossibleLatentStates( node, [ 0, 1 ] )
    elif( ip_type == 'AR' ):
        for node in graph.nodes:
            if( graph.data[ node ] == 1 ):
                # Affected
                graph.setPossibleLatentStates( node, [ 0 ] )
    elif( ip_type == 'XL' ):
        for node in graph.nodes:
            if( graph.groups[ node ] == 0 ):
                # Female
                if( graph.data[ node ] == 1 ):
                    graph.setPossibleLatentStates( node, [ 0 ] )
            elif( graph.groups[ node ] == 1 ):
                # Male
                if( graph.data[ node ] == 1 ):
                    graph.setPossibleLatentStates( node, [ 0 ] )
            else:
                # Unknown sex
                if( graph.data[ node ] == 1 ):
                    graph.setPossibleLatentStates( node, [ 0, 3 ] )

######################################################################

# Algorithm that sets a single root to be a carrier or affected
# and the other roots to not a carrier.
# Chooses the root with the most diagnosed ancestors.

def selectAffectedRoot( graph ):
    n_affected_below = {}
    n_unaffected_below = {}
    for node in graph.backwardPass():
        n_affected_below[ node ] = 0
        n_unaffected_below[ node ] = 0
        if( graph.data[ node ] == 1 ):
            n_affected_below[ node ] += 1
        else:
            n_unaffected_below[ node ] += 1
        for children in graph.getChildren( node ):
            for child in children:
                if( child in n_affected_below ):
                    n_affected_below[ node ] += n_affected_below[ child ]
                    n_unaffected_below[ node ] += n_unaffected_below[ child ]

    n_affected_below_roots = dict( [ ( root, n_affected_below[ root ] ) for root in graph.roots ] )
    n_unaffected_below_roots = dict( [ ( root, n_unaffected_below[ root ] ) for root in graph.roots ] )

    max_val = np.max( np.array( list( n_affected_below_roots.values() ) ) )
    selections = [ root for root, val in n_affected_below_roots.items() if val == max_val ]

    if( len( selections ) > 1 ):
        # Use n_unaffected_below_roots as a tie breaker
        n_unaffected_below_roots = dict( [ ( root, val ) for root, val in n_unaffected_below_roots.items() if root in selections ] )
        min_val = np.min( np.array( list( n_unaffected_below_roots.values() ) ) )
        selections = [ root for root, val in n_unaffected_below_roots.items() if val == min_val and root in selections ]

        # If there are still multiple possibilities, just pick the first one
    return selections[ 0 ]

def sexToCarrierState( graph, node ):
    if( graph.groups[ node ] == 0 ):
        return [ 0, 1 ]
    elif( graph.groups[ node ] == 1 ):
        return [ 0 ]
    elif( graph.groups[ node ] == 2 ):
        return [ 0, 1, 3 ]

def sexToNotCarrierState( graph, node ):
    if( graph.groups[ node ] == 0 ):
        return [ 2 ]
    elif( graph.groups[ node ] == 1 ):
        return [ 1 ]
    elif( graph.groups[ node ] == 2 ):
        return [ 2, 4 ]

def setGraphRootStates( graph, ip_type ):

    if( ip_type == 'AD' ):
        graph = graph if isinstance( graph, Pedigree ) else Pedigree.fromPedigreeSexMatters( graph )
        affected_root = selectAffectedRoot( graph )
        graph.setPossibleLatentStates( affected_root, [ 0, 1 ] )
        for root in filter( lambda x: x!=affected_root, graph.roots ):
            graph.setPossibleLatentStates( root, [ 2 ] )
    elif( ip_type == 'AR' ):
        graph = graph if isinstance( graph, Pedigree ) else Pedigree.fromPedigreeSexMatters( graph )
        affected_root = selectAffectedRoot( graph )
        graph.setPossibleLatentStates( affected_root, [ 0, 1 ] )
        for root in filter( lambda x: x!=affected_root, graph.roots ):
            graph.setPossibleLatentStates( root, [ 2 ] )
    elif( ip_type == 'XL' ):
        graph = graph if isinstance( graph, PedigreeSexMatters ) else PedigreeSexMatters.fromPedigree( graph )
        affected_root = selectAffectedRoot( graph )
        graph.setPossibleLatentStates( affected_root, sexToCarrierState( graph, affected_root ) )
        for root in filter( lambda x: x!=affected_root, graph.roots ):
            graph.setPossibleLatentStates( root, sexToNotCarrierState( graph, root ) )

    return graph