# mongo_objects
#
# Wrap MongoDB documents in a UserDict subclass
# Optionally support polymorphic objects within the same collection
#
# Proxy requests for MongoDB subdocuments back to the parent document
#   single dictionary subdocuments
#   dictionary of subdocument dictionaries
#   list of subdocument dictionaries
# Optionally support polymorphic subdocuments within the same document
#
# Copyright 2024 Jonathan Lindstrom
# Headwaters Entrepreneurs Pte Ltd
# https://headwaters.com.sg
#
# Released under the MIT License

from bson import ObjectId
from collections import namedtuple, UserDict
from datetime import datetime
from pymongo.collection import ReturnDocument



################################################################################
# Custom exceptions
################################################################################

class MongoObjectsAuthFailed( Exception ):
    pass

class MongoObjectsDocumentModified( Exception ):
    pass

class MongoObjectsReadOnly( Exception ):
    pass

class MongoObjectsSubclassError( Exception ):
    pass


################################################################################
# MongoDB document wrappers
################################################################################


class MongoUserDict( UserDict ):
    # Subclasses can provide a collection name and a MongoDb database connection
    # as a class attribute OR override collection() to return the correct collection object
    collection_name = None
    database = None

    # If object_version is non-None, find() and find_one() by default restrict queries
    # to documents with the current object_version
    # This enables a type of schema versioning.
    object_version = None

    # The character sequence used to separate the document ID from proxy subdocument keys
    # This may be overriden but it is the user's responsibility to guarantee that this
    # sequence will never appear in any ID or subdoc key.
    # Since the default IDs and subdoc keys are hex, 'g' is a safe separator
    subdoc_key_sep = 'g'


    def __init__( self, doc={}, readonly=False ):
        '''Initialize the custom UserDict object
        Flag readonly objects appropriately'''
        super().__init__( doc )
        self.readonly = readonly

        # Authorize creating this object prior to returning to the user
        if not self.authorize_init():
            raise MongoObjectsAuthFailed


    @classmethod
    def add_object_version_filter( cls, filter, object_version ):
        '''Implement automatic object version filtering for find() and find_one().
        The object-version keyword argument affects if and how to implement
        object version filtering.'''
        if cls.object_version is not None:
            # False suppresses automatic object_version filtering
            if object_version is False:
                pass
            # None (the default) filters the query to the current class object version
            elif object_version is None:
                filter = dict(filter)
                filter['_objver'] = cls.object_version

            # Any other value filters object version to that value
            else:
                filter = dict(filter)
                filter['_objver'] = object_version
        return filter


    # Authorization hooks()
    # The user may call these hooks to authorize various CRUD operations
    def authorize_init( self ):
        '''Called after the document object is initialized but
        before it is returned to the user.
        If the return value is not truthy, a MongoObjectsAuthFailed exception
        is raised.'''
        return True

    def authorize_delete( self ):
        '''Called before the current document is deleted.
        If the return value is not truthy, a MongoObjectsAuthFailed
        exception is raised.'''
        return True

    @classmethod
    def authorize_pre_read( cls ):
        '''Called before a read operation is performed.
        This is a class method as no data has been read and no
        document object has been created.
        If the return value is not truthy, a MongoObjectsAuthFailed
        exception is raised.'''
        return True

    def authorize_read( self ):
        '''Called after a document has been read but before the
        data is returned to the user.
        If the return value is not truthy, the data will
        not be returned.

        Note that find_one() only inspects the first document
        returned by the underlying MongoDB find_one() call. If the
        document returned does not pass authorization, no attempt is
        made to locate another matching document.'''
        return True

    def authorize_save( self ):
        '''Called before the current document is saved.
        If the return value is not truthy, a MongoObjectsAuthFailed
        exception is raised.'''
        return True


    @classmethod
    def collection( cls ):
        '''Return the collection object from the active database for the named collection'''
        return cls.database.get_collection( cls.collection_name )


    def delete( self ):
        '''Delete the current object
        Remove the id so save() will know this is a new object if we try to re-save.'''
        if '_id' in self:
            # Authorize deleting this object
            if not self.authorize_delete():
                raise MongoObjectsAuthFailed
            self.collection().find_one_and_delete( { '_id' : ObjectId( self['_id'] ) } )
            del self['_id']


    @classmethod
    def find( cls, filter={}, projection=None, readonly=None, object_version=None, **kwargs ):
        '''Return matching documents as instances of this class'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectsAuthFailed

        # if readonly is None, by default force queries with a projection to be read-only
        # otherwise, accept the value provided by the user
        if readonly is None:
            readonly = projection is not None
        else:
            readonly = bool( readonly )

        # automatically filter by object version if requested
        if cls.object_version is not None:
            filter = cls.add_object_version_filter( filter, object_version )

        for doc in cls.collection().find( filter, projection, **kwargs ):
            obj = cls(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                yield obj


    @classmethod
    def find_one( cls, filter={}, projection=None, readonly=None, object_version=None, no_match=None, **kwargs ):
        '''Return a single matching document as an instance of this class or None'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectsAuthFailed

        # if readonly is None, by default force queries with a projection to be read-only
        # otherwise, accept the value provided by the user
        if readonly is None:
            readonly = projection is not None
        else:
            readonly = bool( readonly )

        # automatically filter by object version if requested
        if cls.object_version is not None:
            filter = cls.add_object_version_filter( filter, object_version )

        doc = cls.collection().find_one( filter, projection, **kwargs )
        if doc is not None:
            obj = cls(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                return obj
        return no_match


    def get_unique_integer( self, autosave=True ):
        '''Provide the next unique integer for this document.
        These integers are convenient for use as keys of subdocuments.
        Start with 1; 0 is reserved for single proxy documents which don't have a key.
        By default, the document is saved.'''

        # migrate existing _lastUniqueInteger objects to _last_unique_integer
        if '_lastUniqueInteger' in self:
            self['_last_unique_integer'] = self['_lastUniqueInteger']
            del self['_lastUniqueInteger']
        else:
            self.setdefault( '_last_unique_integer', 0 )
        self['_last_unique_integer'] += 1
        if autosave:
            self.save()
        return self['_last_unique_integer']


    def get_unique_key( self, autosave=True ):
        '''Format the next unique integer as a hexidecimal string'''
        return f"{self.get_unique_integer( autosave ):x}"


    def id( self ):
        '''Convert this document's database ID to a string'''
        return str( self['_id'] )


    @classmethod
    def load_by_id( cls, doc_id, **kwargs ):
        '''Locate a document by its database ID'''
        return cls.find_one( { '_id' : ObjectId( doc_id ) }, **kwargs )


    @classmethod
    def load_proxy_by_id( cls, id, *args, readonly=False ):
        '''Based on a subdocument ID and a list of classes, load the Mongo parent
        documents, create any intermediate proxies and return the requested
        proxy object.

        id is a subdocument ID string separated by subdoc_key_sep. It includes the
        ObjectId of the top-level MongoDB document

        args is a list of proxy objects in descending order. It does not include
        the top-level MongoUserDict class'''

        # split the subdocument_id into its components
        ids = cls.split_id( id )

        # load the MongoDB document and remove the ID from the list of ids
        obj = cls.load_by_id( ids.pop(0), readonly=readonly )

        # loop through each level of proxy using the previous object as the parent
        for (proxy_subclass, id) in zip( args, ids, strict=True ):
            obj = proxy_subclass.get_proxy( obj, id )

        # return the lowest-level object
        return obj



    def save( self, force=False ):
        '''Intelligent wrapper to insert or replace a document
        A current _updated timestamp is added to all documents.
        The first time a document is saved, a _created timestamp is added as well.
        1) Documents without an _id are inserted into the database; MongoDB will assign the ID
        2) If force is set, document will be saved regardless of update time or even if it exists.
           This is useful for upserting document from another database.
        3) Otherwise, only a document with this _id and _updated timestamp will be replaced.
           This protects against overwriting documents that have been updated elsewhere.
        '''

        # internal class to note if a metadata field has added and had no original value
        class NewFieldAdded( object ):
            pass

        # authorize saving this document
        if not self.authorize_save():
            raise MongoObjectsAuthFailed

        # refuse to save a read-only document
        if self.readonly:
            raise MongoObjectsReadOnly( f"Can't save readonly object {type(self)} at {id(self)}" )

        # Use a dictionary to record original metadata in case they need to be rolled back
        # These metadata values should never be None, so during rollback we remove any values
        # for which get() returned None.
        original_metadata = {}

        # set updated timestamp
        original_metadata['_updated'] = self.get('_updated')
        self['_updated'] = self.utcnow()

        # add created timestamp if it doesn't exist
        if '_created' not in self:
            original_metadata['_created'] = None
            self['_created'] = self['_updated']

        # add object version if provided
        if self.object_version is not None:
            original_metadata['_objver'] = self.get('_objver')
            self['_objver'] = self.object_version

        try:
            # if the document has never been written to the database, write it now and record the ID
            if '_id' not in self:
                result = self.collection().insert_one( self.data )
                self['_id'] = result.inserted_id

            # Force-save a document regardless of timestamp
            elif force:
                result = self.collection().replace_one( { '_id' : self['_id'] }, self.data, upsert=True )

            # Otherwise, only update a document with the same updated timestamp as our in-memory object
            else:
                result = self.collection().find_one_and_replace(
                    { '_id' : self['_id'], '_updated' : original_metadata['_updated'] },
                    self.data,
                    return_document=ReturnDocument.AFTER )

                # on failure, we assume the document has been updated elsewhere and raise an exception
                if result is None:
                    raise MongoObjectsDocumentModified( f"document {self.id()} already updated" )

        # on any error roll back to the original metadata
        except Exception as e:
            for (k, v) in original_metadata.items():
                # If the original value is None, assume we added the field and should remove it
                if v is None:
                    del self[k]
                # Otherwise, restore the original value
                else:
                    self[k] = v
            raise(e)


    @classmethod
    def split_id( cls, subdoc_id ):
        '''Split a subdocument ID into its component document ID and one or more subdocument keys.'''
        return subdoc_id.split( cls.subdoc_key_sep )


    @staticmethod
    def utcnow():
        '''MongoDB stores milliseconds, not microseconds.
        Drop microseconds from the standard utcnow() so database time comparisons will work.'''
        now = datetime.utcnow()
        return now.replace( microsecond=(now.microsecond // 1000) * 1000 )



class PolymorphicMongoUserDict( MongoUserDict ):
    '''Like MongoUserDict but supports polymorphic document objects within the same collection.

    Each subclass needs to define a unique subclass_key'''

    # Map subclass_keys to subclasses
    # Override this with an empty dictionary in the base class
    # of your subclass tree to create a separate namespace
    subclass_map = {}

    # Must be unique and non-None for each subclass
    # Base classes may define this key as well
    subclass_key = None

    # Name of internal key added to each document to record the subclass_key
    subclass_key_name = '_sckey'



    @classmethod
    def __init_subclass__( cls, **kwargs):
        '''auto-register every PolymorphicMongoUserDict subclass'''
        super().__init_subclass__(**kwargs)
        try:
            if getattr( cls, 'subclass_key', None ) is not None:
                assert cls.subclass_key not in cls.subclass_map, f"duplicate subclass_key for {type(cls)}"
                cls.subclass_map[ cls.subclass_key ] = cls
        except Exception as e:
            raise MongoObjectsSubclassError( 'PolymorphicMongoUserDict(): unable to register subclass' ) from e


    @classmethod
    def find( cls, filter={}, projection=None, readonly=None, **kwargs ):
        '''Return matching documents as appropriate subclass instances'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectsAuthFailed

        # if a projection is provided, force the resulting object to be read-only
        readonly = readonly or projection is not None

        for doc in cls.collection().find( filter, projection, **kwargs ):
            obj = cls.instantiate(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                yield obj


    @classmethod
    def find_one( cls, filter={}, projection=None, readonly=None, no_match=None, **kwargs ):
        '''Return a single matching document as the appropriate subclass or None'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectsAuthFailed

        # if a projection is provided, force the resulting object to be read-only
        readonly = readonly or projection is not None

        doc = cls.collection().find_one( filter, projection, **kwargs )
        if doc is not None:
            obj = cls.instantiate( doc, readonly=readonly )
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                return obj
        return no_match


    @classmethod
    def get_subclass_by_key( cls, subclass_key ):
        '''Look up a subclass in the subclass_map by its subclass_key
        If the subclass can't be located, return the base class'''
        return cls.subclass_map.get( subclass_key, cls )


    @classmethod
    def get_subclass_from_doc( cls, doc ):
        '''Return the correct subclass to represent this document.
        If the document doesn't contain a subclass_key_name value or the value
        doesn't exist in the subclass_map, return the base class'''
        return cls.get_subclass_by_key( doc.get( cls.subclass_key_name ) )


    @classmethod
    def instantiate( cls, doc, readonly=False ):
        '''Instantiate a PolymorphicMongoUserDict subclass based on the content
        of the provided MongoDB document'''
        # Looks like a bug but isn't
        # The first function call determines the correct subclass
        # The second function call populates a new UserDict subclass with data from the document
        return cls.get_subclass_from_doc( doc )( doc, readonly=readonly )


    def save( self, force=False ):
        '''Add the subclass_key and save the document'''
        if self.subclass_key is not None:
            self[ self.subclass_key_name ] = self.subclass_key
        return super().save( force=force )




################################################################################
## MongoDB subdocument proxies
################################################################################

class MongoBaseProxy( object ):
    '''Intended for interal use. Base of all other proxy objects'''

    # Users must override this to provide the name of the dictionary or list container
    container_name = None


    def __contains__( self, key ):
        return key in self.get_subdoc()


    def __delitem__( self, key ):
        del self.get_subdoc()[ key ]


    def __getitem__( self, key ):
        return self.get_subdoc()[ key ]


    def __iter__( self ):
        return iter( self.get_subdoc().keys() )


    def __setitem__( self, key, value ):
        self.get_subdoc()[ key ] = value


    @classmethod
    def create_key( cls, parent ):
        '''Create a unique key value for this subdocument.
        The default implementation requests a hex string for the next unique integer
        as saved in the ultimate MongoUserDict parent object.
        Users may override this using data from the subdoc or other methods to generate a unique key.'''
        return getattr( parent, 'ultimate_parent', parent ).get_unique_key( autosave=False )


    def data( self ):
        '''Convenience function to behave similar to UserDict'''
        return self.get_subdoc()


    def get( self, key, default=None ):
        return self.get_subdoc().get( key, default )


    def id( self ):
        return f"{self.parent.id()}{self.ultimate_parent.subdoc_key_sep}{self.key}"


    def items( self ):
        return self.get_subdoc().items()


    def keys( self ):
        return self.get_subdoc().keys()


    def setdefault( self, key, default=None ):
        return self.get_subdoc().setdefault( key, default )


    def update( self, values ):
        self.get_subdoc().update( values )


    def save( self ):
        return self.parent.save()


    def values( self ):
        return self.get_subdoc().values()




class PolymorphicMongoBaseProxy( MongoBaseProxy ):
    '''Like MongoBaseProxy but supports polymorphic subdocument objects within the same parent document.

    Each subclass needs to define a unique proxy_subclass_key

    Parent objects need to call instantiate() to create the correct subclass type'''

    # Map proxy_subclass_keys to subclasses
    # Override this with an empty dictionary in the base class
    # of your subclass tree to create a separate namespace
    proxy_subclass_map = {}

    # Must be unique and non-None for each subclass
    # Base classes may define this key as well
    proxy_subclass_key = None

    # Name of internal key added to each subdocument to record the proxy_subclass_key
    proxy_subclass_key_name = '_psckey'


    @classmethod
    def __init_subclass__( cls, **kwargs):
        '''auto-register every PolymorphicMongoBaseProxy subclass'''
        super().__init_subclass__(**kwargs)
        try:
            if getattr( cls, 'proxy_subclass_key', None ) is not None:
                assert cls.proxy_subclass_key not in cls.proxy_subclass_map, f"duplicate proxy_subclass_key for {type(cls)}"
                cls.proxy_subclass_map[ cls.proxy_subclass_key ] = cls
        except Exception as e:
            raise MongoObjectsSubclassError( 'PolymorphicMongoBaseProxy(): unable to register subclass' ) from e


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        '''Add the proxy_subclass_key before passing to the base class create()'''
        if cls.proxy_subclass_key is not None:
            subdoc[ cls.proxy_subclass_key_name ] = cls.proxy_subclass_key
        return super().create( parent, subdoc, autosave=autosave )


    @classmethod
    def get_subclass_by_key( cls, proxy_subclass_key ):
        '''Look up a proxy_subclass in the proxy_subclass_map by its proxy_subclass_key
        If the subclass can't be located, return the called class'''
        return cls.proxy_subclass_map.get( proxy_subclass_key, cls )


    @classmethod
    def get_subclass_from_doc( cls, doc ):
        '''Return the correct subclass to represent this document.
        If the document doesn't contain a proxy_subclass_key_name value or the value
        doesn't exist in the proxy_subclass_map, return the base class'''
        return cls.get_subclass_by_key( doc.get( cls.proxy_subclass_key_name ) )




class AccessDictProxy( object ):
    '''Intended for internal multiple-inheritance use.

    Organize functions to reference subdocuments within a parent MongoDB dictionary.
    Individual subdocuments are stored in a dictionary container.

    Keys must be strings as required by MongoDB documents.

    MongoUserDict.get_unique_key() is a convenient way to generate unique keys
    within a MongoDB document.
    '''

    def __init__( self, parent, key ):
        self.parent = parent
        self.ultimate_parent = getattr( parent, 'ultimate_parent', parent )
        self.key = str(key)

        # make sure this key actually exists before we return successfully
        assert self.key in self.get_subdoc_container()


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        '''Add a new subdocument to the container.
        Auto-assign the ID
        Return the new proxy object'''
        key = cls.create_key( parent )

        # insure the container exists before adding the document
        parent.setdefault( cls.container_name, {} )[ key ] = subdoc
        if autosave:
            parent.save()
        return cls.get_proxy( parent, key )



    def delete( self, autosave=True ):
        '''Delete the subdocument from the container dictionary.
        Remove the key so the proxy can't be referenced again.
        By default save the parent document'''
        del self.get_subdoc_container()[ self.key ]
        if autosave:
            self.parent.save()
        self.key = None


    @classmethod
    def get_proxies( cls, parent ):
        return [ cls.get_proxy( parent, key ) for key in parent.get( cls.container_name, {} ).keys() ]


    def get_subdoc( self ):
        return self.get_subdoc_container()[ self.key ]


    def get_subdoc_container( self ):
        return self.parent.get( self.container_name, {} )




class MongoDictProxy( MongoBaseProxy, AccessDictProxy ):
    '''Implement proxy object using a dictionary as a container'''

    @classmethod
    def get_proxy( cls, parent, key ):
        '''Return a single proxy object. For non-polymorphic use,
        this simply calls __init__()'''
        return cls( parent, key )




class PolymorphicMongoDictProxy( PolymorphicMongoBaseProxy, AccessDictProxy ):
    '''Polymorphic version of MongoDictProxy'''

    @classmethod
    def get_proxy( cls, parent, key ):
        '''Return a single proxy object. For PolymorphicMongoDictProxy,
        determine the correct subclass type and call __init__()'''
        # use an anonymous base-class proxy to get access to the subdocument
        # so that get_subclass_from_doc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        return cls.get_subclass_from_doc( cls( parent, key ) )( parent, key )




class AccessListProxy( object ):
    '''Intended for internal multiple-inheritance use.

    Organize functions to reference subdocuments within a parent MongoDB dictionary.
    Individual subdocuments are stored in a list container.

    Since the container object is a list, not a dictionary, we can't use the key
    to look up items directly.

    Instead, we use get_key() to extract a key from a subdocument
    and use the result to determine if a given document matches.

    For convenience, if no key is given but a sequence provided, we initialize the key from
    the subdocument at that index'''

    # The name of the internal key added to each subdoc to store the unique subdocument "key" value
    # Subclasses may override this name or
    # override get_key() and set_key() to implement their own mechanism of locating subdocuments
    subdoc_key_name = '_sdkey'


    def __init__( self, parent, key=None, seq=None ):
        self.parent = parent
        self.ultimate_parent = getattr( parent, 'ultimate_parent', parent )

        if key is not None:
            self.key = key
            self.seq = seq
        elif seq is not None:
            self.key = self.get_key( self.get_subdoc_container()[ seq ] )
            self.seq = seq
        else:
            raise Exception( "MongoListProxy(): key or seq must be provided" )


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        '''Add a new subdocument to the container.
        Auto-assign the ID
        Return the new proxy object.
        '''
        # Create a unique key for this subdocument
        key = cls.create_key( parent )

        # Add the key to the subdocument
        cls.set_key( subdoc, key )

        # Append the new subdocument to the list
        container = parent.setdefault( cls.container_name, [] )
        container.append( subdoc )

        # Save if requested
        if autosave:
            parent.save()

        # Since we know we just appended to the end of the list, provide
        # the sequence as well as the key
        return cls.get_proxy( parent, key, len( container ) - 1 )


    def delete( self, autosave=True ):
        '''Delete the subdocument from the container list.
        Remove the key and sequence so the proxy can't be referenced again.
        By default save the parent document.
        '''

        # First make sure the sequence number is accurate
        self.get_subdoc()
        # Then pop that item from the list
        self.get_subdoc_container().pop( self.seq )
        if autosave:
            self.parent.save()
        self.key = self.seq = None


    @classmethod
    def get_key( cls, subdoc ):
        '''Extract the key from a subdocument dictionary.'''
        return subdoc[ cls.subdoc_key_name ]


    @classmethod
    def get_proxies( cls, parent ):
        return [ cls.get_proxy( parent, seq=seq ) for seq in range( len( parent.get( cls.container_name, [] ) ) ) ]


    def get_subdoc( self ):
        # We don't want to iterate the list each time looking for the subdoc that matches
        # EAFTP: If the document at self.seq is a match, return it
        # Otherwise, scan the list for a match.
        # Since __init__() sets self.seq to None, the item will automatically be located on first use
        try:
            subdoc = self.get_subdoc_container()[ self.seq ]
            assert self.key == self.get_key( subdoc )
            return subdoc
        except:
            for (seq, subdoc) in enumerate( self.get_subdoc_container() ):
                if self.key == self.get_key( subdoc ):
                    self.seq = seq
                    return subdoc
            raise Exception( "MongoListProxy.get_subdoc(): no match found" )


    def get_subdoc_container( self ):
        return self.parent.get( self.container_name, [] )


    @classmethod
    def set_key( cls, subdoc, key ):
        '''Set the key in a subdocument dictionary.'''
        subdoc[ cls.subdoc_key_name ] = key




class MongoListProxy( MongoBaseProxy, AccessListProxy ):
    '''Implement proxy object using a list as a container'''

    @classmethod
    def get_proxy( cls, parent, key=None, seq=None ):
        '''Return a single proxy object. For non-polymorphic use,
        this simply calls __init__()'''
        return cls( parent, key, seq )




class PolymorphicMongoListProxy( PolymorphicMongoBaseProxy, AccessListProxy ):
    '''Polymorphic version of MongoListProxy'''

    @classmethod
    def get_proxy( cls, parent, key=None, seq=None ):
        '''Return a single proxy object. For PolymorphicMongoDictProxy,
        determine the correct subclass type and call __init__()'''
        # use an anonymous base-class proxy to get access to the subdocument
        # so that get_subclass_from_doc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        return cls.get_subclass_from_doc( cls( parent, key, seq ) )( parent, key, seq )




class AccessSingleProxy( AccessDictProxy ):
    '''Intended for internal multiple-inheritance use.

    Organize functions to reference a single subdocument dictionary
    within a parent MongoDB dictionary.

    This is really just AccessDictProxy with the parent MongoDB document as the container.

    Keys must be strings as required by MongoDB documents.
    '''

    @classmethod
    def create( cls, parent, subdoc={}, key=None, autosave=True ):
        '''Add a new single subdocument dictionary to the parent object.
        No new key is auto-assigned as single subdocuments are assigned to fixed keys.
        The key can be defined in the class as "container_name"
        or overriden in the function call as "key".
        Return the new proxy object.
        '''
        if key is None:
            key = cls.container_name
        parent[ key ] = subdoc
        if autosave:
            parent.save()
        return cls.get_proxy( parent, key )


    @classmethod
    def get_proxies( cls, parent ):
        '''get_proxies() doesn't make sense for single proxy use.
        This is a class method and we don't know the key, so
        we don't know which of the parent's subdocuments to return'''
        raise Exception( 'single proxy objects do not support get_proxies()' )


    def get_subdoc_container( self ):
        '''For a single subdocument dictionary, the container is the parent document.'''
        return self.parent


    def id( self ):
        '''Force the subdocument ID for single proxies to "0". We
        can't use the actual key as we risk exposing the actual
        dictionary key name.'''
        return f"{self.parent.id()}{self.ultimate_parent.subdoc_key_sep}0"






class MongoSingleProxy( AccessSingleProxy, MongoBaseProxy ):
    '''Implement proxy object for a single subdocument dictionary'''

    @classmethod
    def get_proxy( cls, parent, key=None ):
        '''Return a single proxy object. For non-polymorphic use,
        this simply calls __init__()'''
        if key is None:
            key = cls.container_name
        return cls( parent, key )




class PolymorphicMongoSingleProxy( AccessSingleProxy, PolymorphicMongoBaseProxy ):
    '''Polymorphic version of MongoSingleProxy'''

    @classmethod
    def create( cls, parent, subdoc={}, key=None, autosave=True ):
        '''Add the proxy_subclass_key before passing to the base class create()
        AccessSingleProxy needs to be first in the object inheritance to get
        super() to work properly'''
        if cls.proxy_subclass_key is not None:
            subdoc[ cls.proxy_subclass_key_name ] = cls.proxy_subclass_key
        return super().create( parent, subdoc, key=key, autosave=autosave )


    @classmethod
    def get_proxy( cls, parent, key=None ):
        '''Return a single proxy object. For PolymorphicMongoDictProxy,
        determine the correct subclass type and call __init__()'''
        # use an anonymous base-class proxy to get access to the subdocument
        # so that get_subclass_from_doc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        if key is None:
            key = cls.container_name
        return cls.get_subclass_from_doc( cls( parent, key ) )( parent, key )



