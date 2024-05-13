# test_MongoListProxy

from bson import ObjectId
from datetime import datetime
import mongo_objects
from pymongo.collection import Collection
import pytest
import secrets


@pytest.fixture( scope='class' )
def getMMUDClasses( mongo_db ):
    """Return a MongoUserDict configured for a per-class unique collection"""

    class MyMongoUserDict( mongo_objects.MongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db

    class MyMongoListProxyA( mongo_objects.MongoListProxy ):
        container_name = 'proxyA'

    class MyMongoListProxyA1( mongo_objects.MongoListProxy ):
        container_name = 'proxyA1'

    class MyMongoListProxyB( mongo_objects.MongoListProxy ):
        container_name = 'proxyB'

    return {
        'parent_doc' : MyMongoUserDict,
        'A' : MyMongoListProxyA,
        'A1' : MyMongoListProxyA1,
        'B' : MyMongoListProxyB
    }



@pytest.fixture( scope='class' )
def getPopulatedMMUDClasses( getMMUDClasses ):

    classes = getMMUDClasses
    itemMax = 3     # make three of everything

    # make parent objects
    for i in range( itemMax ):
        parent = classes['parent_doc']( {
            'name' : f"Record {i}",
            'amount' : i * 10,
        } )

        # make first-level proxies
        for j in range( itemMax ):
            proxyA = classes['A'].create( parent, {
                'nameA' : f"Proxy A-{j}",
                'amountA' : j * 100,
            } )
            proxyB = classes['B'].create( parent, {
                'nameB' : f"Proxy B-{j}",
                'amountB' : j * 100 + 1,
            } )

            # make second-level proxies
            for k in range( itemMax ):
                proxyA1 = classes['A1'].create( proxyA, {
                    'nameA1' : f"Proxy A1-{k}",
                    'amountA1' : k * 1000,
                } )

        # save data
        parent.save()

    return classes


@pytest.fixture( scope='class' )
def getSampleParent( getPopulatedMMUDClasses ):
    classes = getPopulatedMMUDClasses
    # find a random entry of the base class
    return classes['parent_doc'].find_one()


@pytest.fixture( scope='class' )
def getSampleProxyA( getPopulatedMMUDClasses, getSampleParent ):
    classes = getPopulatedMMUDClasses
    # return the first proxyA in the list
    return classes['A'].get_proxies( getSampleParent )[0]


@pytest.fixture( scope='class' )
def getSampleProxyA1( getPopulatedMMUDClasses, getSampleProxyA ):
    classes = getPopulatedMMUDClasses
    # return the first proxyA1 in the list
    return classes['A1'].get_proxies( getSampleProxyA )[0]


# utility functions
def get_keys( proxy ):
    return [ proxy.get_key( doc ) for doc in proxy.get_subdoc_container() ]



class TestCreate:
    def test_create( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent

        # record current state
        original = parent.copy()
        count = len( proxyA.get_subdoc_container() )

        # create a new entry in a level one proxy
        newProxy = classes['A'].create( parent, { 'name' : 'new proxyA entry'} )

        # verify a key was added to the proxy
        assert proxyA.subdoc_key_name in newProxy

        # verify new key exists in the list
        assert newProxy.key in get_keys( proxyA )

        # verify a new entry was created
        assert len( proxyA.get_subdoc_container() ) == count+1
        assert parent['_last_unique_integer'] == original['_last_unique_integer'] + 1

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


    def test_create_no_save( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent

        # record current state
        original = parent.copy()
        count = len( proxyA.get_subdoc_container() )

        # create a new entry in a level one proxy without saving the parent
        newProxy = classes['A'].create( parent, { 'name' : 'new proxyA entry'}, autosave=False )

        # verify a key was added to the proxy
        assert proxyA.subdoc_key_name in newProxy

        # verify new key exists in the list
        assert newProxy.key in get_keys( proxyA )

        # verify a new entry was created
        assert len( proxyA.get_subdoc_container() ) == count+1
        assert parent['_last_unique_integer'] == original['_last_unique_integer'] + 1

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']


    def test_create_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent
        parent = proxyA1.ultimate_parent

        # record current state
        original = parent.copy()
        countA = len( proxyA.get_subdoc_container() )
        countA1 = len( proxyA1.get_subdoc_container() )

        # create a new entry in a level two proxy
        newProxy = classes['A1'].create( proxyA, { 'name' : 'new proxyA1 entry'} )

        # verify a key was added to the proxy
        assert proxyA1.subdoc_key_name in newProxy

        # verify new key exists in the list
        assert newProxy.key in get_keys( proxyA1 )

        # verify a new entry was created at the second (proxyA1) level
        assert len( proxyA.get_subdoc_container() ) == countA
        assert len( proxyA1.get_subdoc_container() ) == countA1 + 1
        assert parent['_last_unique_integer'] == original['_last_unique_integer'] + 1

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


    def test_create_A1_no_save( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent
        parent = proxyA1.ultimate_parent

        # record current state
        original = parent.copy()
        countA = len( proxyA.get_subdoc_container() )
        countA1 = len( proxyA1.get_subdoc_container() )

        # create a new entry in a level two proxy without saving the parent
        newProxy = classes['A1'].create( proxyA, { 'name' : 'new proxyA1 entry'}, autosave=None )

        # verify a key was added to the proxy
        assert proxyA1.subdoc_key_name in newProxy

        # verify new key exists in the list
        assert newProxy.key in get_keys( proxyA1 )

        # verify a new entry was created at the second (proxyA1) level
        assert len( proxyA.get_subdoc_container() ) == countA
        assert len( proxyA1.get_subdoc_container() ) == countA1 + 1
        assert parent['_last_unique_integer'] == original['_last_unique_integer'] + 1

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']




class TestDelete_ProxyA:
    def test_delete( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent

        # record current state
        original = parent.copy()
        count = len( proxyA.get_subdoc_container() )
        key = proxyA.key

        # delete the level one proxy
        proxyA.delete()

        # verify the entry was deleted
        assert key not in get_keys( proxyA )
        assert proxyA.key is None
        assert len( proxyA.get_subdoc_container() ) == count-1

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']


class TestDelete_ProxyA_No_Save:
    def test_delete_no_save( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent

        # record current state
        original = parent.copy()
        count = len( proxyA.get_subdoc_container() )
        key = proxyA.key

        # delete the level one proxy without saving the parent
        proxyA.delete( autosave=False )

        # verify the entry was deleted
        assert key not in get_keys( proxyA )
        assert proxyA.key is None
        assert len( proxyA.get_subdoc_container() ) == count-1

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']




class TestDelete_ProxyA1:
    def test_delete_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent
        parent = proxyA1.ultimate_parent

        # record current state
        original = parent.copy()
        countA = len( proxyA.get_subdoc_container() )
        countA1 = len( proxyA1.get_subdoc_container() )
        key = proxyA1.key

        # delete the level one proxy
        proxyA1.delete()

        # verify the entry was deleted
        assert key not in get_keys( proxyA1 )
        assert proxyA1.key is None
        assert len( proxyA.get_subdoc_container() ) == countA
        assert len( proxyA1.get_subdoc_container() ) == countA1 - 1

        # confirm the parent document was saved
        assert parent['_updated'] > original['_updated']




class TestDelete_ProxyA1_No_Save:
    def test_delete_A1_no_save( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent
        parent = proxyA1.ultimate_parent

        # record current state
        original = parent.copy()
        countA = len( proxyA.get_subdoc_container() )
        countA1 = len( proxyA1.get_subdoc_container() )
        key = proxyA1.key

        # delete the level one proxy
        proxyA1.delete( autosave=False )

        # verify the entry was deleted
        assert key not in get_keys( proxyA )
        assert proxyA1.key is None
        assert len( proxyA.get_subdoc_container() ) == countA
        assert len( proxyA1.get_subdoc_container() ) == countA1 - 1

        # confirm the parent document was not saved
        assert parent['_updated'] == original['_updated']




class TestDelItem:
    def test_delitem( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA

        # verify that the key exists in the proxy
        assert 'nameA' in proxy

        # delete the key
        del proxy['nameA']

        # verify that the key no longer exists
        assert 'nameA' not in proxy

        # save the data
        proxy.save()

        # locate the object on disk
        doc = classes['parent_doc'].collection().find_one( { '_id' : proxy.parent['_id'] } )

        # verify that the key no longer exists in the database as well
        assert 'nameA' not in doc['proxyA'][ proxy.seq ]



class TestDelItem_A1:
    def test_delitem( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA1

        # verify that the key exists in the proxy
        assert 'nameA1' in proxy

        # delete the key
        del proxy['nameA1']

        # verify that the key no longer exists
        assert 'nameA1' not in proxy

        # save the data
        proxy.save()

        # locate the object on disk
        doc = classes['parent_doc'].collection().find_one( { '_id' : proxy.ultimate_parent['_id'] } )

        # verify that the key no longer exists in the database as well
        assert 'nameA1' not in doc['proxyA'][ proxy.parent.seq ]['proxyA1'][ proxy.seq ]



class TestSetDefault:
    def test_setdefault( self, getSampleProxyA ):
        proxy = getSampleProxyA
        # confirm initial state
        assert 'newKey' not in proxy
        # set a default value
        proxy.setdefault( 'newKey', 1 )
        assert proxy['newKey'] == 1
        # confirm that setting a second default does nothing
        proxy.setdefault( 'newKey', 2 )
        assert proxy['newKey'] == 1




class TestSetDefaultNone:
    def test_setdefault_none( self, getSampleProxyA ):
        proxy = getSampleProxyA
        # confirm initial state
        assert 'newKey' not in proxy
        # set a default value
        proxy.setdefault( 'newKey' )
        assert proxy['newKey'] is None
        # confirm that setting a second default does nothing
        proxy.setdefault( 'newKey', 2 )
        assert proxy['newKey'] is None




class TestSetDefaultA1:
    def test_setdefault_A1( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        # confirm initial state
        assert 'newKey' not in proxy
        # set a default value
        proxy.setdefault( 'newKey', 1 )
        assert proxy['newKey'] == 1
        # confirm that setting a second default does nothing
        proxy.setdefault( 'newKey', 2 )
        assert proxy['newKey'] == 1




class TestSetDefaultA1None:
    def test_setdefault_A1_none( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        # confirm initial state
        assert 'newKey' not in proxy
        # set a default value
        proxy.setdefault( 'newKey' )
        assert proxy['newKey'] is None
        # confirm that setting a second default does nothing
        proxy.setdefault( 'newKey', 2 )
        assert proxy['newKey'] is None


class TestSetItem:
    def test_setitem( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA

        # verify that the key doesn't exist in the proxy
        assert 'newKey' not in proxy

        # add the key
        proxy['newKey'] = 'this is a new value'

        # verify that the key now exists
        assert 'newKey' in proxy
        assert proxy['newKey'] == 'this is a new value'

        # save the data
        proxy.save()

        # locate the object on disk
        doc = classes['parent_doc'].collection().find_one( { '_id' : proxy.parent['_id'] } )

        # verify that the new key exists in the database as well
        assert 'newKey' in doc['proxyA'][ proxy.seq ]
        assert doc['proxyA'][ proxy.seq ]['newKey'] == 'this is a new value'



class TestSetItem_A1:
    def test_setitem_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA1

        # verify that the key doesn't exist in the proxy
        assert 'newKey' not in proxy

        # add the key
        proxy['newKey'] = 'this is a new value'

        # verify that the key now exists
        assert 'newKey' in proxy
        assert proxy['newKey'] == 'this is a new value'

        # save the data
        proxy.save()

        # locate the object on disk
        doc = classes['parent_doc'].collection().find_one( { '_id' : proxy.ultimate_parent['_id'] } )

        # verify that the new key exists in the database as well
        assert 'newKey' in doc['proxyA'][ proxy.parent.seq ]['proxyA1'][ proxy.seq ]
        assert doc['proxyA'][ proxy.parent.seq ]['proxyA1'][ proxy.seq ]['newKey'] == 'this is a new value'



class TestUpdate:
    def test_update( self, getSampleProxyA ):
        proxy = getSampleProxyA

        # confirm initial state
        assert proxy['nameA'] != 'new name'
        assert proxy['amountA'] != 'new amount'
        assert 'newKey1' not in proxy
        assert 'newKey2' not in proxy
        count = len( proxy.keys() )

        # update the dictionary
        proxy.update( {
            'nameA' : 'new name',
            'amountA' : 'new amount',
            'newKey1' : 1,
            'newKey2' : 2
        } )

        # verify updates
        assert proxy['nameA'] == 'new name'
        assert proxy['amountA'] == 'new amount'
        assert proxy['newKey1'] == 1
        assert proxy['newKey2'] == 2
        assert len( proxy.keys() ) == count + 2


    def test_update_A1( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1

        # confirm initial state
        assert proxy['nameA1'] != 'new name'
        assert proxy['amountA1'] != 'new amount'
        assert 'newKey1' not in proxy
        assert 'newKey2' not in proxy
        count = len( proxy.keys() )

        # update the dictionary
        proxy.update( {
            'nameA1' : 'new name',
            'amountA1' : 'new amount',
            'newKey1' : 1,
            'newKey2' : 2
        } )

        # verify updates
        assert proxy['nameA1'] == 'new name'
        assert proxy['amountA1'] == 'new amount'
        assert proxy['newKey1'] == 1
        assert proxy['newKey2'] == 2
        assert len( proxy.keys() ) == count + 2




class TestBasics:
    def test_copy( self, getSampleProxyA ):
        proxyA = getSampleProxyA
        copied = proxyA.copy()

        # Verify data is the same
        assert copied == proxyA.data()
        # Verify that data location is not the same
        assert id( copied ) != id( proxyA.data() )


    def test_create_key( self, getPopulatedMMUDClasses, getSampleProxyA ):
        """Test key creation for single and two-level proxies"""
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA
        parent = proxyA.parent
        updated = parent['_updated']

        # create a proxyA key
        keyA = classes['A'].create_key( parent, {} )
        assert isinstance( keyA, str )
        assert keyA == f"{parent['_last_unique_integer']:x}"

        # create a proxyA1 key
        keyA1 = classes['A1'].create_key( proxyA, {} )
        assert isinstance( keyA1, str )
        assert keyA1 == f"{parent['_last_unique_integer']:x}"
        assert keyA != keyA1

        # verify that create_key doesn't save the parent object
        doc = classes['parent_doc'].collection().find_one( { '_id' : parent['_id'] } )
        assert doc['_updated'] == updated


    def test_create_key_override( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test custom key creation"""
        parent = getSampleParent
        subdoc = { 'custom' : 'XYZ', 'more-data' : 3.1415 }

        class LocalProxyClass( getPopulatedMMUDClasses['A'] ):
            @classmethod
            def create_key( cls, parent, subdoc ):
                return subdoc['custom']

        # confirm key is extracted as expected
        assert LocalProxyClass.create_key( parent, subdoc ) == 'XYZ'

        # confirm a new object uses the expected key
        proxy = LocalProxyClass.create( parent, subdoc )
        assert proxy.key == 'XYZ'


    def test_contains( self, getSampleProxyA ):
        proxy = getSampleProxyA
        assert 'nameA' in proxy
        assert 'will-not-match' not in proxy


    def test_contains_A1( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        assert 'nameA1' in proxy
        assert 'will-not-match' not in proxy


    def test_data( self, getSampleProxyA ):
        proxy = getSampleProxyA
        # verify that the data references the same dictionary
        assert id( proxy.data() ) == id( proxy.parent['proxyA'][ proxy.seq ] )


    def test_data_A1( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        # verify that the data references the same dictionary
        assert id( proxy.data() ) == id( proxy.ultimate_parent['proxyA'][ proxy.parent.seq ]['proxyA1'][ proxy.seq ] )


    def test_exists( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA
        # verify the class can find this key within this parent
        assert classes['A'].exists( proxy.parent, proxy.key )


    def test_exists_non_existent( self, getPopulatedMMUDClasses, getSampleParent ):
        classes = getPopulatedMMUDClasses
        # verify a non-existent key can't be located
        assert not classes['A'].exists( getSampleParent, 'non-existent-key' )


    def test_get( self, getSampleProxyA ):
        proxy = getSampleProxyA
        assert proxy.get('nameA') is not None
        assert proxy.get('will-not-match') is None


    def test_get( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        assert proxy.get('nameA1') is not None
        assert proxy.get('will-not-match') is None


    def test_getitem( self, getSampleProxyA ):
        proxy = getSampleProxyA
        assert proxy['nameA'] is not None
        with pytest.raises( Exception ):
            assert proxy['will-not-match']


    def test_getitem_A1( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        assert proxy['nameA1'] is not None
        with pytest.raises( Exception ):
            assert proxy['will-not-match']


    def test_get_key( self, getMMUDClasses ):
        classes = getMMUDClasses

        sample = { '_sdkey' : 'proxy-key'}

        assert classes['A'].get_key( sample ) == 'proxy-key'


    def test_get_key_alt_name( self ):
        class MyAltListProxy( mongo_objects.MongoListProxy ):
            subdoc_key_name = 'alt-subdoc-key-name'

        sample = { 'alt-subdoc-key-name' : 'proxy-key'}
        assert MyAltListProxy.get_key( sample ) == 'proxy-key'


    def test_get_proxies( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test accessing both first-level and second-level proxy lists"""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # get all first-level proxies
        result = classes['A'].get_proxies( parent )

        # verify type and length of the result
        assert isinstance( result, list )
        assert len( result ) == len( parent[ classes['A'].container_name ] )

        # verify type matches
        for proxy in result:
            assert isinstance( proxy, classes['A'])

        # choose a proxyA to continue testing with
        proxyA = classes['A'].get_proxy( parent, seq=0 )

        # get all second-level proxies
        result = classes['A1'].get_proxies( proxyA )

        # verify type and length of the result
        assert isinstance( result, list )
        assert len( result ) == len( parent[ classes['A'].container_name ][ proxyA.seq ][ classes['A1'].container_name ] )

        # verify type matches
        for proxy in result:
            assert isinstance( proxy, classes['A1'])


    def test_get_proxies_empty( self, getPopulatedMMUDClasses ):
        """Test get proxies from an empty object"""
        classes = getPopulatedMMUDClasses

        # collect proxies from an empty object
        result = classes['A'].get_proxies( {} )
        assert len(result) == 0


    def test_get_proxy( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test accessing both first-level and second-level proxies"""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # locate the key for the first entry in the proxy A container
        keyA = parent[ classes['A'].container_name ][0][ classes['A'].subdoc_key_name ]

        # create a first-level proxy object
        proxyA = classes['A'].get_proxy( parent, keyA )

        # verify dictionary and type matches
        assert id( proxyA.data() ) == id( parent[ classes['A'].container_name ][0] )
        assert isinstance( proxyA, classes['A'] )

        # locate the key for the first entry in the proxy A1 container
        keyA1 = parent[ classes['A'].container_name ][0][ classes['A1'].container_name ][0][ classes['A'].subdoc_key_name ]

        # create a second-level proxy object
        proxyA1 = classes['A1'].get_proxy( proxyA, keyA1 )

        # verify dictionary and type matches
        assert id( proxyA1.data() ) == id( parent[ classes['A'].container_name ][0][ classes['A1'].container_name ][0] )
        assert isinstance( proxyA1, classes['A1'] )


    def test_get_proxy_by_sequence( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test accessing both first-level and second-level proxies"""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # create a first-level proxy object
        proxyA = classes['A'].get_proxy( parent, seq=0 )

        # verify dictionary and type matches
        assert id( proxyA.data() ) == id( parent[ classes['A'].container_name ][0] )
        assert isinstance( proxyA, classes['A'] )

        # create a second-level proxy object
        proxyA1 = classes['A1'].get_proxy( proxyA, seq=0 )

        # verify dictionary and type matches
        assert id( proxyA1.data() ) == id( parent[ classes['A'].container_name ][0][ classes['A1'].container_name ][0] )
        assert isinstance( proxyA1, classes['A1'] )


    def test_get_subdoc( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # verify data location
        assert id( proxyA.get_subdoc() ) == id( proxyA.parent[ classes['A'].container_name ][ proxyA.seq ] )


    def test_get_subdoc_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # verify data location
        assert id( proxyA1.get_subdoc() ) == id( proxyA1.ultimate_parent[ classes['A'].container_name ][ proxyA1.parent.seq ][ classes['A1'].container_name ][ proxyA1.seq ] )


    def test_get_subdoc_container( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # verify data location
        assert id( proxyA.get_subdoc_container() ) == id( proxyA.parent[ classes['A'].container_name ] )


    def test_get_subdoc_container_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # verify data location
        assert id( proxyA1.get_subdoc_container() ) == id( proxyA1.ultimate_parent[ classes['A'].container_name ][ proxyA1.parent.seq ][ classes['A1'].container_name ] )


    def test_id( self, getSampleProxyA ):
        """Test ID for single level proxy"""
        proxy = getSampleProxyA
        assert proxy.id() == f"{proxy.parent.id()}{proxy.parent.subdoc_key_sep}{proxy.key}"


    def test_id_A1( self, getSampleProxyA1 ):
        """Test ID for two-level proxy"""
        proxy = getSampleProxyA1
        assert proxy.id() == f"{proxy.ultimate_parent.id()}{proxy.ultimate_parent.subdoc_key_sep}{proxy.parent.key}{proxy.ultimate_parent.subdoc_key_sep}{proxy.key}"


    def test_init( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test initialization of single and two-level proxies"""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # pick the first proxyA key
        keyA = parent[ classes['A'].container_name ][0][ classes['A'].subdoc_key_name ]

        # create the proxy
        proxyA = classes['A']( parent, keyA )

        # verify that the data references the same dictionary
        assert id( proxyA.data() ) == id( parent['proxyA'][0] )

        # pick the first proxyA1 key
        keyA1 = parent[ classes['A'].container_name ][0][ classes['A1'].container_name ][0][ classes['A1'].subdoc_key_name ]

        # create the proxy
        proxyA1 = classes['A1']( proxyA, keyA1 )

        # verify that the data references the same dictionary
        assert id( proxyA1.data() ) == id( parent['proxyA'][0]['proxyA1'][0] )


    def test_init_bad_key( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test initialization of single and two-level proxies"""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # creating a first-level proxy with a bad key raises an exception
        # proxy must be accessed before the invalid key is detected
        with pytest.raises( Exception ):
            proxyA = classes['A']( parent, 'not-a-valid-key')
            proxyA.keys()

        # create a proxy for the first proxyA key
        proxyA = classes['A']( parent, seq=0 )

        # creating a second-level proxy with a bad key raises an exception
        # proxy must be accessed before the invalid key is detected
        with pytest.raises( Exception ):
            proxyA1 = classes['A1']( proxyA, 'not-a-valid-key')
            proxyA1.keys()



    def test_init_bad_seq( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test initialization of single and two-level proxies with a bad sequence.
        Invalid sequence values are automatically corrected."""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # pick the first proxyA key
        keyA = parent[ classes['A'].container_name ][0][ classes['A'].subdoc_key_name ]

        # create the proxy with a bad sequence
        proxyA = classes['A']( parent, keyA, seq=1.0 )

        # verify that the data references the same dictionary
        assert id( proxyA.data() ) == id( parent['proxyA'][0] )

        # pick the first proxyA1 key
        keyA1 = parent[ classes['A'].container_name ][0][ classes['A1'].container_name ][0][ classes['A1'].subdoc_key_name ]

        # create the proxy
        proxyA1 = classes['A1']( proxyA, keyA1, seq=1.0 )

        # verify that the data references the same dictionary
        assert id( proxyA1.data() ) == id( parent['proxyA'][0]['proxyA1'][0] )


    def test_init_sequence( self, getPopulatedMMUDClasses, getSampleParent ):
        """Test initialization of single and two-level proxies"""
        classes = getPopulatedMMUDClasses
        parent = getSampleParent

        # create the proxy
        proxyA = classes['A']( parent, seq=0 )

        # verify that the data references the same dictionary
        assert id( proxyA.data() ) == id( parent['proxyA'][0] )

        # create the proxy
        proxyA1 = classes['A1']( proxyA, seq=0 )

        # verify that the data references the same dictionary
        assert id( proxyA1.data() ) == id( parent['proxyA'][0]['proxyA1'][0] )


    def test_iter( self, getSampleProxyA ):
        proxy = getSampleProxyA
        # compare the keys
        assert set( [ key for key in proxy ] ) == set( proxy.parent['proxyA'][ proxy.seq ].keys() )


    def test_iter_A1( self, getSampleProxyA1 ):
        proxy = getSampleProxyA1
        # compare the keys
        assert set( [ key for key in proxy ] ) == set( proxy.parent['proxyA1'][ proxy.seq ].keys() )


    def test_keys( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA

        assert proxy.keys() == proxy.parent[ classes['A'].container_name ][ proxy.seq].keys()


    def test_keys_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent

        assert proxyA1.keys() == proxyA1.ultimate_parent[ classes['A'].container_name ][ proxyA.seq ][ classes['A1'].container_name ][ proxyA1.seq ].keys()


    def test_load_proxy_by_id( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # reload the proxy by its ID
        result = classes['parent_doc'].load_proxy_by_id( proxyA.id(), classes['A'] )

        # verify the objects are the same
        assert result.data() == proxyA.data()

        # verify the parent is not readonly
        assert result.ultimate_parent.readonly is False



    def test_load_proxy_by_id_readonly( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # reload the proxy by its ID
        result = classes['parent_doc'].load_proxy_by_id( proxyA.id(), classes['A'], readonly=True )

        # verify the objects are the same
        assert result.data() == proxyA.data()

        # verify the parent is readonly
        assert result.ultimate_parent.readonly is True


    def test_load_proxy_by_id_invalid_proxy_id( self, getPopulatedMMUDClasses ):
        """Test load_proxy_by_id() with a totally invalid ID"""
        classes = getPopulatedMMUDClasses

        # reload the proxy by its ID
        result = classes['parent_doc'].load_proxy_by_id( 'this-is-not-a-proxy-id', classes['A'] )

        # verify the return value is None
        assert result == None


    def test_load_proxy_by_id_invalid_object_id( self, getPopulatedMMUDClasses, getSampleProxyA ):
        """Test load_proxy_by_id() with a non-existent ObjectId"""
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # tamper with the ID to replace its ObjectId
        proxyId = str( ObjectId() ) + proxyA.id()[24:]

        # reload the proxy by its ID
        result = classes['parent_doc'].load_proxy_by_id( proxyId, classes['A'] )

        # verify the return value is None
        assert result == None


    def test_load_proxy_by_id_invalid_local_id( self, getPopulatedMMUDClasses, getSampleProxyA ):
        """Test load_proxy_by_id() with a non-existent proxy ID"""
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # Can't load proxyB with proxyA's ID
        with pytest.raises( mongo_objects.MongoObjectsNonexistentKey ):
            result = classes['parent_doc'].load_proxy_by_id( proxyA.id(), classes['B'] )
            # list proxies are lazy lookups and must be used to be resolved
            result.keys()


    def test_load_proxy_by_id_list_mismatch( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # loading a proxy with more classes than IDs raises a ValueError
        with pytest.raises( ValueError ):
            classes['parent_doc'].load_proxy_by_id( proxyA.id(), classes['A'], classes['B'] )


    def test_load_proxy_by_id_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # reload the proxy by its ID
        result = classes['parent_doc'].load_proxy_by_id( proxyA1.id(), classes['A'], classes['A1'] )

        # verify the objects are the same
        assert result.data() == proxyA1.data()

        # verify the parent is not readonly
        assert result.ultimate_parent.readonly is False


    def test_load_proxy_by_id_A1_readonly( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # reload the proxy by its ID
        result = classes['parent_doc'].load_proxy_by_id( proxyA1.id(), classes['A'], classes['A1'], readonly=True )

        # verify the objects are the same
        assert result.data() == proxyA1.data()

        # verify the parent is readonly
        assert result.ultimate_parent.readonly is True


    def test_load_proxy_by_id_A1_list_mismatch( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # loading a proxy with more IDs than classes raises a ValueError
        with pytest.raises( ValueError ):
            classes['parent_doc'].load_proxy_by_id( proxyA1.id(), classes['A'] )


    def test_load_proxy_by_local_id( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # reload the proxy by its local ID
        result = proxyA.ultimate_parent.load_proxy_by_local_id( proxyA.proxy_id(), classes['A'] )

        # verify the objects are the same
        assert result.data() == proxyA.data()


    def test_load_proxy_by_local_id_list_mismatch( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # loading a proxy with more classes than IDs raises a ValueError
        with pytest.raises( ValueError ):
            proxyA.ultimate_parent.load_proxy_by_local_id( proxyA.proxy_id(), classes['A'], classes['B'] )


    def test_load_proxy_by_local_id_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # reload the proxy by its ID
        result = proxyA1.ultimate_parent.load_proxy_by_local_id( proxyA1.proxy_id(), classes['A'], classes['A1'] )

        # verify the objects are the same
        assert result.data() == proxyA1.data()



    def test_load_proxy_by_local_id_A1_list_mismatch( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # loading a proxy with more IDs than classes raises a ValueError
        with pytest.raises( ValueError ):
            result = proxyA1.ultimate_parent.load_proxy_by_local_id( proxyA1.proxy_id(), classes['A'] )
            result.keys()


    def test_id_A1( self, getSampleProxyA1 ):
        """Test second level proxy ID"""
        proxy = getSampleProxyA1
        assert proxy.proxy_id() == f"{proxy.parent.key}{proxy.ultimate_parent.subdoc_key_sep}{proxy.key}"


    def test_id_A1_id_with_parent_id( self, getSampleProxyA1 ):
        """Test second level proxy ID with parent ID.
        This should be the same as id()"""
        proxy = getSampleProxyA1
        assert proxy.proxy_id( include_parent_doc_id=True ) == f"{proxy.ultimate_parent.id()}{proxy.ultimate_parent.subdoc_key_sep}{proxy.parent.key}{proxy.ultimate_parent.subdoc_key_sep}{proxy.key}"
        assert proxy.proxy_id( include_parent_doc_id=True ) == proxy.id()


    def test_proxy_id( self, getSampleProxyA ):
        """Test single level proxy ID"""
        proxy = getSampleProxyA
        assert proxy.proxy_id() == f"{proxy.key}"


    def test_proxy_id_with_parent_id( self, getSampleProxyA ):
        """Test single level proxy ID with parent ID
        This should be the same as id()"""
        proxy = getSampleProxyA
        assert proxy.proxy_id( include_parent_doc_id=True ) == f"{proxy.parent.id()}{proxy.parent.subdoc_key_sep}{proxy.key}"
        assert proxy.proxy_id( include_parent_doc_id=True ) == proxy.id()


    def test_save( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxyA = getSampleProxyA

        # preserve original state
        original = proxyA.parent.copy()

        # save the object
        proxyA.save()

        # verify the parent document was saved
        assert proxyA.parent['_updated'] > original['_updated']


    def test_save_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1

        # preserve original state
        original = proxyA1.ultimate_parent.copy()

        # save the object
        proxyA1.save()

        # verify the parent document was saved
        assert proxyA1.ultimate_parent['_updated'] > original['_updated']


    def test_set_key( self, getMMUDClasses ):
        classes = getMMUDClasses

        sample = {}
        classes['A'].set_key( sample, 'proxy-key' )

        assert sample['_sdkey'] == 'proxy-key'


    def test_set_key_alt_name( self ):
        class MyAltListProxy( mongo_objects.MongoListProxy ):
            subdoc_key_name = 'alt-subdoc-key-name'

        sample = {}
        MyAltListProxy.set_key( sample, 'proxy-key' )

        print( repr( sample ) )
        assert sample['alt-subdoc-key-name'] == 'proxy-key'


    def test_values( self, getPopulatedMMUDClasses, getSampleProxyA ):
        classes = getPopulatedMMUDClasses
        proxy = getSampleProxyA

        # compare contents of values() as lists (dict_values objects don't compare properly)
        assert list( proxy.values() ) == list( proxy.parent[ classes['A'].container_name ][ proxy.seq ].values() )


    def test_values_A1( self, getPopulatedMMUDClasses, getSampleProxyA1 ):
        classes = getPopulatedMMUDClasses
        proxyA1 = getSampleProxyA1
        proxyA = proxyA1.parent

        # compare contents of values() as lists (dict_values objects don't compare properly)
        assert list( proxyA1.values() ) == list( proxyA1.ultimate_parent[ classes['A'].container_name ][ proxyA.seq ][ classes['A1'].container_name ][ proxyA1.seq ].values() )





