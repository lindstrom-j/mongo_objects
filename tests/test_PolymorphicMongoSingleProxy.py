# test_PolymorphicMongoSingleProxy
#
# Since MongoSingleProxy has been thoroughly exercised elsewhere,
# only test functionality unique to PolymorphicMongoSingleProxy

from bson import ObjectId
from datetime import datetime
import mongo_objects
from pymongo.collection import Collection
import pytest
import secrets



@pytest.fixture( scope='class' )
def getMPMUDClasses( mongo_db ):
    '''Return a set of polymorphic MongoUserDict classes configured for a per-test-class unique collection

    Since each class is only used once per object, we can predefine the container_name'''

    class MyMongoUserDict( mongo_objects.MongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db

    class MyMongoSingleProxyA( mongo_objects.PolymorphicMongoSingleProxy ):
        proxy_subclass_map = {}
        container_name = "proxyA-0"

    class MyMongoSingleProxyAa( MyMongoSingleProxyA ):
        proxy_subclass_key = 'Aa'
        container_name = "proxyA-1"

    class MyMongoSingleProxyAb( MyMongoSingleProxyA ):
        proxy_subclass_key = 'Ab'
        container_name = "proxyA-2"

    class MyMongoSingleProxyAc( MyMongoSingleProxyA ):
        proxy_subclass_key = 'Ac'
        container_name = "proxyA-3"

    class MyMongoSingleProxyA1( mongo_objects.PolymorphicMongoSingleProxy ):
        proxy_subclass_map = {}
        container_name = "proxyA1-0"

    class MyMongoSingleProxyA1a( MyMongoSingleProxyA1 ):
        proxy_subclass_key = 'A1a'
        container_name = "proxyA1-1"

    class MyMongoSingleProxyA1b( MyMongoSingleProxyA1 ):
        proxy_subclass_key = 'A1b'
        container_name = "proxyA1-2"

    class MyMongoSingleProxyA1c( MyMongoSingleProxyA1 ):
        proxy_subclass_key = 'A1c'
        container_name = "proxyA1-3"

    class MyMongoSingleProxyB( mongo_objects.PolymorphicMongoSingleProxy ):
        proxy_subclass_map = {}
        container_name = "proxyB-0"

    class MyMongoSingleProxyBa( MyMongoSingleProxyB ):
        proxy_subclass_key = 'Ba'
        container_name = "proxyB-1"

    class MyMongoSingleProxyBb( MyMongoSingleProxyB ):
        proxy_subclass_key = 'Bb'
        container_name = "proxyB-2"

    class MyMongoSingleProxyBc( MyMongoSingleProxyB ):
        proxy_subclass_key = 'Bc'
        container_name = "proxyB-3"


    return {
        'base' : MyMongoUserDict,
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

    classes = getMPMUDClasses
    itemMax = 3     # make three of everything

    # make parent objects
    for i in range( itemMax ):
        parent = classes['base']( {
            'name' : f"Record {i}",
            'amount' : i * 10,
        } )

        # make "A" proxies include a base-class proxy
        for (j, keyA) in enumerate( ['A', 'Aa', 'Ab', 'Ac'] ):
            proxyA = classes[keyA].create(
                parent,
                {
                    'nameA' : f"Proxy A-{j}",
                    'amountA' : j * 100,
                },
            )

            # make second-level A1 proxies
            for (k, keyA1) in enumerate( ['A1', 'A1a', 'A1b', 'A1c'] ):
                proxyA1 = classes[keyA1].create(
                    proxyA,
                    {
                        'nameA1' : f"Proxy A1-{k}",
                        'amountA1' : k * 1000,
                    },
                )

        # make "B" proxies
        for (j, keyB) in enumerate( ['B', 'Ba', 'Bb', 'Bc'] ):
            proxyB = classes[keyB].create(
                parent,
                {
                    'nameB' : f"Proxy B-{j}",
                    'amountB' : j * 100 + 1,
                },
            )


        # save data
        parent.save()

    return classes


@pytest.fixture( scope='class' )
def getSampleParent( getPopulatedMPMUDClasses ):
    classes = getPopulatedMPMUDClasses
    # find a random entry of the base class
    return classes['base'].find_one()


@pytest.fixture( scope='class' )
def getSampleProxyAKey():
    '''Return a fixed sample key for first-level A proxy testing'''
    return 'proxyA-0'


@pytest.fixture( scope='class' )
def getSampleProxyAKeys():
    '''Return a fixed sample keys for first-level A proxy testing'''
    return [ 'proxyA-0', 'proxyA-1', 'proxyA-2' ]


@pytest.fixture( scope='class' )
def getSampleProxyA( getPopulatedMPMUDClasses, getSampleParent, getSampleProxyAKey ):
    classes = getPopulatedMPMUDClasses
    return classes['A'].get_proxy( getSampleParent, getSampleProxyAKey )


@pytest.fixture( scope='class' )
def getSampleProxyA1Key():
    '''Return a fixed sample key for second-level A1 proxy testing'''
    return 'proxyA1-0'


@pytest.fixture( scope='class' )
def getSampleProxyA1Keys():
    '''Return a fixed sample keys for first-level A proxy testing'''
    return [ 'proxyA1-0', 'proxyA1-1', 'proxyA1-2' ]


@pytest.fixture( scope='class' )
def getSampleProxyA1( getPopulatedMPMUDClasses, getSampleProxyA, getSampleProxyA1Key ):
    classes = getPopulatedMPMUDClasses
    return classes['A1'].get_proxy( getSampleProxyA, getSampleProxyA1Key )



class TestInitSubclass:
    '''Test __init_subclass__ permutations'''

    def test_init_subclass( self ):
        class MyTestClassBase( mongo_objects.PolymorphicMongoSingleProxy ):
            # create our own local testing namespace
            proxy_subclass_map = {}

        class MyTestSubclassA( MyTestClassBase ):
            proxy_subclass_key = 'A'

        class MyTestSubclassB( MyTestClassBase ):
            proxy_subclass_key = 'B'

        class MyTestSubclassC( MyTestClassBase ):
            pass

        # Verify that classes A and B were added to the map
        # Class C should be skipped because it doesn't have a non-None subclass_key
        assert MyTestClassBase.proxy_subclass_map == {
            'A' : MyTestSubclassA,
            'B' : MyTestSubclassB
        }

        # verify our local subclass map namespace didn't affect the module base class map
        assert len( mongo_objects.PolymorphicMongoBaseProxy.proxy_subclass_map ) == 0


    def test_init_subclass_duplicate_key( self ):
        with pytest.raises( Exception ):

            class MyTestClassBase( mongo_objects.PolymorphicMongoSingleProxy ):
                # create our own local testing namespace
                proxy_subclass_map = {}

            class MyTestSubclassA( MyTestClassBase ):
                proxy_subclass_key = 'A'

            class MyTestSubclassAnotherA( MyTestClassBase ):
                proxy_subclass_key = 'A'




class TestCreate:
    def test_create( self, getPopulatedMPMUDClasses, getSampleProxyA ):
        classes = getPopulatedMPMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent

        # record current state
        original = dict( parent )
        count = len( proxyA.get_subdoc_container().keys() )

        # create a base class proxy object
        # Override the container name since there is already a proxyA at the default location
        newProxy = classes['A'].create( 
            parent,
            { 'name' : 'new proxyA entry'},
            key='newProxyA'
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A'] )

        # Now create new subclass objects
        for key in ('Aa', 'Ab', 'Ac'):
            newProxy = classes[key].create(
                parent,
                { 'name' : f"new proxy{key} entry" },
                key=f"newProxy{key}" )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify four new entries created
        assert len( proxyA.get_subdoc_container().keys() ) == count+4

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


class TestCreateNoSave:
    def test_create_no_save( self, getPopulatedMPMUDClasses, getSampleProxyA ):
        classes = getPopulatedMPMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent

        # record current state
        original = dict( parent )
        count = len( proxyA.get_subdoc_container().keys() )

        # create a base class proxy object
        newProxy = classes['A'].create( 
            parent,
            { 'name' : 'new proxyA entry'},
            key='newProxyA',
            autosave=False
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A'] )

        # Now create new subclass objects
        for key in ('Aa', 'Ab', 'Ac'):
            newProxy = classes[key].create(
                parent,
                { 'name' : f"new proxy{key} entry" },
                key=f"newProxy{key}",
                autosave=False
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify four new entries created
        assert len( proxyA.get_subdoc_container().keys() ) == count+4

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']


class TestCreateA1:
    def test_create_A1( self, getPopulatedMPMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMPMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent
        parent = proxyA1.ultimate_parent

        # record current state
        original = dict( parent )
        countA = len( proxyA.get_subdoc_container().keys() )
        countA1 = len( proxyA1.get_subdoc_container().keys() )

        # create a base class second-level proxy object
        newProxy = classes['A1'].create(
            proxyA,
            { 'name' : 'new proxyA1 entry'},
            key='newProxyA1'
        )

        # Since the base class does not define a proxy_subclass_key, verify none was added to the record
        assert '_psckey' not in newProxy
        assert isinstance( newProxy, classes['A1'] )

        # Now create new second-level subclass objects
        for key in ('A1a', 'A1b', 'A1c'):
            newProxy = classes[key].create(
                proxyA,
                { 'name' : f"new proxy{key} entry" },
                key=f"newProxy{key}",
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify four new entries created at the second level
        assert len( proxyA.get_subdoc_container().keys() ) == countA
        assert len( proxyA1.get_subdoc_container().keys() ) == countA1+4

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


class TestCreateA1NoSave:
    def test_create_A1_no_save( self, getPopulatedMPMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMPMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent
        parent = proxyA1.ultimate_parent

        # record current state
        original = dict( parent )
        countA = len( proxyA.get_subdoc_container().keys() )
        countA1 = len( proxyA1.get_subdoc_container().keys() )

        # create a base class second-level proxy object
        newProxy = classes['A1'].create(
            proxyA,
            { 'name' : 'new proxyA1 entry'},
            key='newProxyA',
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
                key=f"newProxy{key}",
                autosave=False
            )
            assert newProxy['_psckey'] == key
            assert isinstance( newProxy, classes[key] )

        # verify four new entries created at the second level
        assert len( proxyA.get_subdoc_container().keys() ) == countA
        assert len( proxyA1.get_subdoc_container().keys() ) == countA1+4

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']



class TestPolymorphicBasics:
    def test_subclass_map( self , getPopulatedMPMUDClasses ):
        '''getMPMUDClasses create a new proxy_subclass_map namespace for each proxy base class
        Verify the keys in the proxy_subclass map
        Verify the base class proxy_subclass map is empty'''
        classes = getPopulatedMPMUDClasses
        assert len( mongo_objects.PolymorphicMongoSingleProxy.proxy_subclass_map ) == 0
        assert sorted( classes['A'].proxy_subclass_map ) == ['Aa', 'Ab', 'Ac']
        assert sorted( classes['A1'].proxy_subclass_map ) == ['A1a', 'A1b', 'A1c']
        assert sorted( classes['B'].proxy_subclass_map ) == ['Ba', 'Bb', 'Bc']


    def test_get_proxy( self, getPopulatedMPMUDClasses, getSampleParent, getSampleProxyAKeys, getSampleProxyA1Keys ):
        '''Test accessing both first-level and second-level proxies

        For testing convenience, the keys of the getPopulatedMPMUDClasses dictionary
        match the proxy_subclass_key for each subclass'''
        classes = getPopulatedMPMUDClasses
        parent = getSampleParent

        # loop through keys in the proxy A container
        for keyA in getSampleProxyAKeys:

            # create a first-level proxy object
            proxyA = classes['A'].get_proxy( parent, keyA )

            # verify dictionary
            assert id( proxyA.data() ) == id( parent[ keyA ] )

            # the base class object won't have _psckey
            if '_psckey' not in proxyA:
                assert isinstance( proxyA, classes['A'] )
            else:
                assert isinstance( proxyA, classes[ proxyA['_psckey'] ] )

            # loop through the keys of the second level proxy A1 container
            for keyA1 in getSampleProxyA1Keys:

                # create a second-level proxy object
                proxyA1 = classes['A1'].get_proxy( proxyA, keyA1 )

                # verify dictionary
                assert id( proxyA1.data() ) == id( parent[ keyA ][ keyA1 ] )

                # the base class object won't have _psckey
                if '_psckey' not in proxyA1:
                    assert isinstance( proxyA1, classes['A1'] )
                else:
                    assert isinstance( proxyA1, classes[ proxyA1['_psckey'] ] )


    def test_get_subclass_by_key( self, getMPMUDClasses ):
        classes = getMPMUDClasses
        assert classes['A'].get_subclass_by_key( 'Aa' ) == classes['Aa']


    def test_get_subclass_from_doc( self, getMPMUDClasses ):
        classes = getMPMUDClasses
        assert classes['A'].get_subclass_by_key( 'Aa' ) == classes['Aa']
        assert classes['A'].get_subclass_from_doc( { classes['A'].proxy_subclass_key_name : 'Aa' } ) == classes['Aa']


