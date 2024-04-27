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
def getMMUDClass( mongo_db ):
    '''Return a MongoUserDict configured for a per-class unique collection'''

    class MyMongoUserDict( mongo_objects.MongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db

    return MyMongoUserDict



@pytest.fixture( scope='class' )
def getPopulatedMMUDClass( getMMUDClass, sampleData ):

    MMUD = getMMUDClass

    # for each entry in the sampleData, save it to the collection configured in MMUD
    for x in sampleData:
        obj = MMUD(x)
        obj.save()
    return MMUD



@pytest.fixture( scope='class' )
def getVersionedPopulatedMMUDClass( getMMUDClass, sampleData ):
    '''Like getPopulatedMMUDClass except each document is saved
    with a different version number.

    MMUD is left with the final object version number.'''

    MMUD = getMMUDClass

    # for each entry in the sampleData, save it to the collection configured in MMUD
    for (ver, x) in enumerate( sampleData ):
        MMUD.object_version = ver+1
        obj = MMUD(x)
        obj.save()
    return MMUD



class TestVersioning:
    '''Test how various function perform with object versioning'''

    def test_find_all_current_version( self, getVersionedPopulatedMMUDClass ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # There should only be one document at the current version (the default query)
        result = list( MMUD.find() )
        assert len( result ) == 1
        assert result[0]['_objver'] == MMUD.object_version


    def test_find_all_specified_version( self, getVersionedPopulatedMMUDClass ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # There should only be one document at version 1
        result = list( MMUD.find( object_version=1 ) )
        assert len( result ) == 1
        assert result[0]['_objver'] == 1


    def test_find_all_versioning_suppressed( self, getVersionedPopulatedMMUDClass, sampleData ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # All documents should be returned if object versioning is suppressed
        result = list( MMUD.find( object_version=False ) )
        assert len( result ) == len( sampleData )


    def test_find_all_nonexistent_version( self, getVersionedPopulatedMMUDClass ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # Nothing should be returned at a non-existent version
        result = list( MMUD.find( object_version=10000000 ) )
        assert len( result ) == 0


    def test_find_one_current_version( self, getVersionedPopulatedMMUDClass, sampleData ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # There should only be one document at the current version (the default query)
        matches = 0
        for doc in sampleData:
            filter = dict( doc )
            result = MMUD.find_one( filter )
            if result is not None:
                assert result['_objver'] == MMUD.object_version
                matches += 1

        assert matches == 1


    def test_find_one_specified_version( self, getVersionedPopulatedMMUDClass, sampleData ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # There should only be one document at version 1
        matches = 0
        for doc in sampleData:
            filter = dict( doc )
            result = MMUD.find_one( filter, object_version=1 )
            if result is not None:
                assert result['_objver'] == 1
                matches += 1

        assert matches == 1


    def test_find_one_versioning_suppressed( self, getVersionedPopulatedMMUDClass, sampleData ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # Any document may be returned if object versioning is suppressed
        for doc in sampleData:
            filter = dict( doc )
            assert MMUD.find_one( filter, object_version=False ) is not None


    def test_find_one_nonexistent_version( self, getVersionedPopulatedMMUDClass, sampleData ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # None should be returned at a non-existent version for any document
        for doc in sampleData:
            filter = dict( doc )
            assert MMUD.find_one( filter, object_version=10000000 ) is None



class TestVersionedSave:

    def test_save_version( self, getVersionedPopulatedMMUDClass ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # Create an empty object
        obj = MMUD( {} )
        assert '_objver' not in obj

        # save the object and verify the version was added to the document
        obj.save()
        assert obj['_objver'] == MMUD.object_version

        # load the data from the database and check the version
        obj2 = MMUD.load_by_id( obj.id() )
        assert obj2['_objver'] == MMUD.object_version



class TestVersionedSaveException:

    def test_save_version_exception( self, getVersionedPopulatedMMUDClass ):
        MMUD = getVersionedPopulatedMMUDClass

        # verify there is a current object version
        assert MMUD.object_version is not None

        # Create an invalid object; BSON dictionary keys must be strings
        obj = MMUD( { 1 : "not valid BSON"} )
        assert '_objver' not in obj

        # saving the object will raise an exception
        with pytest.raises( Exception ):
            obj.save()

        # verify that the object version was removed during rollback
        assert '_objver' not in obj



class TestSave:
    '''Test various permutations of MongoUserDict.save()
    Other functionality is tested in a separate class'''

    def test_save( self, getMMUDClass, sampleData ):
        '''Verify a basic dictionary is saved properly.
        Confirm original object is updated with time and ID
        and that data is stored as expected in the database.
        '''

        MMUD = getMMUDClass

        # count documents
        assert MMUD.collection().count_documents( {} ) == 0

        # record the current time
        startTime = MMUD.utcnow()

        # save the first record
        obj = MMUD( sampleData[0] )
        obj.save()

        # verify a record was saved
        assert MMUD.collection().count_documents( {} ) == 1

        # verify that ID was added to original object
        assert '_id' in obj
        assert isinstance( obj['_id'], ObjectId )

        # verify that _created timestamp was added to original document
        # timestamp microseconds should be set to 0
        # time should be later than the start of this test (disregarding microseconds)
        assert '_created' in obj
        assert isinstance( obj['_created'], datetime )
        assert obj['_created'].microsecond % 1000 == 0
        assert obj['_created'].replace(microsecond=0) >= startTime.replace(microsecond=0)

        # verify that _updated was also added and matches _created
        assert '_updated' in obj
        assert isinstance( obj['_updated'], datetime )
        assert obj['_created'] == obj['_updated']

        # save the document again and confirm _updated changes but _created doesn't
        original = dict( obj )
        obj.save()
        assert obj['_created'] == original['_created']
        assert obj['_updated'] > original['_updated']

        # find document directly from database driver
        doc = MMUD.collection().find_one( { '_id' : obj['_id'] } )

        # make sure the database object as the exact same data as the in-memory object
        assert len( set( obj.keys() ).symmetric_difference( doc.keys() ) ) == 0, "missing keys"
        for key in obj.keys():
            assert doc[key] == obj[key]


    def test_save_exception_1( self, getMMUDClass ):
        '''Test that an exception saving a new document removes _created, _updated timestamps'''
        MMUD = getMMUDClass

        # count documents
        count =  MMUD.collection().count_documents( {} )

        # Create an empty document
        obj = MMUD()
        assert '_created' not in obj
        assert '_updated' not in obj
        assert '_objver' not in obj

        # Create an exception
        # MongoDB keys must be strings, so use an integer to create the exception
        obj[1] = "This document can't be saved."

        # Raise the exception
        with pytest.raises( Exception ):
            obj.save()

        # verify that nothing was saved
        assert MMUD.collection().count_documents( {} ) == count

        # verify that _created and _updated were removed; _objver won't have been added anyway
        assert '_created' not in obj
        assert '_updated' not in obj
        assert '_objver' not in obj


    def test_save_exception_2( self, getMMUDClass ):
        '''Test that an exception saving a previously saved document leaves the _updated timestamp unchanged'''
        MMUD = getMMUDClass

        # count documents
        count = MMUD.collection().count_documents( {} )

        # save an empty document
        obj = MMUD()
        obj.save()
        original = dict( obj )

        # verify that the object was saved
        assert MMUD.collection().count_documents( {} ) == count + 1

        # Confirm _id, _created and _updated are all set
        assert '_id' in obj
        assert '_created' in obj
        assert '_updated' in obj

        # Create an exception
        # MongoDB keys must be strings, so use an integer to create the exception
        obj[1] = "This document can't be saved."

        # Raise the exception
        with pytest.raises( Exception ):
            obj.save()

        # verify the document count hasn't changed
        assert MMUD.collection().count_documents( {} ) == count + 1

        # verify that _created and _updated exist and weren't changed
        assert obj['_created'] == original['_created']
        assert obj['_updated'] == original['_updated']

        # find document directly from database driver
        doc = MMUD.collection().find_one( { '_id' : obj['_id'] } )

        # verify database object _created and _updated timestamp
        assert doc['_created'] == obj['_created']
        assert doc['_updated'] == obj['_updated']


    def test_save_force( self, getMMUDClass, sampleData ):
        MMUD = getMMUDClass

        # count documents
        count =  MMUD.collection().count_documents( {} )

        # record the current time
        startTime = MMUD.utcnow()

        # manually assign an ObjectId
        # any object with an _id is assumed to have been saved already
        # and to have a valid _updated timestamp
        obj = MMUD( sampleData[1] )
        obj['_id'] = ObjectId()

        # saving it should raise an exception as no existing object can be found
        # in this case _updated starts as None but it could be anything
        original_updated = obj.get('_updated')
        with pytest.raises( Exception ):
            obj.save()

        # verify that nothing was saved
        assert MMUD.collection().count_documents( {} ) == count

        # verify that _updated wasn't changed
        assert obj.get('_updated') == original_updated

        # force saving will work
        obj.save( force=True )

        # verify that something was saved
        assert MMUD.collection().count_documents( {} ) == count+1

        # verify that timestamp has been updated
        assert obj['_updated'] >= startTime

        # find document directly from database driver
        doc = MMUD.collection().find_one( { '_id' : obj['_id'] } )

        # verify database object _updated timestamp
        assert doc['_updated'] == obj['_updated']


    def test_save_overwrite( self, getMMUDClass, sampleData ):
        '''Test attempting to save over an already-updated object'''
        MMUD = getMMUDClass

        # count documents
        count =  MMUD.collection().count_documents( {} )

        # record the current time
        startTime = MMUD.utcnow()

        # save the third record
        obj = MMUD( sampleData[2] )
        obj.save()

        # reload the data into a new object
        obj2 = MMUD.load_by_id( obj.id() )

        # verify the timestamps are the same
        assert obj['_updated'] == obj2['_updated']

        # save the first object again
        obj.save()

        # verify a newer timestamp
        assert obj['_updated'] > obj2['_updated']

        # try to save second object; it won't work
        original_updated = obj2.get('_updated')
        with pytest.raises( mongo_objects.MongoObjectsDocumentModified ):
            obj2.save()

        # verify that obj2 _updated is the original value
        assert obj2.get('_updated') == original_updated

        # locate object on disk and verify _updated matches obj (not obj2)
        doc = MMUD.collection().find_one( { '_id' : obj['_id'] } )
        assert doc['_updated'] == obj['_updated']


    def test_save_readonly( self, getPopulatedMMUDClass ):
        '''Test attempting to save a readonly object'''
        MMUD = getPopulatedMMUDClass
        result = MMUD.find_one( readonly=True )
        assert result.readonly is True

        # saving a readonly document produces an exception
        with pytest.raises( mongo_objects.MongoObjectsReadOnly ):
            result.save()


    def test_save_no_auth( self, getPopulatedMMUDClass ):
        '''Test attempting to save a document without authorization'''
        class LocalMMUD( getPopulatedMMUDClass):
            def authorize_save( self ):
                return False

        obj = LocalMMUD.find_one()
        original = dict( obj )

        # verify saving a document without authorization produces an exception
        with pytest.raises( mongo_objects.MongoObjectsAuthFailed ):
            obj.save()

        # verify nothing was saved
        assert obj['_updated'] == original['_updated']




class TestDelete:
    '''Test MongoUserDict.delete() in its own database'''

    def test_delete( self, getMMUDClass, sampleData ):
        MMUD = getMMUDClass

        # save the first record
        obj = MMUD( sampleData[0] )
        obj.save()

        # verify a record was saved
        assert MMUD.collection().count_documents( {} ) == 1

        # delete the object
        obj.delete()

        # verify that the ID has been removed from the memory object
        assert '_id' not in obj

        # verify a record was removed and the database is empty
        assert MMUD.collection().count_documents( {} ) == 0


    def test_delete_new( self, getMMUDClass, sampleData ):
        '''Delete an object that was never saved. This should be a no-op'''
        MMUD = getMMUDClass

        # create but don't save the first record
        obj = MMUD( sampleData[0] )

        # verify that no _id is present
        assert '_id' not in obj

        # note the number of documents in the database
        count = MMUD.collection().count_documents( {} )

        # delete the object
        obj.delete()

        # verify the database document count hasn't changed
        assert count == MMUD.collection().count_documents( {} )


    def test_delete_no_auth( self, getPopulatedMMUDClass ):
        '''Test attempting to delete a document without authorization'''
        class LocalMMUD( getPopulatedMMUDClass):
            def authorize_delete( self ):
                return False

        obj = LocalMMUD.find_one()

        # note the number of documents in the database
        count = LocalMMUD.collection().count_documents( {} )

        # verify deleting a document without authorization produces an exception
        with pytest.raises( mongo_objects.MongoObjectsAuthFailed ):
            obj.delete()

        # verify the database document count hasn't changed
        assert count == LocalMMUD.collection().count_documents( {} )




class TestBasics:
    '''Test all other functionality of MongoUserDict'''

    def test_init( self, getMMUDClass, sampleData ):
        MMUD = getMMUDClass
        obj = MMUD( sampleData[0] )
        assert obj.data == sampleData[0]
        assert obj.readonly is False


    def test_init_empty( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD()
        assert len(obj.data) == 0
        assert obj.readonly is False


    def test_init_readonly( self, getMMUDClass, sampleData ):
        MMUD = getMMUDClass
        obj = MMUD( sampleData[0], readonly=True )
        assert obj.data == sampleData[0]
        assert obj.readonly is True


    def test_init_empty_readonly( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD(readonly=True)
        assert len(obj.data) == 0
        assert obj.readonly is True


    def test_init_no_auth( self, getMMUDClass, sampleData ):
        class LocalMMUD( getMMUDClass):
            def authorize_init( self ):
                return False

        # verify initializing a document without authorization produces an exception
        with pytest.raises( mongo_objects.MongoObjectsAuthFailed ):
            obj = LocalMMUD( sampleData[0] )


    def test_add_object_version( self ):
        '''Verify add_object_version adds the correct filter
        The original filter should be left intact.'''
        class LocalClass( mongo_objects.MongoUserDict ):
            object_version = 5

        # object_version = False never adds a filter
        filter = {}
        result = LocalClass.add_object_version_filter( filter, False )
        assert len(filter) == 0
        assert len(result) == 0

        # object_version = None adds a filter for the current object version
        filter = {}
        result = LocalClass.add_object_version_filter( filter, None )
        assert len(filter) == 0
        assert result == { '_objver' : 5 }

        # object_version = Value adds a filter for the current value
        # With no class object version, nothing will happen
        filter = {}
        result = LocalClass.add_object_version_filter( filter, 10 )
        assert len(filter) == 0
        assert result == { '_objver' : 10 }


    def test_add_object_version_empty( self ):
        '''Verify add_object_version() if the class has no object version
        Since the class has no object version, no filter should be
        added under any circumstances'''
        class LocalClass( mongo_objects.MongoUserDict ):
            pass

        # object_version = False never adds a filter
        filter = {}
        result = LocalClass.add_object_version_filter( filter, False )
        assert len(filter) == 0
        assert len(result) == 0

        # object_version = None adds a filter for the current object version
        # With no class object version, nothing will happen
        filter = {}
        result = LocalClass.add_object_version_filter( filter, None )
        assert len(filter) == 0
        assert len(result) == 0

        # object_version = Value adds a filter for the current value
        # With no class object version, nothing will happen
        filter = {}
        result = LocalClass.add_object_version_filter( filter, 10 )
        assert len(filter) == 0
        assert len(result) == 0


    def test_collection( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass
        assert isinstance( MMUD.collection(), Collection )


    def test_find_all( self, getPopulatedMMUDClass, sampleData ):
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = list( MMUD.find() )

        # verify that we found all the entries
        assert len( result ) == len( sampleData )
        assert len( result ) == MMUD.collection().count_documents( {} )

        # verify type and data present
        # since no projection was used and readonly wasn't True,
        # verify object is not marked readonly
        for x in result:
            assert isinstance( x, MMUD )
            assert '_id' in x
            assert '_created' in x
            assert '_updated' in x
            assert 'name' in x
            assert 'amount' in x
            assert x.readonly is False

        # verify all records found
        # All 'name' values from sampleData should also exist in the find() result
        assert len(
            set( [ x['name'] for x in result] ).symmetric_difference(
                 [ y['name'] for y in sampleData ] )
            ) == 0


    def test_find_none( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = list( MMUD.find( { 'not-a-field' : 'wont-match-anything' } ) )

        # verify that we found nothing
        assert len( result ) == 0


    def test_find_single( self, getPopulatedMMUDClass, sampleData ):
        '''Use a filter to find a single record, in this case, the first sample by name'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = list( MMUD.find( { 'name' : sampleData[0]['name'] } ) )

        # verify that we found a single entry
        assert len( result ) == 1

        # since no projection was used and readonly wasn't True,
        # verify object is not marked readonly
        assert result[0].readonly is False


    def test_find_projection_1( self, getPopulatedMMUDClass ):
        '''Test find() with a "positive" projection'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        for x in MMUD.find( {}, { 'amount' : True } ):
            assert '_id' in x
            assert '_created' not in x
            assert '_updated' not in x
            assert 'amount' in x
            assert 'name' not in x
            assert x.readonly is True


    def test_find_projection_2( self, getPopulatedMMUDClass ):
        '''Test find() with a "positive" projection but suppress _id'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        for x in MMUD.find( {}, { '_id' : False, 'name' : True } ):
            assert '_id' not in x
            assert '_created' not in x
            assert '_updated' not in x
            assert 'amount' not in x
            assert 'name' in x
            assert x.readonly is True


    def test_find_projection_3( self, getPopulatedMMUDClass ):
        '''Test find() with a "negative" projection'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        for x in MMUD.find( {}, { 'amount' : False } ):
            assert '_id' in x
            assert '_created' in x
            assert '_updated' in x
            assert 'amount' not in x
            assert 'name' in x
            assert x.readonly is True


    def test_find_projection_4( self, getPopulatedMMUDClass ):
        '''Test find() with a "negative" projection and suppress _id'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        for x in MMUD.find( {}, { '_id' : False, 'name' : False } ):
            assert '_id' not in x
            assert '_created' in x
            assert '_updated' in x
            assert 'amount' in x
            assert 'name' not in x
            assert x.readonly is True


    def test_find_projection_5( self, getPopulatedMMUDClass ):
        '''Test find() with a "negative" projection with readonly forced to False'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is not marked readonly
        for x in MMUD.find( {}, { '_id' : False, 'name' : False }, readonly=False ):
            assert '_id' not in x
            assert '_created' in x
            assert '_updated' in x
            assert 'amount' in x
            assert 'name' not in x
            assert x.readonly is False


    def test_find_readonly( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = list( MMUD.find( readonly=True ) )

        # verify all objects are marked readonly
        for x in result:
            assert x.readonly is True


    def test_find_no_pre_auth( self, getPopulatedMMUDClass ):
        '''Test attempting to read without pre-authorization'''
        class LocalMMUD( getPopulatedMMUDClass ):
            @classmethod
            def authorize_pre_read( cls ):
                return False

        # verify reading documents without pre-read authorization produces an exception
        # must convert to a list or the generator is never called
        with pytest.raises( mongo_objects.MongoObjectsAuthFailed ):
            list( LocalMMUD.find() )


    def test_find_no_auth_1( self, getPopulatedMMUDClass ):
        '''Test attempting to read without authorization'''
        class LocalMMUD( getPopulatedMMUDClass):
            def authorize_read( self ):
                return False

        # verify reading documents without read authorization produces an empty list
        result = LocalMMUD.find()
        assert len( list( result ) ) == 0


    def test_find_no_auth_2( self, getPopulatedMMUDClass ):
        '''Test attempting to read without authorization for certain objects'''

        # first collect a list of object IDs
        ids = [ x.id() for x in getPopulatedMMUDClass.find() ]

        # create a class authorized to read all but the first ID
        class LocalMMUD( getPopulatedMMUDClass):
            def authorize_read( self ):
                return self.id() != ids[0]

        # read all documents with the new custom class
        ids2 = [ x.id() for x in LocalMMUD.find() ]
        # construct a list of all ids missing from the second find() call
        diff = list( set(ids).difference( ids2 ) )
        # verify that only ids[0] is missing (the ID excluded by authorize_read() )
        assert len( diff ) == 1
        assert diff[0] == ids[0]


    def test_find_one( self, getPopulatedMMUDClass ):
        '''Test returning a single (random) object'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = MMUD.find_one()
        assert isinstance( result, MMUD )
        assert '_id' in result
        assert '_created' in result
        assert '_updated' in result
        assert 'amount' in result
        assert 'name' in result
        assert result.readonly is False


    def test_find_one_none( self, getPopulatedMMUDClass ):
        '''Verify a non-matching filter produces a None result'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = MMUD.find_one( { 'not-a-field' : 'wont-match-anything' } )

        # verify that we found nothing
        assert result is None


    def test_find_one_none_custom_return( self, getPopulatedMMUDClass ):
        '''Verify a non-matching filter produces our custom "no_match" result'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        class EmptyResponse( object ):
            pass

        result = MMUD.find_one( { 'not-a-field' : 'wont-match-anything' }, no_match=EmptyResponse() )

        assert isinstance( result, EmptyResponse )


    def test_find_one_filter( self, getPopulatedMMUDClass, sampleData ):
        '''Use a filter to find a specific single record, in this case, the third sample by name'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        result = MMUD.find_one( { 'name' : sampleData[2]['name'] } )

        # verify that we found the right record
        assert result['name'] == sampleData[2]['name']


    def test_find_one_projection_1( self, getPopulatedMMUDClass ):
        '''Test find() with a "positive" projection'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        result = MMUD.find_one( {}, { 'amount' : True } )
        assert '_id' in result
        assert '_created' not in result
        assert '_updated' not in result
        assert 'amount' in result
        assert 'name' not in result
        assert result.readonly is True


    def test_find_one_projection_2( self, getPopulatedMMUDClass ):
        '''Test find() with a "positive" projection but suppress _id'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        result = MMUD.find_one( {}, { '_id' : False, 'name' : True } )
        assert '_id' not in result
        assert '_created' not in result
        assert '_updated' not in result
        assert 'amount' not in result
        assert 'name' in result
        assert result.readonly is True


    def test_find_one_projection_3( self, getPopulatedMMUDClass ):
        '''Test find() with a "negative" projection'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        result = MMUD.find_one( {}, { 'amount' : False } )
        assert '_id' in result
        assert '_created' in result
        assert '_updated' in result
        assert 'amount' not in result
        assert 'name' in result
        assert result.readonly is True


    def test_find_one_projection_4( self, getPopulatedMMUDClass ):
        '''Test find() with a "negative" projection and suppress _id'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is marked readonly
        result = MMUD.find_one( {}, { '_id' : False, 'name' : False } )
        assert '_id' not in result
        assert '_created' in result
        assert '_updated' in result
        assert 'amount' in result
        assert 'name' not in result
        assert result.readonly is True


    def test_find_one_projection_5( self, getPopulatedMMUDClass ):
        '''Test find() with a "negative" projection with readonly forced to False'''
        MMUD = getPopulatedMMUDClass

        # verify that this is an unversioned test
        assert MMUD.object_version is None

        # Verify projection produced the proper key set
        # Also confirm object is not marked readonly
        result = MMUD.find_one( {}, { '_id' : False, 'name' : False }, readonly=False )
        assert '_id' not in result
        assert '_created' in result
        assert '_updated' in result
        assert 'amount' in result
        assert 'name' not in result
        assert result.readonly is False


    def test_find_one_readonly( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass
        result = MMUD.find_one( readonly=True )

        # verify object are marked readonly
        result.readonly is True


    def test_find_one_no_pre_auth( self, getPopulatedMMUDClass ):
        '''Test attempting to read without pre-authorization'''
        class LocalMMUD( getPopulatedMMUDClass ):
            @classmethod
            def authorize_pre_read( cls ):
                return False

        # verify reading a document without pre-read authorization produces an exception
        with pytest.raises( mongo_objects.MongoObjectsAuthFailed ):
            LocalMMUD.find_one()


    def test_find_one_no_auth( self, getPopulatedMMUDClass ):
        '''Test attempting to read without authorization'''
        class LocalMMUD( getPopulatedMMUDClass):
            def authorize_read( self ):
                return False

        # verify reading documents without read authorization produces an empty list
        result = LocalMMUD.find_one()
        assert result is None


    def test_get_unique_integer( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD()
        startTime = MMUD.utcnow()

        # verify new object doesn't have a _last_unique_integer
        # an _id, a created or an update time
        assert '_id' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj
        assert '_last_unique_integer' not in obj

        # obtain the next unique integer
        x = obj.get_unique_integer()
        assert x == 1
        assert x == obj['_last_unique_integer']

        # object should have been saved
        assert '_id' in obj
        assert obj['_created'] >= startTime
        assert obj['_updated'] == obj['_created']

        # get 10 more integers
        for i in range(10):
            x = obj.get_unique_integer()
        assert x == 11
        assert x == obj['_last_unique_integer']


    def test_get_unique_integer_no_save( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD()

        # verify new object doesn't have a _last_unique_integer
        # an _id, a created or an update time
        assert '_id' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj
        assert '_last_unique_integer' not in obj

        # obtain the next unique integer
        x = obj.get_unique_integer( autosave=False )
        assert x == 1
        assert x == obj['_last_unique_integer']

        # object should not have been saved
        assert '_id' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj


    def test_get_unique_integer_migration( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD( { '_lastUniqueInteger' : 10 } )

        # obtain the next unique integer
        x = obj.get_unique_integer( autosave=False )
        assert x == 11
        assert x == obj['_last_unique_integer']

        # verify that _lastUniqueInteger has been removed
        assert '_lastUniqueInteger' not in obj


    def test_get_unique_key( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD()
        startTime = MMUD.utcnow()

        # verify new object doesn't have a _last_unique_integer
        # an _id, or an update time
        assert '_id' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj
        assert '_last_unique_integer' not in obj

        # obtain the next unique key
        x = obj.get_unique_key()
        assert x == '1'
        assert x == str( obj['_last_unique_integer'] )

        # object should have been saved
        assert '_id' in obj
        assert obj['_created'] >= startTime
        assert obj['_updated'] == obj['_created']

        # get 10 more keys
        for i in range(10):
            x = obj.get_unique_key()
        assert x == 'b'   # 11 in hex
        assert x == f"{obj['_last_unique_integer']:x}"


    def test_get_unique_integer_no_save( self, getMMUDClass ):
        MMUD = getMMUDClass
        obj = MMUD()

        # verify new object doesn't have a _last_unique_integer
        # an _id, or an update time
        assert '_id' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj
        assert '_last_unique_integer' not in obj

        # obtain the next unique key
        x = obj.get_unique_key( autosave=False )
        assert x == '1'
        assert x == str(obj['_last_unique_integer'])

        # object should not have been saved
        assert '_id' not in obj
        assert '_created' not in obj
        assert '_updated' not in obj


    def test_id( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass
        result = MMUD.find_one()

        # id() is just the string version of the MongoDB _id value
        assert result.id() == str( result['_id'] )


    def test_id_new_object( self, getMMUDClass ):
        MMUD = getMMUDClass

        # new objects don't have an _id value yet
        # so id() will raise an exception
        obj = MMUD( {} )
        with pytest.raises( Exception ):
            obj.id()


    def test_load_by_id_bson( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # load a random object
        source = MMUD.find_one()

        # locate it again by the MongoDB BSON id
        result = MMUD.load_by_id( source['_id'] )

        # verify the objects are the same
        assert source == result

        # since no flag was used, verify the object is not readonly
        assert source.readonly is False


    def test_load_by_id_str( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # load a random object
        source = MMUD.find_one()

        # locate it again by the string id
        result = MMUD.load_by_id( source.id() )

        # verify the objects are the same
        assert source == result

        # since no flag was used, verify the object is not readonly
        assert result.readonly is False


    def test_load_by_id_readonly( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # load a random object
        source = MMUD.find_one()

        # locate it again by the string id
        result = MMUD.load_by_id( source.id(), readonly=True )

        # verify the objects are the same
        assert source == result

        # verify the object is readonly
        assert result.readonly is True


    def test_load_proxy_by_id( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # load a random object
        source = MMUD.find_one()

        # load the same object with an empty proxy tree
        result = MMUD.load_proxy_by_id( source.id() )

        # verify the objects are the same
        assert source == result

        # verify the object is readonly
        assert result.readonly is False


    def test_load_proxy_by_id_readonly( self, getPopulatedMMUDClass ):
        MMUD = getPopulatedMMUDClass

        # load a random object
        source = MMUD.find_one()

        # load the same object with an empty proxy tree
        result = MMUD.load_proxy_by_id( source.id(), readonly=True )

        # verify the objects are the same
        assert source == result

        # verify the object is readonly
        assert result.readonly is True


    def test_split_id( self, getMMUDClass ):
        MMUD = getMMUDClass

        # verify that the subdocument key separator exists
        assert hasattr( MMUD, 'subdoc_key_sep' )

        # construct a mock subdocument ID
        a = [ '123456', '78', '90']
        id = MMUD.subdoc_key_sep.join( a )

        # split the ID back into components
        assert MMUD.split_id( id ) == a


    def test_utcnow( self, getMMUDClass ):
        MMUD = getMMUDClass
        startTime = datetime.utcnow()
        mongoNow = MMUD.utcnow()
        endTime = datetime.utcnow()

        # verify that mongoNow has no microseconds
        assert mongoNow.microsecond % 1000 == 0

        # disregarding microseconds, verify mongoNow >= startTime
        assert mongoNow.replace(microsecond=0) >= startTime.replace(microsecond=0)

        # verify that mongoNow is less than endTime
        assert mongoNow < endTime
