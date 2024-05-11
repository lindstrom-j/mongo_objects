# test_PolymorphicMongoSingleProxy
#
# Since MongoSingleProxy has been thoroughly exercised elsewhere,
# only test functionality unique to PolymorphicMongoSingleProxy

from bson import ObjectId
import copy
from datetime import datetime
import mongo_objects
from pymongo.collection import Collection
import pytest
import secrets



@pytest.fixture( scope='class' )
def getMPMUDClasses( mongo_db ):
    """Return a set of polymorphic MongoUserDict classes configured for a per-test-class unique collection"""

    class MyMongoUserDict( mongo_objects.MongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db

    class MyMongoSingleProxyA( mongo_objects.PolymorphicMongoSingleProxy ):
        proxy_subclass_map = {}
        container_name = "proxyA"

    class MyMongoSingleProxyAa( MyMongoSingleProxyA ):
        proxy_subclass_key = 'Aa'

    class MyMongoSingleProxyAb( MyMongoSingleProxyA ):
        proxy_subclass_key = 'Ab'

    class MyMongoSingleProxyAc( MyMongoSingleProxyA ):
        proxy_subclass_key = 'Ac'

    class MyMongoSingleProxyA1( mongo_objects.PolymorphicMongoSingleProxy ):
        proxy_subclass_map = {}
        container_name = "proxyA1"

    class MyMongoSingleProxyA1a( MyMongoSingleProxyA1 ):
        proxy_subclass_key = 'A1a'

    class MyMongoSingleProxyA1b( MyMongoSingleProxyA1 ):
        proxy_subclass_key = 'A1b'

    class MyMongoSingleProxyA1c( MyMongoSingleProxyA1 ):
        proxy_subclass_key = 'A1c'

    class MyMongoSingleProxyB( mongo_objects.PolymorphicMongoSingleProxy ):
        proxy_subclass_map = {}
        container_name = "proxyB"

    class MyMongoSingleProxyBa( MyMongoSingleProxyB ):
        proxy_subclass_key = 'Ba'

    class MyMongoSingleProxyBb( MyMongoSingleProxyB ):
        proxy_subclass_key = 'Bb'

    class MyMongoSingleProxyBc( MyMongoSingleProxyB ):
        proxy_subclass_key = 'Bc'


    return {
        'parent' : MyMongoUserDict,
        'A' : MyMongoSingleProxyA,
        'Aa' : MyMongoSingleProxyAa,
        'Ab' : MyMongoSingleProxyAb,
        'Ac' : MyMongoSingleProxyAc,
        'A1' : MyMongoSingleProxyA1,
        'A1a' : MyMongoSingleProxyA1a,
        'A1b' : MyMongoSingleProxyA1b,
        'A1c' : MyMongoSingleProxyA1c,
        'B' : MyMongoSingleProxyB,
        'Ba' : MyMongoSingleProxyBa,
        'Bb' : MyMongoSingleProxyBb,
        'Bc' : MyMongoSingleProxyBc,
    }



@pytest.fixture( scope='class' )
def getPopulatedMPMUDClasses( getMPMUDClasses ):
    '''Make four objects, one with the base classes and one for
    each of the *a, *b and *c subclasses.'''

    classes = getMPMUDClasses

    # one document with just base classes
    for (seq, A, A1, B) in [
        (0, 'A',  'A1',  'B'  ),
        (1, 'Aa', 'A1a', 'Ba' ),
        (2, 'Ab', 'A1b', 'Bb' ),
        (3, 'Ac', 'A1c', 'Bc' ),
    ]:
        parent = classes['parent']( {
            'name' : f"Parent Document {seq}",
            'amount' : 10,
            }
        )
        proxyA = classes[A].create(
            parent,
            {
                'nameA' : f"Proxy A-{seq}",
                'amountA' : 100 + seq,
            },
        )
        proxyA1 = classes[A1].create(
            proxyA,
            {
                'nameA1' : f"Proxy A1-{seq}",
                'amountA1' : 1000 + seq,
            },
        )
        proxyB = classes['B'].create(
            parent,
            {
                'nameB' : f"Proxy B-{seq}",
                'amountB' : 200 + seq,
            },
        )
        # save data
        parent.save()

    return classes


@pytest.fixture( scope='class' )
def getSampleParent( getPopulatedMPMUDClasses ):
    classes = getPopulatedMPMUDClasses
    # find a random entry of the parent class
    return classes['parent'].find_one()


@pytest.fixture( scope='class' )
def getSampleProxyA( getPopulatedMPMUDClasses, getSampleParent ):
    classes = getPopulatedMPMUDClasses
    return classes['A'].get_proxy( getSampleParent )


@pytest.fixture( scope='class' )
def getSampleProxyA1( getPopulatedMPMUDClasses, getSampleProxyA ):
    classes = getPopulatedMPMUDClasses
    return classes['A1'].get_proxy( getSampleProxyA )



class TestInitSubclass:
    """Test __init_subclass__ permutations"""

    def test_init_subclass( self ):
        class MyTestClassBase( mongo_objects.PolymorphicMongoSingleProxy ):
            # create our own local testing namespace
            proxy_subclass_map = {}

        class MyTestSubclassA( MyTestClassBase ):
            proxy_subclass_key = 'A'

        class MyTestSubclassB( MyTestClassBase ):
            proxy_subclass_key = 'B'

        class MyTestSubclassC( MyTestClassBase ):
            proxy_subclass_key = 'C'

        # Verify that all classes were added to the map
        assert MyTestClassBase.proxy_subclass_map == {
            None : MyTestClassBase,
            'A' : MyTestSubclassA,
            'B' : MyTestSubclassB,
            'C' : MyTestSubclassC
        }

        # verify our local subclass map namespace didn't affect the module base class map
        assert len( mongo_objects.PolymorphicMongoSingleProxy.proxy_subclass_map ) == 0


    def test_init_subclass_duplicate_key( self ):
        with pytest.raises( mongo_objects.MongoObjectsSubclassError ):

            class MyTestClassBase( mongo_objects.PolymorphicMongoSingleProxy ):
                # create our own local testing namespace
                proxy_subclass_map = {}

            class MyTestSubclassA( MyTestClassBase ):
                proxy_subclass_key = 'A'

            class MyTestSubclassAnotherA( MyTestClassBase ):
                proxy_subclass_key = 'A'




class TestCreate:
    def test_create( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # create an empty parent document
        parent = classes['parent']( {} )
        parent.save()

        # record current state
        original = copy.deepcopy( parent.data )

        # create a base class proxy object
        newProxy = classes['A'].create(
            parent,
            { 'name' : 'new proxyA entry'},
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A'] )

        # Now create new subclass objects; these will overwrite each other
        for key in ('Aa', 'Ab', 'Ac'):
            newProxy = classes[key].create(
                parent,
                { 'name' : f"new proxy{key} entry" }
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify one new subdoc created
        assert len( parent.keys() ) == len( original.keys() ) + 1

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


class TestCreateNoSave:
    def test_create_no_save( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # create an empty parent document
        parent = classes['parent']( {} )
        parent.save()

        # record current state
        original = copy.deepcopy( parent.data )

        # create a base class proxy object
        newProxy = classes['A'].create( 
            parent,
            { 'name' : 'new proxyA entry'},
            autosave=False
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A'] )

        # Now create new subclass objects; these will overwrite each other
        for key in ('Aa', 'Ab', 'Ac'):
            newProxy = classes[key].create(
                parent,
                { 'name' : f"new proxy{key} entry" },
                autosave=False
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify one new subdoc created
        assert len( parent.keys() ) == len( original.keys() ) + 1

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']


class TestCreateA1:
    def test_create_A1( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # create an empty parent document
        parent = classes['parent']( {} )
        proxyA = classes['A'].create( parent, {} )
        parent.save()

        # record current state
        original = copy.deepcopy( parent.data )

        # create a base class second-level proxy object
        newProxy = classes['A1'].create(
            proxyA,
            { 'name' : 'new proxyA1 entry'},
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A1'] )

        # Now create new second-level subclass objects
        for key in ('A1a', 'A1b', 'A1c'):
            newProxy = classes[key].create(
                proxyA,
                { 'name' : f"new proxy{key} entry" },
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify one new subdoc created at the second level
        assert len( parent.keys() ) == len( original.keys() )
        assert len( proxyA.keys() ) == len( original[ classes['A'].container_name ].keys() ) + 1

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


class TestCreateA1NoSave:
    def test_create_A1_no_save( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # create an empty parent document
        parent = classes['parent']( {} )
        proxyA = classes['A'].create( parent, {} )
        parent.save()

        # record current state
        original = copy.deepcopy( parent.data )

        # create a base class second-level proxy object
        newProxy = classes['A1'].create(
            proxyA,
            { 'name' : 'new proxyA1 entry'},
            autosave=False
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A1'] )

        # Now create new second-level subclass objects
        for key in ('A1a', 'A1b', 'A1c'):
            newProxy = classes[key].create(
                proxyA,
                { 'name' : f"new proxy{key} entry" },
                autosave=False
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify one new subdoc created at the second level
        assert len( parent.keys() ) == len( original.keys() )
        assert len( proxyA.keys() ) == len( original[ classes['A'].container_name ].keys() ) + 1

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']



class TestPolymorphicBasics:
    def test_subclass_map( self , getPopulatedMPMUDClasses ):
        """getMPMUDClasses create a new proxy_subclass_map namespace for each proxy base class
        Verify the keys in the proxy_subclass map
        Verify the base class proxy_subclass map is empty"""
        classes = getPopulatedMPMUDClasses
        assert len( mongo_objects.PolymorphicMongoSingleProxy.proxy_subclass_map ) == 0
        assert len( set( classes['A'].proxy_subclass_map ).difference( [None, 'Aa', 'Ab', 'Ac'] ) ) == 0
        assert len( set( classes['A1'].proxy_subclass_map ).difference( [None, 'A1a', 'A1b', 'A1c'] ) ) == 0
        assert len( set( classes['B'].proxy_subclass_map ).difference( [None, 'Ba', 'Bb', 'Bc'] ) ) == 0


    def test_get_proxy( self, getPopulatedMPMUDClasses ):
        """
        Test accessing both first-level and second-level proxies
        """
        classes = getPopulatedMPMUDClasses

        # record how many documents we find and how many subclasses
        docCount = 0
        proxyAVariants = set()
        proxyA1Variants = set()

        # loop through all pre-populated objects as they contain different
        # subclasses of the proxies
        for parent in classes['parent'].find():
            docCount += 1

            # load the polymorphic proxyA
            proxyA = classes['A'].get_proxy( parent )

            # verify dictionary content; all subclasses use the same container name
            assert id( proxyA.data() ) == id( parent[ classes['A'].container_name ] )

            # verify polymorphic subclass key and add it to the list
            assert proxyA.get( '_psckey' ) in (None, 'Aa', 'Ab', 'Ac')
            proxyAVariants.add( proxyA.get('_psckey') )

            # verify instance type; all objects must be a instance of A or one of its subclasses
            assert isinstance( proxyA, classes['A'] )

            # for subclasses, verify the exact class
            if '_psckey' in proxyA:
                assert isinstance( proxyA, classes[ proxyA['_psckey'] ] )


            # load the polymorphic proxyA1
            proxyA1 = classes['A1'].get_proxy( proxyA )

            # verify dictionary content; all subclasses use the same container name
            assert id( proxyA1.data() ) == id( parent[ classes['A'].container_name ][ classes['A1'].container_name ] )

            # verify polymorphic subclass key and add it to the list
            assert proxyA1.get( '_psckey' ) in (None, 'A1a', 'A1b', 'A1c')
            proxyA1Variants.add( proxyA1.get('_psckey') )

            # verify instance type; all objects must be a instance of A1 or one of its subclasses
            assert isinstance( proxyA1, classes['A1'] )

            # for subclasses, verify the exact class
            if '_psckey' in proxyA1:
                assert isinstance( proxyA1, classes[ proxyA1['_psckey'] ] )

        # the way the sample data is created, make sure we found as many
        # polymorphic subclasses as documents themselves
        assert docCount == len( proxyAVariants )
        assert docCount == len( proxyA1Variants )


    def test_get_proxy_subclass( self, getPopulatedMPMUDClasses ):
        """
        Test accessing both first-level and second-level proxies via sublcass
        """
        classes = getPopulatedMPMUDClasses

        # loop through all pre-populated objects as they contain different
        # subclasses of the proxies
        for parent in classes['parent'].find():

            # load the polymorphic proxyA
            proxyA = classes['A'].get_proxy( parent )

            # loop through the subclasses
            for subclass in ('Aa', 'Ab', 'Ac'):
                # we should also be able to locate the proxy with its subclass
                if proxyA.get('_psckey') == subclass:
                    proxyA_by_subclass = classes[subclass].get_proxy( parent )
                    assert id( proxyA.data() ) == id( proxyA_by_subclass.data() )

                # creating a proxy with the wrong class raises an exception
                else:
                    with pytest.raises( mongo_objects.MongoObjectsPolymorphicMismatch ):
                        proxyA_by_subclass = classes[subclass].get_proxy( parent )
                        proxyA_by_subclass.keys()


            # load the polymorphic proxyA1
            proxyA1 = classes['A1'].get_proxy( proxyA )

            # loop through the subclasses
            for subclassA1 in ('A1a', 'A1b', 'A1c'):
                # we should also be able to locate the proxy with its subclass
                if proxyA1.get('_psckey') == subclassA1:
                    proxyA1_by_subclass = classes[subclassA1].get_proxy( proxyA )
                    assert id( proxyA1.data() ) == id( proxyA1_by_subclass.data() )

                # creating a proxy with the wrong class raises an exception
                else:
                    with pytest.raises( mongo_objects.MongoObjectsPolymorphicMismatch ):
                        proxyA1_by_subclass = classes[subclassA1].get_proxy( proxyA )
                        proxyA1_by_subclass.keys()


    def test_get_proxies( self, getMPMUDClasses, getSampleParent ):
        '''
        Single proxies don't support get_proxes()
        Verify an exception is raised
        '''
        classes = getMPMUDClasses
        parent = getSampleParent
        with pytest.raises( Exception ):
            classes['A'].get_proxies( parent )


    def test_get_subclass_by_key( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # Check the map from the base class
        assert classes['A'].get_subclass_by_key( 'Aa' ) == classes['Aa']
        assert classes['A'].get_subclass_by_key( 'Ab' ) == classes['Ab']
        assert classes['A'].get_subclass_by_key( 'Ac' ) == classes['Ac']

        # In the default classes, the base doc class has None
        # as a subclass key and so is the default for all unknown
        # subclass keys
        assert classes['A'].get_subclass_by_key( 'A' ) == classes['A']
        assert classes['A'].get_subclass_by_key( 'Ad' ) == classes['A']


    def test_get_subclass_by_key_from_subclass( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # Check the map from the base class
        assert classes['Aa'].get_subclass_by_key( 'Aa' ) == classes['Aa']
        assert classes['Aa'].get_subclass_by_key( 'Ab' ) == classes['Ab']
        assert classes['Aa'].get_subclass_by_key( 'Ac' ) == classes['Ac']

        # In the default classes, the base doc class has None
        # as a subclass key and so is the default for all unknown
        # subclass keys
        assert classes['Aa'].get_subclass_by_key( 'A' ) == classes['A']
        assert classes['Aa'].get_subclass_by_key( 'Ad' ) == classes['A']


    def test_get_subclass_by_key_no_default( self ):
        '''Test get_subclass_by_key with a different class structure
        where the base class has its own proxy_subclass_key and thus
        there is no default class.'''
        class LocalMongoSingleProxyA( mongo_objects.PolymorphicMongoSingleProxy ):
            container_name = 'proxyA'
            proxy_subclass_map = {}
            proxy_subclass_key = 'A'

        class LocalMongoSingleProxyAa( LocalMongoSingleProxyA ):
            proxy_subclass_key = 'Aa'

        class LocalMongoSingleProxyAb( LocalMongoSingleProxyA ):
            proxy_subclass_key = 'Ab'

        class LocalMongoSingleProxyAc( LocalMongoSingleProxyA ):
            proxy_subclass_key = 'Ac'

        assert LocalMongoSingleProxyA.get_subclass_by_key( 'A' ) == LocalMongoSingleProxyA
        assert LocalMongoSingleProxyA.get_subclass_by_key( 'Aa' ) == LocalMongoSingleProxyAa
        assert LocalMongoSingleProxyA.get_subclass_by_key( 'Ab' ) == LocalMongoSingleProxyAb
        assert LocalMongoSingleProxyA.get_subclass_by_key( 'Ac' ) == LocalMongoSingleProxyAc

        # There is no default class (no class with a None subclass_key)
        # so unknown subclass keys will raise an exception
        with pytest.raises( mongo_objects.MongoObjectsPolymorphicMismatch ):
            LocalMongoSingleProxyA.get_subclass_by_key( 'Ad' )

        # Also check the return from a subclass
        assert LocalMongoSingleProxyAa.get_subclass_by_key( 'A' ) == LocalMongoSingleProxyA
        assert LocalMongoSingleProxyAa.get_subclass_by_key( 'Aa' ) == LocalMongoSingleProxyAa
        assert LocalMongoSingleProxyAa.get_subclass_by_key( 'Ab' ) == LocalMongoSingleProxyAb
        assert LocalMongoSingleProxyAa.get_subclass_by_key( 'Ac' ) == LocalMongoSingleProxyAc

        # There is no default class (no class with a None subclass_key)
        # so unknown subclass keys will raise an exception
        with pytest.raises( mongo_objects.MongoObjectsPolymorphicMismatch ):
            LocalMongoSingleProxyAa.get_subclass_by_key( 'Ad' )


    def test_get_subclass_from_doc( self, getMPMUDClasses ):
        classes = getMPMUDClasses
        assert classes['A'].get_subclass_by_key( 'Aa' ) == classes['Aa']
        assert classes['A'].get_subclass_from_doc( { classes['A'].proxy_subclass_key_name : 'Aa' } ) == classes['Aa']


