# test_MongoUserDict

from bson import ObjectId
from datetime import datetime
import mongo_objects
from pymongo.collection import Collection
import pytest
import secrets


@pytest.fixture(scope='session' )
def sampleData():
    return [
        {
            'name' : 'record 1',
            'amount' : 100,
        },
        {
            'name' : 'record 2',
            'amount' : 200,

        },
        {
            'name' : 'record 3',
            'amount' : 300,

        }
    ]


@pytest.fixture( scope='class' )
def getMPMUDClasses( mongo_db ):
    '''Return a set of PolymorphicMongoUserDict classes configured for a per-test-class unique collection'''

    class MyPolymorphicMongoUserDictBase( mongo_objects.PolymorphicMongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db

    class MyPolymorphicMongoUserDictA( MyPolymorphicMongoUserDictBase ):
        subclass_key = 'A'

    class MyPolymorphicMongoUserDictB( MyPolymorphicMongoUserDictBase ):
        subclass_key = 'B'

    class MyPolymorphicMongoUserDictC( MyPolymorphicMongoUserDictBase ):
        subclass_key = 'C'

    return {
        'base' : MyPolymorphicMongoUserDictBase,
        'A' : MyPolymorphicMongoUserDictA,
        'B' : MyPolymorphicMongoUserDictB,
        'C' : MyPolymorphicMongoUserDictC
    }



@pytest.fixture( scope='class' )
def getPopulatedMPMUDClasses( getMPMUDClasses, sampleData ):

    classes = getMPMUDClasses

    # for each entry in the sampleData, save it as a separate polymorphic class
    a = classes['A']( sampleData[0] )
    a.save()
    b = classes['B']( sampleData[1] )
    b.save()
    c = classes['C']( sampleData[2] )
    c.save()

    return classes



class TestInitSubclass:
    '''Test __init_subclass__ permutations'''

    def test_init_subclass( self ):
        class MyTestClassBase( mongo_objects.PolymorphicMongoUserDict ):
            # create our own local testing namespace
            subclass_map = {}

        class MyTestSubclassA( MyTestClassBase ):
            subclass_key = 'A'

        class MyTestSubclassB( MyTestClassBase ):
            subclass_key = 'B'

        class MyTestSubclassC( MyTestClassBase ):
            pass

        # Verify that classes A and B were added to the map
        # Class C should be skipped because it doesn't have a non-None subclass_key
        assert MyTestClassBase.subclass_map == {
            'A' : MyTestSubclassA,
            'B' : MyTestSubclassB
        }

        # verify our local subclass map namespace didn't affect the module base class map
        assert len( mongo_objects.PolymorphicMongoUserDict.subclass_map ) == 0


    def test_init_subclass_duplicate_key( self ):
        with pytest.raises( mongo_objects.MongoObjectsSubclassError ):

            class MyTestClassBase( mongo_objects.PolymorphicMongoUserDict ):
                # create our own local testing namespace
                subclass_map = {}

            class MyTestSubclassA( MyTestClassBase ):
                subclass_key = 'A'

            class MyTestSubclassAnotherA( MyTestClassBase ):
                subclass_key = 'A'



class TestPolymorphicBasics:
    def test_subclass_map( self , getPopulatedMPMUDClasses ):
        '''getMPMUDClasses doesn't create a new subclass_map namespace
        Verify that our base class and the module base class subclass_maps are the same'''
        classes = getPopulatedMPMUDClasses
        assert len( classes['base'].subclass_map ) == 3
        assert classes['base'].subclass_map == mongo_objects.PolymorphicMongoUserDict.subclass_map


    def test_find_all( self, getPopulatedMPMUDClasses ):
        '''Verify all sample data are returned with the correct class'''
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find():
            # match the sample data to the expected classes
            if obj['name'] == 'record 1':
                assert obj['_sckey'] == 'A'
                assert isinstance( obj, classes['A'] )
            elif obj['name'] == 'record 2':
                assert obj['_sckey'] == 'B'
                assert isinstance( obj, classes['B'] )
            elif obj['name'] == 'record 3':
                assert obj['_sckey'] == 'C'
                assert isinstance( obj, classes['C'] )
            else:
                assert False, 'unexpected sample data subclass'
            # since no project or flag was set, objects should not be readonly
            assert obj.readonly is False


    def test_find_single( self, getPopulatedMPMUDClasses ):
        '''Verify a single matching record is returned with the correct class'''
        classes = getPopulatedMPMUDClasses
        result = list( classes['base'].find( { 'name' : 'record 1'} ) )
        assert len(result) == 1
        assert result[0]['_sckey'] == 'A'
        assert isinstance( result[0], classes['A'] )


    def test_find_none( self, getPopulatedMPMUDClasses ):
        '''Verify a non-matching filter produces an empty result'''
        classes = getPopulatedMPMUDClasses
        result = list( classes['base'].find( { 'not-a-match' : 'will not return data'} ) )
        assert len(result) == 0


    def test_find_projection_1( self, getPopulatedMPMUDClasses ):
        '''Verify "positive" projection works'''
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find( {}, { 'name' : True } ):
            assert '_id' in obj
            assert '_sckey' not in obj
            assert '_created' not in obj
            assert '_updated' not in obj
            assert 'name' in obj
            assert 'amount' not in obj
            assert obj.readonly is True


    def test_find_projection_2( self, getPopulatedMPMUDClasses ):
        '''Verify "positive" projection works while suppressing _id"'''
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find( {}, { '_id' : False, 'name' : True } ):
            assert '_id' not in obj
            assert '_sckey' not in obj
            assert '_created' not in obj
            assert '_updated' not in obj
            assert 'name' in obj
            assert 'amount' not in obj
            assert obj.readonly is True


    def test_find_projection_3( self, getPopulatedMPMUDClasses ):
        '''Verify "negative" projection works'''
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find( {}, { 'name' : False } ):
            assert '_id' in obj
            assert '_sckey' in obj
            assert '_created' in obj
            assert '_updated' in obj
            assert 'name' not in obj
            assert 'amount' in obj
            assert obj.readonly is True


    def test_find_projection_4( self, getPopulatedMPMUDClasses ):
        '''Verify "negative" projection works while suppressing _id'''
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find( {}, { '_id' : False, 'name' : False } ):
            assert '_id' not in obj
            assert '_sckey' in obj
            assert '_created' in obj
            assert '_updated' in obj
            assert 'name' not in obj
            assert 'amount' in obj
            assert obj.readonly is True


    def test_find_readonly( self, getPopulatedMPMUDClasses ):
        '''Verify find() readonly flag'''
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find( readonly=True ):
            assert obj.readonly is True


    def test_find_one( self, getPopulatedMPMUDClasses ):
        '''Verify a single sample document is returned with the correct class'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one()

        # match the sample data to the expected classes
        if obj['name'] == 'record 1':
            assert obj['_sckey'] == 'A'
            assert isinstance( obj, classes['A'] )
        elif obj['name'] == 'record 2':
            assert obj['_sckey'] == 'B'
            assert isinstance( obj, classes['B'] )
        elif obj['name'] == 'record 3':
            assert obj['_sckey'] == 'C'
            assert isinstance( obj, classes['C'] )
        else:
            assert False, 'unexpected sample data subclass'

        # since no project or flag was set, objects should not be readonly
        assert obj.readonly is False


    def test_find_one_match( self, getPopulatedMPMUDClasses ):
        '''Verify a single matching record is returned with the correct class'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( { 'name' : 'record 1'} )
        assert obj is not None
        assert obj['_sckey'] == 'A'
        assert isinstance( obj, classes['A'] )


    def test_find_one_none( self, getPopulatedMPMUDClasses ):
        '''Verify a non-matching filter produces a None result'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( { 'not-a-match' : 'will not return data'} )
        assert obj is None


    def test_find_one_none_custom_return( self, getPopulatedMPMUDClasses ):
        '''Verify a non-matching filter produces our custom "no_match" result'''
        classes = getPopulatedMPMUDClasses

        class EmptyResponse( object ):
            pass

        obj = classes['base'].find_one( { 'not-a-match' : 'will not return data'}, no_match=EmptyResponse() )

        assert isinstance( obj, EmptyResponse )


    def test_find_one_projection_1( self, getPopulatedMPMUDClasses ):
        '''Verify "positive" projection works'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( {}, { 'name' : True } )
        assert '_id' in obj
        assert '_sckey' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj
        assert 'name' in obj
        assert 'amount' not in obj
        assert obj.readonly is True


    def test_find_one_projection_2( self, getPopulatedMPMUDClasses ):
        '''Verify "positive" projection works while suppressing _id"'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( {}, { '_id' : False, 'name' : True } )
        assert '_id' not in obj
        assert '_sckey' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj
        assert 'name' in obj
        assert 'amount' not in obj
        assert obj.readonly is True


    def test_find_one_projection_3( self, getPopulatedMPMUDClasses ):
        '''Verify "negative" projection works'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( {}, { 'name' : False } )
        assert '_id' in obj
        assert '_sckey' in obj
        assert '_created' in obj
        assert '_updated' in obj
        assert 'name' not in obj
        assert 'amount' in obj
        assert obj.readonly is True


    def test_find_one_projection_4( self, getPopulatedMPMUDClasses ):
        '''Verify "negative" projection works while suppressing _id'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( {}, { '_id' : False, 'name' : False } )
        assert '_id' not in obj
        assert '_sckey' in obj
        assert '_created' in obj
        assert '_updated' in obj
        assert 'name' not in obj
        assert 'amount' in obj
        assert obj.readonly is True


    def test_find_one_readonly( self, getPopulatedMPMUDClasses ):
        '''Verify find_one() readonly flag'''
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( readonly=True )
        assert obj.readonly is True


    def test_instantiate( self, getPopulatedMPMUDClasses ):
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].instantiate( { '_sckey' : 'A' } )
        assert isinstance( obj, classes['A'] )
        assert obj.readonly is False


    def test_get_subclass_by_key( self, getMPMUDClasses ):
        classes = getMPMUDClasses
        assert classes['base'].get_subclass_by_key( 'A' ) == classes['A']


    def test_get_subclass_from_doc( self, getMPMUDClasses ):
        classes = getMPMUDClasses
        assert classes['base'].get_subclass_from_doc( { classes['base'].subclass_key_name : 'A' } ) == classes['A']


    def test_instantiate_readonly( self, getPopulatedMPMUDClasses ):
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].instantiate( { '_sckey' : 'B' }, readonly=True )
        assert isinstance( obj, classes['B'] )
        assert obj.readonly is True


    def test_load_proxy_by_id( self, getPopulatedMPMUDClasses ):
        '''Verify find_one() readonly flag'''
        classes = getPopulatedMPMUDClasses

        # loop through sample objects
        for source in classes['base'].find():

            # load the same object with an empty proxy tree
            result = classes['base'].load_proxy_by_id( source.id() )

            # verify that the type of the object is correct
            assert type(source) == type(result)

            # verify the objects are the same
            assert source == result

            # verify the object is readonly
            assert result.readonly is False


    def test_load_proxy_by_id( self, getPopulatedMPMUDClasses ):
        '''Verify find_one() readonly flag'''
        classes = getPopulatedMPMUDClasses

        # loop through sample objects
        for source in classes['base'].find():

            # load the same object with an empty proxy tree
            result = classes['base'].load_proxy_by_id( source.id(), readonly=True )

            # verify that the type of the object is correct
            assert type(source) == type(result)

            # verify the objects are the same
            assert source == result

            # verify the object is readonly
            assert result.readonly is True





