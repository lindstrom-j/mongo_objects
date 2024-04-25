# test_proxy_combo
#
# All other unit testing of proxies-within-proxies
# has used the same proxy type (dict within dict, list within list, etc)
#
# This module tests whether each of the three proxy types
# functions correctly as a subproxy of the other two types

from bson import ObjectId
from datetime import datetime
import mongo_objects
from pymongo.collection import Collection
import pytest
import secrets


@pytest.fixture( scope='class' )
def getMMUDBaseClass( mongo_db ):
    '''Return a MongoUserDict configured for a per-class unique collection'''

    class MyMongoUserDict( mongo_objects.MongoUserDict ):
        collection_name = secrets.token_hex(6)
        database = mongo_db

    return MyMongoUserDict


class TestDictAsPrimary:
    def test_dict_proxy_as_primary( self, getMMUDBaseClass ):
        itemMax = 3     # make three of everything

        # create one class of each proxy type
        class MyMongoDictProxyA( mongo_objects.MongoDictProxy ):
            container_name = 'proxyA'

        class MyMongoListProxyA1( mongo_objects.MongoListProxy ):
            container_name = 'proxyA1'

        class MyMongoSingleProxyA2( mongo_objects.MongoSingleProxy ):
            container_name = 'proxyA2'

        # create an empty object
        obj = getMMUDBaseClass()

        # populate three first-level dict proxies with
        # second-level list and single proxy objects
        for i in range( itemMax ):
            proxyA = MyMongoDictProxyA.create(
                obj,
                { 'name' : f"proxyA-{i}" },
                autosave=False
            )

            for j in range( itemMax ):
                proxyA1 = MyMongoListProxyA1.create(
                    proxyA,
                    { 'name' : f"proxyA1-{j}" },
                    autosave=False
                )

            # create only one single proxy object
            proxyA2 = MyMongoSingleProxyA2.create(
                proxyA,
                { 'name' : f"proxyA2" },
            )

        # save the original object
        obj.save()

        # reload the data from the database into a new object
        obj2 = getMMUDBaseClass.load_by_id( obj['_id'] )

        # check that all first-level proxy entries are present
        assert sorted( [ x['name'] for x in MyMongoDictProxyA.get_proxies( obj2 ) ] ) == \
                [ 'proxyA-0', 'proxyA-1', 'proxyA-2' ]

        # loop through each first-level proxy and check the second-level entries
        for proxyA in MyMongoDictProxyA.get_proxies( obj2 ):
            assert sorted( [ x['name'] for x in MyMongoListProxyA1.get_proxies( proxyA ) ] ) == \
                    [ 'proxyA1-0', 'proxyA1-1', 'proxyA1-2' ]
            assert MyMongoSingleProxyA2.get_proxy( proxyA )['name'] == "proxyA2"



class TestListAsPrimary:
    def test_list_proxy_as_primary( self, getMMUDBaseClass ):
        itemMax = 3     # make three of everything

        # create one class of each proxy type
        class MyMongoListProxyA( mongo_objects.MongoListProxy ):
            container_name = 'proxyA'

        class MyMongoDictProxyA1( mongo_objects.MongoDictProxy ):
            container_name = 'proxyA1'

        class MyMongoSingleProxyA2( mongo_objects.MongoSingleProxy ):
            container_name = 'proxyA2'

        # create an empty object
        obj = getMMUDBaseClass()

        # populate three first-level list proxies with
        # second-level dict and single proxy objects
        for i in range( itemMax ):
            proxyA = MyMongoListProxyA.create(
                obj,
                { 'name' : f"proxyA-{i}" },
                autosave=False
            )

            for j in range( itemMax ):
                proxyA1 = MyMongoDictProxyA1.create(
                    proxyA,
                    { 'name' : f"proxyA1-{j}" },
                    autosave=False
                )

            # create only one single proxy object
            proxyA2 = MyMongoSingleProxyA2.create(
                proxyA,
                { 'name' : f"proxyA2" },
            )

        # save the original object
        obj.save()

        # reload the data from the database into a new object
        obj2 = getMMUDBaseClass.load_by_id( obj['_id'] )

        # check that all first-level proxy entries are present
        assert sorted( [ x['name'] for x in MyMongoListProxyA.get_proxies( obj2 ) ] ) == \
                [ 'proxyA-0', 'proxyA-1', 'proxyA-2' ]

        # loop through each first-level proxy and check the second-level entries
        for proxyA in MyMongoListProxyA.get_proxies( obj2 ):
            assert sorted( [ x['name'] for x in MyMongoDictProxyA1.get_proxies( proxyA ) ] ) == \
                    [ 'proxyA1-0', 'proxyA1-1', 'proxyA1-2' ]
            assert MyMongoSingleProxyA2.get_proxy( proxyA )['name'] == "proxyA2"



class TestSingleAsPrimary:
    def test_dict_proxy_as_primary( self, getMMUDBaseClass ):
        itemMax = 3     # make three of everything

        # create one class of each proxy type
        class MyMongoSingleProxyA( mongo_objects.MongoSingleProxy ):
            container_name = 'proxyA2'

        class MyMongoDictProxyA1( mongo_objects.MongoDictProxy ):
            container_name = 'proxyA1'

        class MyMongoListProxyA2( mongo_objects.MongoListProxy ):
            container_name = 'proxyA2'


        # create an empty object
        obj = getMMUDBaseClass()

        # create only one single proxy object
        proxyA = MyMongoSingleProxyA.create(
            obj,
            { 'name' : f"proxyA" },
        )

        # populate the first-level proxy with
        # second-level dict and list objects
        for i in range( itemMax ):
            proxyA1 = MyMongoDictProxyA1.create(
                proxyA,
                { 'name' : f"proxyA1-{i}" },
                autosave=False
            )

            proxyA2 = MyMongoListProxyA2.create(
                proxyA,
                { 'name' : f"proxyA2-{i}" },
                autosave=False
            )
        # save the original object
        obj.save()

        # reload the data from the database into a new object
        obj2 = getMMUDBaseClass.load_by_id( obj['_id'] )

        # check that the first-level proxy entry is present
        proxyA = MyMongoSingleProxyA.get_proxy( obj2 )
        assert proxyA['name'] == "proxyA"

        # loop check the second-level entries
        assert sorted( [ x['name'] for x in MyMongoDictProxyA1.get_proxies( proxyA ) ] ) == \
                [ 'proxyA1-0', 'proxyA1-1', 'proxyA1-2' ]
        assert sorted( [ x['name'] for x in MyMongoListProxyA2.get_proxies( proxyA ) ] ) == \
                [ 'proxyA2-0', 'proxyA2-1', 'proxyA2-2' ]



