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

class MongoObjectReadOnly( Exception ):
    pass

class MongoObjectAuthFailed( Exception ):
    pass


################################################################################
# MongoDB document wrappers
################################################################################


class MongoUserDict( UserDict ):
    # Subclasses can provide a collection name and a MongoDb database connection
    # as a class attribute OR override collection() to return the correct collection object
    collection_name = None
    database = None

    # The character sequence used to separate the document ID from proxy subdocument keys
    # This may be overriden but it is the user's responsibility to guarantee that this
    # sequence will never appear in any ID or subdoc key.
    # Since the default IDs and subdoc keys are hex, 'g' is a safe separator
    subdocKeySep = 'g'


    def __init__( self, doc={}, readonly=False ):
        '''Initialize the custom UserDict object
        Flag readonly objects appropriately'''
        super().__init__( doc )
        self.readonly = readonly

        # Authorize creating this object prior to returning to the user
        if not self.authorize_init():
            raise MongoObjectAuthFailed


    # Authorization hooks()
    # The user may call these hooks to authorize various CRUD operations
    def authorize_init( self ):
        '''Called after the document object is initialized but
        before it is returned to the user.
        If the return value is not truthy, an exception is raised.'''
        return True

    def authorize_delete( self ):
        '''Called before the current document is deleted.
        If the return value is not truthy, an exception is raised.'''
        return True

    @classmethod
    def authorize_pre_read( cls ):
        '''Called before a read operation is performed.
        This is a class method as no data has been read and no
        document object has been created.
        If the return value is not truthy, an exception is raised.'''
        return True

    def authorize_read( self ):
        '''Called after a document has been read but before the
        data is returned to the user.
        If the return value is not truthy, the data will
        not be returned.

        Note that if find_one() only inspects the first document
        returned by the underlying MongoDB find_one() call. If the
        document returned does not pass authorization, no attempt is
        made to locate another matching document.'''
        return True

    def authorize_save( self ):
        '''Called before the current document is saved.
        If the return value is not truthy, an exception is raised.'''
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
                raise MongoObjectAuthFailed
            self.collection().find_one_and_delete( { '_id' : ObjectId( self['_id'] ) } )
            del self['_id']


    @classmethod
    def find( cls, filter={}, projection=None, readonly=False, **kwargs ):
        '''Return matching documents as instances of this class'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectAuthFailed

        # if a projection is provided, force the resulting object to be read-only
        readonly = readonly or projection is not None

        for doc in cls.collection().find( filter, projection, **kwargs ):
            print( "STEP 4" )
            obj = cls(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                yield obj


    @classmethod
    def find_one( cls, filter={}, projection=None, readonly=False, noMatch=None, **kwargs ):
        '''Return a single matching document as an instance of this class or None'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectAuthFailed

        # if a projection is provided, force the resulting object to be read-only
        readonly = readonly or projection is not None

        doc = cls.collection().find_one( filter, projection, **kwargs )
        if doc is not None:
            obj = cls(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                return obj
        return noMatch


    def getUniqueInteger( self, autosave=True ):
        '''Provide the next unique integer for this document.
        These integers are convenient for use as keys of subdocuments.
        Start with 1; 0 is reserved for single proxy documents which don't have a key.
        By default, the document is saved.'''
        self.setdefault( '_lastUniqueInteger', 0 )
        self['_lastUniqueInteger'] += 1
        if autosave:
            self.save()
        return self['_lastUniqueInteger']


    def getUniqueKey( self, autosave=True ):
        '''Format the next unique integer as a hexidecimal string'''
        return f"{self.getUniqueInteger( autosave ):x}"


    def id( self ):
        '''Convert this document's database ID to a string'''
        return str( self['_id'] )


    @classmethod
    def loadById( cls, docId, **kwargs ):
        '''Locate a document by its database ID'''
        return cls.find_one( { '_id' : ObjectId( docId ) }, **kwargs )


    @classmethod
    def loadProxyById( cls, id, *args, readonly=False ):
        '''Based on a subdocument ID and a list of classes, load the Mongo parent
        documents, create any intermediate proxies and return the requested
        proxy object.

        id is a subdocument ID string separated by subdocKeySep. It includes the
        ObjectId of the top-level MongoDB document

        args is a list of proxy objects in descending order. It does not include
        the top-level MongoUserDict class'''

        # split the subdocumentId into its components
        ids = cls.splitId( id )

        # load the MongoDB document and remove the ID from the list of ids
        obj = cls.loadById( ids.pop(0), readonly=readonly )

        # loop through each level of proxy using the previous object as the parent
        for (proxyClass, id) in zip( args, ids, strict=True ):
            obj = proxyClass.getProxy( obj, id )

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

        # authorize saving this document
        if not self.authorize_save():
            raise MongoObjectAuthFailed

        # refuse to save a read-only document
        if self.readonly:
            raise MongoObjectReadOnly( f"Can't save readonly object {type(self)} at {id(self)}" )

        # set updated timestamp
        # Note the original value in case we need to roll back
        addedUpdated = '_updated' not in self
        originalUpdated = self.get('_updated')
        self['_updated'] = self.utcnow()

        # add created timestamp if it doesn't exist
        # set flag in case we need to roll back
        addedCreated = '_created' not in self
        self.setdefault( '_created', self['_updated'] )

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
                    { '_id' : self['_id'], '_updated' : originalUpdated },
                    self.data,
                    return_document=ReturnDocument.AFTER )

                # on failure, we assume the document has been updated elsewhere and raise an exception
                assert result is not None, f"document {self.id()} already updated"

        # on any error roll back _updated and _created to the original value or remove if we added them
        except Exception as e:
            if addedCreated:
                del self['_created']
            if addedUpdated:
                del self['_updated']
            else:
                self['_updated'] = originalUpdated
            raise(e)


    @classmethod
    def splitId( cls, subdocId ):
        '''Split a subdocument ID into its component document ID and one or more subdocument keys.'''
        return subdocId.split( cls.subdocKeySep )


    @staticmethod
    def utcnow():
        '''MongoDB stores milliseconds, not microseconds.
        Drop microseconds from the standard utcnow() so database time comparisons will work.'''
        now = datetime.utcnow()
        return now.replace( microsecond=(now.microsecond // 1000) * 1000 )



class PolymorphicMongoUserDict( MongoUserDict ):
    '''Like MongoUserDict but supports polymorphic document objects within the same collection.

    Each subclass needs to define a unique subclassKey'''

    # Map subclassKeys to subclasses
    # Override this with an empty dictionary in the base class
    # of your subclass tree to create a separate namespace
    subclassMap = {}

    # Must be unique and non-None for each subclass
    # Base classes may define this key as well
    subclassKey = None

    # Name of internal key added to each document to record the subclassKey
    subclassKeyName = '_sckey'



    @classmethod
    def __init_subclass__( cls, **kwargs):
        '''auto-register every PolymorphicMongoUserDict subclass'''
        super().__init_subclass__(**kwargs)
        try:
            if getattr( cls, 'subclassKey', None ) is not None:
                assert cls.subclassKey not in cls.subclassMap, f"duplicate subclassKey for {type(cls)}"
                cls.subclassMap[ cls.subclassKey ] = cls
        except Exception as e:
            raise Exception( 'PolymorphicMongoUserDict(): unable to register subclass' ) from e


    @classmethod
    def find( cls, filter={}, projection=None, readonly=False, **kwargs ):
        '''Return matching documents as appropriate subclass instances'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectAuthFailed

        # if a projection is provided, force the resulting object to be read-only
        readonly = readonly or projection is not None

        for doc in cls.collection().find( filter, projection, **kwargs ):
            obj = cls.instantiate(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                yield obj


    @classmethod
    def find_one( cls, filter={}, projection=None, readonly=False, noMatch=None, **kwargs ):
        '''Return a single matching document as the appropriate subclass or None'''
        # Authorize reading at all
        if not cls.authorize_pre_read():
            raise MongoObjectAuthFailed

        # if a projection is provided, force the resulting object to be read-only
        readonly = readonly or projection is not None

        doc = cls.collection().find_one( filter, projection, **kwargs )
        if doc is not None:
            obj = cls.instantiate( doc, readonly=readonly )
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                return obj
        return noMatch


    @classmethod
    def getSubclassByKey( cls, subclassKey ):
        '''Look up a subclass in the subclassMap by its subclassKey
        If the subclass can't be located, return the base class'''
        return cls.subclassMap.get( subclassKey, cls )


    @classmethod
    def getSubclassFromDoc( cls, doc ):
        '''Return the correct subclass to represent this document.
        If the document doesn't contain a subclassKeyName value or the value
        doesn't exist in the subclassMap, return the base class'''
        return cls.getSubclassByKey( doc.get( cls.subclassKeyName ) )


    @classmethod
    def instantiate( cls, doc, readonly=False ):
        '''Instantiate a PolymorphicMongoUserDict subclass based on the content
        of the provided MongoDB document'''
        # Looks like a bug but isn't
        # The first function call determines the correct subclass
        # The second function call populates a new UserDict subclass with data from the document
        return cls.getSubclassFromDoc( doc )( doc, readonly=readonly )


    def save( self, force=False ):
        '''Add the subclassKey and save the document'''
        if self.subclassKey is not None:
            self[ self.subclassKeyName ] = self.subclassKey
        return super().save( force=force )




################################################################################
## MongoDB subdocument proxies
################################################################################

class MongoBaseProxy( object ):
    '''Intended for interal use. Base of all other proxy objects'''

    # Users must override this to provide the name of the dictionary or list container
    containerName = None


    def __contains__( self, key ):
        return key in self.getSubdoc()


    def __delitem__( self, key ):
        del self.getSubdoc()[ key ]


    def __getitem__( self, key ):
        return self.getSubdoc()[ key ]


    def __iter__( self ):
        return iter( self.getSubdoc().keys() )


    def __setitem__( self, key, value ):
        self.getSubdoc()[ key ] = value


    @classmethod
    def createKey( cls, parent ):
        '''Create a unique key value for this subdocument.
        The default implementation requests a hex string for the next unique integer
        as saved in the ultimate MongoUserDict parent object.
        Users may override this using data from the subdoc or other methods to generate a unique key.'''
        return getattr( parent, 'ultimateParent', parent ).getUniqueKey( autosave=False )


    def data( self ):
        '''Convenience function to behave similar to UserDict'''
        return self.getSubdoc()


    def get( self, key, default=None ):
        return self.getSubdoc().get( key, default )


    def id( self ):
        return f"{self.parent.id()}{self.ultimateParent.subdocKeySep}{self.key}"


    def items( self ):
        return self.getSubdoc().items()


    def keys( self ):
        return self.getSubdoc().keys()


    def setdefault( self, key, default=None ):
        return self.getSubdoc().setdefault( key, default )


    def update( self, values ):
        self.getSubdoc().update( values )


    def save( self ):
        return self.parent.save()


    def values( self ):
        return self.getSubdoc().values()




class PolymorphicMongoBaseProxy( MongoBaseProxy ):
    '''Like MongoBaseProxy but supports polymorphic subdocument objects within the same parent document.

    Each subclass needs to define a unique proxySubclassKey

    Parent objects need to call instantiate() to create the correct subclass type'''

    # Map proxySubclassKeys to subclasses
    # Override this with an empty dictionary in the base class
    # of your subclass tree to create a separate namespace
    proxySubclassMap = {}

    # Must be unique and non-None for each subclass
    # Base classes may define this key as well
    proxySubclassKey = None

    # Name of internal key added to each subdocument to record the proxySubclassKey
    proxySubclassKeyName = '_psckey'


    @classmethod
    def __init_subclass__( cls, **kwargs):
        '''auto-register every PolymorphicMongoBaseProxy subclass'''
        super().__init_subclass__(**kwargs)
        try:
            if getattr( cls, 'proxySubclassKey', None ) is not None:
                assert cls.proxySubclassKey not in cls.proxySubclassMap, f"duplicate proxySubclassKey for {type(cls)}"
                cls.proxySubclassMap[ cls.proxySubclassKey ] = cls
        except Exception as e:
            raise Exception( 'PolymorphicMongoBaseProxy(): unable to register subclass' ) from e


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        '''Add the proxySubclassKey before passing to the base class create()'''
        if cls.proxySubclassKey is not None:
            subdoc[ cls.proxySubclassKeyName ] = cls.proxySubclassKey
        return super().create( parent, subdoc, autosave=autosave )


    @classmethod
    def getSubclassByKey( cls, proxySubclassKey ):
        '''Look up a proxySubclass in the proxySubclassMap by its proxySubclassKey
        If the subclass can't be located, return the called class'''
        return cls.proxySubclassMap.get( proxySubclassKey, cls )


    @classmethod
    def getSubclassFromDoc( cls, doc ):
        '''Return the correct subclass to represent this document.
        If the document doesn't contain a proxySubclassKeyName value or the value
        doesn't exist in the proxySubclassMap, return the base class'''
        return cls.getSubclassByKey( doc.get( cls.proxySubclassKeyName ) )




class AccessDictProxy( object ):
    '''Intended for internal multiple-inheritance use.

    Organize functions to reference subdocuments within a parent MongoDB dictionary.
    Individual subdocuments are stored in a dictionary container.

    Keys must be strings as required by MongoDB documents.

    MongoUserDict.getUniqueKey() is a convenient way to generate unique keys
    within a MongoDB document.
    '''

    def __init__( self, parent, key ):
        self.parent = parent
        self.ultimateParent = getattr( parent, 'ultimateParent', parent )
        self.key = str(key)

        # make sure this key actually exists before we return successfully
        assert self.key in self.getSubdocContainer()


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        '''Add a new subdocument to the container.
        Auto-assign the ID
        Return the new proxy object'''
        key = cls.createKey( parent )

        # insure the container exists before adding the document
        parent.setdefault( cls.containerName, {} )[ key ] = subdoc
        if autosave:
            parent.save()
        return cls.getProxy( parent, key )



    def delete( self, autosave=True ):
        '''Delete the subdocument from the container dictionary.
        Remove the key so the proxy can't be referenced again.
        By default save the parent document'''
        del self.getSubdocContainer()[ self.key ]
        if autosave:
            self.parent.save()
        self.key = None


    @classmethod
    def getProxies( cls, parent ):
        return [ cls.getProxy( parent, key ) for key in parent.get( cls.containerName, {} ).keys() ]


    def getSubdoc( self ):
        return self.getSubdocContainer()[ self.key ]


    def getSubdocContainer( self ):
        return self.parent.get( self.containerName, {} )




class MongoDictProxy( MongoBaseProxy, AccessDictProxy ):
    '''Implement proxy object using a dictionary as a container'''

    @classmethod
    def getProxy( cls, parent, key ):
        '''Return a single proxy object. For non-polymorphic use,
        this simply calls __init__()'''
        return cls( parent, key )




class PolymorphicMongoDictProxy( PolymorphicMongoBaseProxy, AccessDictProxy ):
    '''Polymorphic version of MongoDictProxy'''

    @classmethod
    def getProxy( cls, parent, key ):
        '''Return a single proxy object. For PolymorphicMongoDictProxy,
        determine the correct subclass type and call __init__()'''
        # use an anonymous base-class proxy to get access to the subdocument
        # so that getSubclassFromDoc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        return cls.getSubclassFromDoc( cls( parent, key ) )( parent, key )




class AccessListProxy( object ):
    '''Intended for internal multiple-inheritance use.

    Organize functions to reference subdocuments within a parent MongoDB dictionary.
    Individual subdocuments are stored in a list container.

    Since the container object is a list, not a dictionary, we can't use the key
    to look up items directly.

    Instead, we use getKey() to extract a key from a subdocument
    and use the result to determine if a given document matches.

    For convenience, if no key is given but a sequence provided, we initialize the key from
    the subdocument at that index'''

    # The name of the internal key added to each subdoc to store the unique subdocument "key" value
    # Subclasses may override this name or
    # override getKey() and setKey() to implement their own mechanism of locating subdocuments
    subdocKeyName = '_sdkey'


    def __init__( self, parent, key=None, seq=None ):
        self.parent = parent
        self.ultimateParent = getattr( parent, 'ultimateParent', parent )

        if key is not None:
            self.key = key
            self.seq = seq
        elif seq is not None:
            self.key = self.getKey( self.getSubdocContainer()[ seq ] )
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
        key = cls.createKey( parent )

        # Add the key to the subdocument
        cls.setKey( subdoc, key )

        # Append the new subdocument to the list
        container = parent.setdefault( cls.containerName, [] )
        container.append( subdoc )

        # Save if requested
        if autosave:
            parent.save()

        # Since we know we just appended to the end of the list, provide
        # the sequence as well as the key
        return cls.getProxy( parent, key, len( container ) - 1 )


    def delete( self, autosave=True ):
        '''Delete the subdocument from the container list.
        Remove the key and sequence so the proxy can't be referenced again.
        By default save the parent document.
        '''

        # First make sure the sequence number is accurate
        self.getSubdoc()
        # Then pop that item from the list
        self.getSubdocContainer().pop( self.seq )
        if autosave:
            self.parent.save()
        self.key = self.seq = None


    @classmethod
    def getKey( cls, subdoc ):
        '''Extract the key from a subdocument dictionary.'''
        return subdoc[ cls.subdocKeyName ]


    @classmethod
    def getProxies( cls, parent ):
        return [ cls.getProxy( parent, seq=seq ) for seq in range( len( parent.get( cls.containerName, [] ) ) ) ]


    def getSubdoc( self ):
        # We don't want to iterate the list each time looking for the subdoc that matches
        # EAFTP: If the document at self.seq is a match, return it
        # Otherwise, scan the list for a match.
        # Since __init__() sets self.seq to None, the item will automatically be located on first use
        try:
            subdoc = self.getSubdocContainer()[ self.seq ]
            assert self.key == self.getKey( subdoc )
            return subdoc
        except:
            for (seq, subdoc) in enumerate( self.getSubdocContainer() ):
                if self.key == self.getKey( subdoc ):
                    self.seq = seq
                    return subdoc
            raise Exception( "MongoListProxy.getSubdoc(): no match found" )


    def getSubdocContainer( self ):
        return self.parent.get( self.containerName, [] )


    @classmethod
    def setKey( cls, subdoc, key ):
        '''Set the key in a subdocument dictionary.'''
        subdoc[ cls.subdocKeyName ] = key




class MongoListProxy( MongoBaseProxy, AccessListProxy ):
    '''Implement proxy object using a list as a container'''

    @classmethod
    def getProxy( cls, parent, key=None, seq=None ):
        '''Return a single proxy object. For non-polymorphic use,
        this simply calls __init__()'''
        return cls( parent, key, seq )




class PolymorphicMongoListProxy( PolymorphicMongoBaseProxy, AccessListProxy ):
    '''Polymorphic version of MongoListProxy'''

    @classmethod
    def getProxy( cls, parent, key=None, seq=None ):
        '''Return a single proxy object. For PolymorphicMongoDictProxy,
        determine the correct subclass type and call __init__()'''
        # use an anonymous base-class proxy to get access to the subdocument
        # so that getSubclassFromDoc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        return cls.getSubclassFromDoc( cls( parent, key, seq ) )( parent, key, seq )




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
        The key can be defined in the class as "containerName"
        or overriden on the command line as "key".
        Return the new proxy object.
        '''
        if key is None:
            key = cls.containerName
        parent[ key ] = subdoc
        if autosave:
            parent.save()
        return cls.getProxy( parent, key )


    @classmethod
    def getProxies( cls, parent ):
        '''getProxies() doesn't make sense for single proxy use.
        This is a class method and we don't know the key, so
        we don't know which of the parent's subdocuments to return'''
        raise Exception( 'single proxy objects do not support getProxies()' )


    def getSubdocContainer( self ):
        '''For a single subdocument dictionary, the container is the parent document.'''
        return self.parent


    def id( self ):
        '''Force the subdocument ID for single proxies to "0". We
        can't use the actual key as we risk exposing the actual
        dictionary key name.'''
        return f"{self.parent.id()}{self.ultimateParent.subdocKeySep}0"






class MongoSingleProxy( AccessSingleProxy, MongoBaseProxy ):
    '''Implement proxy object for a single subdocument dictionary'''

    @classmethod
    def getProxy( cls, parent, key=None ):
        '''Return a single proxy object. For non-polymorphic use,
        this simply calls __init__()'''
        if key is None:
            key = cls.containerName
        return cls( parent, key )




class PolymorphicMongoSingleProxy( AccessSingleProxy, PolymorphicMongoBaseProxy ):
    '''Polymorphic version of MongoSingleProxy'''

    @classmethod
    def create( cls, parent, subdoc={}, key=None, autosave=True ):
        '''Add the proxySubclassKey before passing to the base class create()
        AccessSingleProxy needs to be first in the object inheritance to get
        super() to work properly'''
        if cls.proxySubclassKey is not None:
            subdoc[ cls.proxySubclassKeyName ] = cls.proxySubclassKey
        return super().create( parent, subdoc, key=key, autosave=autosave )


    @classmethod
    def getProxy( cls, parent, key=None ):
        '''Return a single proxy object. For PolymorphicMongoDictProxy,
        determine the correct subclass type and call __init__()'''
        # use an anonymous base-class proxy to get access to the subdocument
        # so that getSubclassFromDoc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        if key is None:
            key = cls.containerName
        return cls.getSubclassFromDoc( cls( parent, key ) )( parent, key )



