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
    """Return a set of PolymorphicMongoUserDict classes configured for a per-test-class unique collection"""

    class MyPolymorphicMongoUserDictBase( mongo_objects.PolymorphicMongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db
        subclass_map = {}

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



@pytest.fixture( scope='class' )
def getVersionedMPMUDClasses( mongo_db ):
    """Return a set of PolymorphicMongoUserDict classes configured for a per-test-class unique collection"""

    class MyPolymorphicMongoUserDictBase( mongo_objects.PolymorphicMongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db
        # set a separate subclass_map so these versioned classes don't interfere
        # with the other non-versioned equivalents with identical keys
        subclass_map = {}
        object_version = 1

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
def getVersionedPopulatedMPMUDClasses( getVersionedMPMUDClasses, sampleData ):
    """Like getPopulatedMPMUDClass except each document is saved
    with a different version number.
    """

    classes = getVersionedMPMUDClasses

    # for each entry in the sampleData, save it as a separate polymorphic class
    classes['base'].object_version = 1
    a = classes['A']( sampleData[0] )
    a.save()

    classes['base'].object_version = 2
    b = classes['B']( sampleData[1] )
    b.save()

    classes['base'].object_version = 3
    c = classes['C']( sampleData[2] )
    c.save()

    return classes




class TestVersioning:
    """Test how various methods perform with object versioning"""

    def test_find_all_current_version( self, getVersionedPopulatedMPMUDClasses ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # There should only be one document at the current version (the default query)
        result = list( classes['base'].find() )
        assert len( result ) == 1
        assert result[0]['_objver'] == classes['base'].object_version


    def test_find_all_specified_version( self, getVersionedPopulatedMPMUDClasses ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # There should only be one document at version 1
        result = list( classes['base'].find( object_version=1 ) )
        assert len( result ) == 1
        assert result[0]['_objver'] == 1


    def test_find_all_versioning_suppressed( self, getVersionedPopulatedMPMUDClasses, sampleData ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # All documents should be returned if object versioning is suppressed
        result = list( classes['base'].find( object_version=False ) )
        assert len( result ) == len( sampleData )


    def test_find_all_nonexistent_version( self, getVersionedPopulatedMPMUDClasses ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # Nothing should be returned at a non-existent version
        result = list( classes['base'].find( object_version=10000000 ) )
        assert len( result ) == 0


    def test_find_one_current_version( self, getVersionedPopulatedMPMUDClasses, sampleData ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # There should only be one document at the current version (the default query)
        matches = 0
        for doc in sampleData:
            filter = doc.copy()
            result = classes['base'].find_one( filter )
            if result is not None:
                assert result['_objver'] == classes['base'].object_version
                matches += 1

        assert matches == 1


    def test_find_one_specified_version( self, getVersionedPopulatedMPMUDClasses, sampleData ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # There should only be one document at version 1
        matches = 0
        for doc in sampleData:
            filter = doc.copy()
            result = classes['base'].find_one( filter, object_version=1 )
            if result is not None:
                assert result['_objver'] == 1
                matches += 1

        assert matches == 1


    def test_find_one_versioning_suppressed( self, getVersionedPopulatedMPMUDClasses, sampleData ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # Any document may be returned if object versioning is suppressed
        for doc in sampleData:
            filter = doc.copy()
            assert classes['base'].find_one( filter, object_version=False ) is not None


    def test_find_one_nonexistent_version( self, getVersionedPopulatedMPMUDClasses, sampleData ):
        classes = getVersionedPopulatedMPMUDClasses

        # verify there is a current object version
        assert classes['base'].object_version is not None

        # None should be returned at a non-existent version for any document
        for doc in sampleData:
            filter = doc.copy()
            assert classes['base'].find_one( filter, object_version=10000000 ) is None



class TestInitSubclass:
    """Test __init_subclass__ permutations"""

    def test_init_subclass( self ):
        class MyTestClassBase( mongo_objects.PolymorphicMongoUserDict ):
            # create our own local testing namespace
            subclass_map = {}

        class MyTestSubclassA( MyTestClassBase ):
            subclass_key = 'A'

        class MyTestSubclassB( MyTestClassBase ):
            subclass_key = 'B'

        class MyTestSubclassC( MyTestClassBase ):
            subclass_key = 'C'

        # Verify that all classes were added to the map
        assert MyTestClassBase.subclass_map == {
            None : MyTestClassBase,
            'A' : MyTestSubclassA,
            'B' : MyTestSubclassB,
            'C' : MyTestSubclassC
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
        """getMPMUDClasses creates a new subclass_map namespace
        Verify that our base class is separate from the module base class subclass_map"""
        classes = getPopulatedMPMUDClasses
        assert len( classes['base'].subclass_map ) == 4
        assert len( mongo_objects.PolymorphicMongoUserDict.subclass_map ) == 0


    def test_find_all( self, getPopulatedMPMUDClasses, sampleData ):
        """Verify all sample data are returned with the correct class"""
        classes = getPopulatedMPMUDClasses
        result = list( classes['base'].find() )

        # Make sure that all sample data documents were returned
        assert len(result) == len( sampleData)

        # match the sample data to the expected classes
        for obj in result:
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


    def test_find_all_subclass( self, getPopulatedMPMUDClasses ):
        """Verify all sample data are returned with the correct class"""
        classes = getPopulatedMPMUDClasses

        # Loop through the subclasses and make sure only that type is returned
        for subclass in ('A', 'B', 'C'):
            result = list( classes[subclass].find() )

            # There should be only one document with each subclass
            assert len(result) == 1

            # verify the object type
            assert result[0]['_sckey'] == subclass
            assert isinstance( result[0], classes[subclass] )


    def test_find_single( self, getPopulatedMPMUDClasses ):
        """Verify a single matching record is returned with the correct class"""
        classes = getPopulatedMPMUDClasses
        result = list( classes['base'].find( { 'name' : 'record 1'} ) )
        assert len(result) == 1
        assert result[0]['_sckey'] == 'A'
        assert isinstance( result[0], classes['A'] )


    def test_find_one_subclass( self, getPopulatedMPMUDClasses ):
        """Verify all sample data are returned with the correct class"""
        classes = getPopulatedMPMUDClasses

        # Build a map of subclasses and objectIds
        docSubclassMap = {
            x['_sckey'] : str( x['_id'] )
            for x in classes['base'].find()
        }

        # Loop through the subclasses and make sure that searching
        # for a known object of the correct subclass produces a result
        for (docClass, docId) in docSubclassMap.items():
            result = classes[docClass].find_one( { '_id' : ObjectId( docId ) } )

            # A document should be found for each subclass
            assert result is not None

            # verify the object type
            assert result['_sckey'] == docClass
            assert isinstance( result, classes[docClass] )


    def test_find_one_subclass_mismatch( self, getPopulatedMPMUDClasses ):
        """Verify all sample data are returned with the correct class"""
        classes = getPopulatedMPMUDClasses

        # Build a map of subclasses and objectIds
        docSubclassMap = {
            x['_sckey'] : str( x['_id'] )
            for x in classes['base'].find()
        }

        # Make sure that searching for an existing object with the wrong class
        # returns None
        for (docClass, docId) in docSubclassMap.items():
            for subclass in ('A', 'B', 'C'):
                # Only search with classes other than the current document's subclass
                if subclass == docClass:
                    continue
                # Searching with the wrong class must return none
                assert classes[subclass].find_one( { '_id' : ObjectId( docId ) } ) is None


    def test_find_none( self, getPopulatedMPMUDClasses ):
        """Verify a non-matching filter produces an empty result"""
        classes = getPopulatedMPMUDClasses
        result = list( classes['base'].find( { 'not-a-match' : 'will not return data'} ) )
        assert len(result) == 0


    def test_find_projection_1( self, getPopulatedMPMUDClasses ):
        """Verify "positive" projection works"""
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
        """Verify "positive" projection works while suppressing _id"""
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
        """Verify "negative" projection works"""
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
        """Verify "negative" projection works while suppressing _id"""
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
        """Verify find() readonly flag"""
        classes = getPopulatedMPMUDClasses
        for obj in classes['base'].find( readonly=True ):
            assert obj.readonly is True


    def test_find_one( self, getPopulatedMPMUDClasses ):
        """Verify a single sample document is returned with the correct class"""
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
        """Verify a single matching record is returned with the correct class"""
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( { 'name' : 'record 1'} )
        assert obj is not None
        assert obj['_sckey'] == 'A'
        assert isinstance( obj, classes['A'] )


    def test_find_one_none( self, getPopulatedMPMUDClasses ):
        """Verify a non-matching filter produces a None result"""
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].find_one( { 'not-a-match' : 'will not return data'} )
        assert obj is None


    def test_find_one_none_custom_return( self, getPopulatedMPMUDClasses ):
        """Verify a non-matching filter produces our custom "no_match" result"""
        classes = getPopulatedMPMUDClasses

        class EmptyResponse( object ):
            pass

        obj = classes['base'].find_one( { 'not-a-match' : 'will not return data'}, no_match=EmptyResponse() )

        assert isinstance( obj, EmptyResponse )


    def test_find_one_projection_1( self, getPopulatedMPMUDClasses ):
        """Verify "positive" projection works"""
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
        """Verify "positive" projection works while suppressing _id"""
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
        """Verify "negative" projection works"""
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
        """Verify "negative" projection works while suppressing _id"""
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
        """Verify find_one() readonly flag"""
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

        # Check the map from the base class
        assert classes['base'].get_subclass_by_key( 'base' ) == classes['base']
        assert classes['base'].get_subclass_by_key( 'A' ) == classes['A']
        assert classes['base'].get_subclass_by_key( 'B' ) == classes['B']
        assert classes['base'].get_subclass_by_key( 'C' ) == classes['C']

        # In the default classes, the base doc class has None
        # as a subclass key and so is the default for all unknown
        # subclass keys
        assert classes['base'].get_subclass_by_key( 'D' ) == classes['base']


    def test_get_subclass_by_key_from_subclass( self, getMPMUDClasses ):
        classes = getMPMUDClasses

        # Check the map from the base class
        assert classes['A'].get_subclass_by_key( 'base' ) == classes['base']
        assert classes['A'].get_subclass_by_key( 'A' ) == classes['A']
        assert classes['A'].get_subclass_by_key( 'B' ) == classes['B']
        assert classes['A'].get_subclass_by_key( 'C' ) == classes['C']

        # In the default classes, the base doc class has None
        # as a subclass key and so is the default for all unknown
        # subclass keys
        assert classes['A'].get_subclass_by_key( 'D' ) == classes['base']


    def test_get_subclass_by_key_no_default( self ):
        class LocalPMUDBase( mongo_objects.PolymorphicMongoUserDict ):
            subclass_key = 'base'

        class LocalPMUDA( LocalPMUDBase ):
            subclass_key = 'A'

        class LocalPMUDB( LocalPMUDBase ):
            subclass_key = 'B'

        class LocalPMUDC( LocalPMUDBase ):
            subclass_key = 'C'

        assert LocalPMUDBase.get_subclass_by_key( 'base' ) == LocalPMUDBase
        assert LocalPMUDBase.get_subclass_by_key( 'A' ) == LocalPMUDA
        assert LocalPMUDBase.get_subclass_by_key( 'B' ) == LocalPMUDB
        assert LocalPMUDBase.get_subclass_by_key( 'C' ) == LocalPMUDC

        # There is no default class (no class with a None subclass_key)
        # so unknown subclass keys will raise an exception
        with pytest.raises( mongo_objects.MongoObjectsPolymorphicMismatch ):
            LocalPMUDBase.get_subclass_by_key( 'D' )

        # Also check the return from a subclass
        assert LocalPMUDA.get_subclass_by_key( 'base' ) == LocalPMUDBase
        assert LocalPMUDA.get_subclass_by_key( 'A' ) == LocalPMUDA
        assert LocalPMUDA.get_subclass_by_key( 'B' ) == LocalPMUDB
        assert LocalPMUDA.get_subclass_by_key( 'C' ) == LocalPMUDC

        # There is no default class (no class with a None subclass_key)
        # so unknown subclass keys will raise an exception
        with pytest.raises( mongo_objects.MongoObjectsPolymorphicMismatch ):
            LocalPMUDA.get_subclass_by_key( 'D' )


    def test_get_subclass_from_doc( self, getMPMUDClasses ):
        classes = getMPMUDClasses
        assert classes['base'].get_subclass_from_doc( { classes['base'].subclass_key_name : 'A' } ) == classes['A']


    def test_instantiate_readonly( self, getPopulatedMPMUDClasses ):
        classes = getPopulatedMPMUDClasses
        obj = classes['base'].instantiate( { '_sckey' : 'B' }, readonly=True )
        assert isinstance( obj, classes['B'] )
        assert obj.readonly is True


    def test_load_by_id( self, getPopulatedMPMUDClasses ):
        """Verify data and type from load_by_id()"""
        classes = getPopulatedMPMUDClasses

        # loop through sample objects
        for source in classes['base'].find():

            # load the same object by its ID
            result = classes['base'].load_by_id( source.id() )

            # verify that the type of the object is correct
            assert type(source) == type(result)

            # verify the objects are the same
            assert source == result

            # verify the object is not readonly
            assert result.readonly is False


    def test_load_by_id_readonly( self, getPopulatedMPMUDClasses ):
        """Verify readonly flag for load_by_id()"""
        classes = getPopulatedMPMUDClasses

        # loop through sample objects
        for source in classes['base'].find():

            # load the same object by its ID
            result = classes['base'].load_by_id( source.id(), readonly=True )

            # verify that the type of the object is correct
            assert type(source) == type(result)

            # verify the objects are the same
            assert source == result

            # verify the object is readonly
            assert result.readonly is True





