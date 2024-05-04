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
from collections import UserDict
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
    """
    Access MongoDB documents through user-defined UserDict subclasses.

    User classes must provide `collection_name` and `database` or override
    the :func:`collection()` function to return the correct pymongo collection object.
    """

    #: Required: override with the name of the MongoDB collection
    #: where the documents are stored
    #:
    #: :meta hide-value:
    collection_name = None

    #: Required: override with the pymongo database connection object
    #:
    #: :meta hide-value:
    database = None

    #: Optional: If object_version is not``None``, :func:`find()` and :func:`find_one()`
    #: by default restrict queries to documents with the current `object_version`.
    #: This enables a type of schema versioning.
    object_version = None

    #: The character sequence used to separate the document ID from proxy subdocument keys.
    #: This may be overriden but it is the user's responsibility to guarantee that this
    #: sequence will never appear in any ID or subdoc key.
    #: Since the default IDs and subdoc keys are hex, ``g`` is a safe, default separator
    subdoc_key_sep = 'g'


    def __init__( self, doc={}, readonly=False ):
        """
        Initialize the custom UserDict object
        flagging readonly objects appropriately.

        :raises MongoObjectsAuthFailed: if `authorize_init()` has been overriden
          and does not return a truthy value
        """

        super().__init__( doc )
        self.readonly = readonly

        # Authorize creating this object prior to returning to the user
        if not self.authorize_init():
            raise MongoObjectsAuthFailed


    @classmethod
    def add_object_version_filter( cls, filter, object_version ):
        """
        Implement automatic object version filtering for ``find()`` and ``find_one()`.
        The object-version keyword argument affects if and how to implement
        object version filtering.

        :meta private:
        """
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
        """Called after the document object is initialized but
        before it is returned to the user.

        This hook is called when creating a new object and during calls to
        :func:`find` and :func:`find_one`.

        Override this function and return ``False`` to block creating
        this document.

        :returns: Whether creating the current document is authorized (default ``True``)
        :rtype: bool
        """
        return True

    def authorize_delete( self ):
        """Called before the current document is deleted.

        Override this function and return ``False`` to block deleting
        this document.

        :returns: Whether deleting the current document is authorized (default ``True``)
        :rtype: bool
        """
        return True

    @classmethod
    def authorize_pre_read( cls ):
        """Called before a read operation is performed.
        This is a class method as no data has been read and no
        document object has been created.

        :returns: Whether reading any documents is authorized (default ``True``)
        :rtype: bool
        """
        return True

    def authorize_read( self ):
        """Called after a document has been read but before the
        data is returned to the user.
        If the return value is not truthy, the data will
        not be returned.

        Note that ``find_one()`` only inspects the first document
        returned by the underlying ``pymongo.find_one()`` call. If the
        document returned does not pass authorization, no attempt is
        made to locate another matching document.

        :returns: Whether reading the current document is authorized (default ``True``)
        :rtype: bool
        """
        return True

    def authorize_save( self ):
        """Called before the current document is saved.

        :returns: Whether saving the current document is authorized (default ``True``)
        :rtype: bool
        """
        return True


    @classmethod
    def collection( cls ):
        """Return the :class:`pymongo.Collection` object
        from the active database for the named collection

        For complex situations users may omit the *database* and *connection_name*
        attributes when defining the class and instead override this function.

        This function must return a :class:`pymongo.Collection` object.
        """

        return cls.database.get_collection( cls.collection_name )


    def delete( self ):
        """Delete the current object.
        Remove the id so :func:`.save()` will know this is a new object if we try to re-save.

        :raises MongoObjectsAuthFailed: if `authorize_delete()` has been overriden
          and does not return a truthy value
        """

        if '_id' in self:
            # Authorize deleting this object
            if not self.authorize_delete():
                raise MongoObjectsAuthFailed
            self.collection().find_one_and_delete( { '_id' : ObjectId( self['_id'] ) } )
            del self['_id']


    @classmethod
    def find( cls, filter={}, projection=None, readonly=None, object_version=None, **kwargs ):
        """Return matching documents as instances of this class

        :param dict filter: Updated with *cls.object_version* as appropriate
          and passed to :func:`pymongo.find`
        :param dict projection: Passed to :func:`pymongo.find`
        :param readonly:

          1) If ``None`` and a projection is provided, mark the objects as readonly.
          2) If ``None`` and no projection is given, consider the objects read-write.
          3) If ``True``, mark the objects as readonly regardless of the projection.
          4) If ``False``, consider the objects read-write regardless of the projection.

        :type readonly: ``None`` or *bool*
        :param object_version: Only if *cls.object_version* is not ``None``, implement object schema versioning.

          1) If ``None``, update the filter to only return documents with the current *cls.object_version* value
          2) If ``False``, don't filter objects by *cls.object_version*
          3) For any other value, update the filter to only return documents with the given *object_version*

        :type object_version: ``None``, ``False``, any scalar value
        :returns: a generator for instances of the user-defined :class:`MongoUserDict` subclass
        :raises MongoObjectsAuthFailed: if `authorize_pre_read()` has been overriden
          and does not return a truthy value
        """

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
        """
        Return a single matching document as an instance of this class or None

        :param filter: as with :func:`.find`
        :param projection: as with :func:`.find`
        :param readonly: as with :func:`.find`
        :param object_version: as with :func:`.find`
        :param no_match: Value to return if no matching document is found
        :type no_match: ``None`` or any value
        :returns: *no_match* value; ``None`` by default
        :raises MongoObjectsAuthFailed: if `authorize_pre_read()` has been overriden
          and does not return a truthy value
        """
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
        """Provide the next unique integer for this document.

        These integers are convenient for use as keys of subdocuments.
        Starts with 1; 0 is reserved for single proxy documents which don't have a key.

        :param autosave: Should the document be saved after the next
          unique integer is issued
        :type autosave: bool
        :returns: The next unique integer for this document
        :rtype: int
        """

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
        """Format the next unique integer as a hexidecimal string

        :param autosave: passed to :func:`get_unique_integer`
        :type autosave: bool
        :returns: The lowercase hexidecimal string representing the
          next unique integer for this document.
        :rtype: str
        """
        return f"{self.get_unique_integer( autosave ):x}"


    def id( self ):
        """Convert this document's ObjectId to a string

        :return: The document ObjectId
        :rtype: str
        :raises KeyError: if the document has not yet been saved
          and has not been assigned an ObjectId
        """
        return str( self['_id'] )


    @classmethod
    def load_by_id( cls, doc_id, **kwargs ):
        """Locate a document by its ObjectId

        :param doc_id: the ObjectId for the desired document
        :type doc_id: `str` or `bson.ObjectId`
        :param kwargs: passed to :func:`.find_one`
        :returns: an instance of the current class
        """
        return cls.find_one( { '_id' : ObjectId( doc_id ) }, **kwargs )


    @classmethod
    def load_proxy_by_id( cls, id, *args, readonly=False ):
        """Based on a full subdocument ID string and a list of classes,
        load the Mongo parent document, create any intermediate proxies
        and return the requested proxy object.

        :param id: a full subdocument ID string separated by `cls.subdoc_key_sep`.
          It includes the ObjectId of the top-level MongoDB document and
          one or more subdocument keys.
        :type id: str
        :param args: one or more user-defined proxy classes in descending order,
          one per subdocument key. The top-level parent :class:`MongoUserDict`
          subclass is not included.
        :param readonly: passed to :func:`find_one`
        :type readonly: bool
        :returns: an instance of the final, rightmost proxy subdocument class
          from *args*
        """

        # split the subdocument_id into its components
        ids = cls.split_id( id )

        # load the MongoDB document and remove the ID from the list of ids
        obj = cls.load_by_id( ids.pop(0), readonly=readonly )

        # loop through each level of proxy using the previous object as the parent
        for (proxy_subclass, id) in zip( args, ids, strict=True ):
            obj = proxy_subclass.get_proxy( obj, id )

        # return the lowest-level object
        return obj


    def proxy_id( self, *args, include_parent_doc_id=False ):
        """Assemble a list of proxy IDs into a single string

        :param include_parent_doc_id: whether to include the
          parent document ID in the resulting ID string
        :type include_parent_doc_id: bool
        :return: One or more proxy IDs separated by `subdoc_key_sep`
        :rtype: str
        """
        if include_parent_doc_id:
            return self.subdoc_key_sep.join( [ self.id(), *args ] )
        else:
            return self.subdoc_key_sep.join( args )


    def save( self, force=False ):
        """
        Intelligent wrapper to insert or replace a document

        A current `_updated` timestamp is added to all documents.

        The first time a document is saved, a `_created` timestamp is added as well.

        If the class defines a non-``None`` `object_version`, this added as `_objver` to
        the document as well.

        1) Documents without an `_id` are inserted into the database; MongoDB will assign the ObjectId
        2) If `force` is set, document will be saved regardless of update time or even if it exists.
           This is useful for upserting documents from another database.
        3) Otherwise, only a database document whose `_id` and `_updated` timestamp
           match this object will be replaced.
           This protects against overwriting documents that have been updated elsewhere.

        :param force: if ``True``, upsert the new document regardless of its `_updated` timestamp
        :type force: bool, optional
        :raises MongoObjectsAuthFailed: if `authorize_save()` has been overriden
          and does not return a truthy value
        """

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
        """Split a subdocument ID into its component document ID and one or more subdocument keys.

        :param subdoc_id: a full subdocument ID starting with a document ObjectId
          followed by one or more subdocument proxy keys separated by `cls.subdoc_key_sep`.
        :type subdoc_id: str
        :returns: A list. The first element of the list is the document ObjectId.
          The remaining elements in the list are subdocument proxy keys.
        :rtype: list
        """
        return subdoc_id.split( cls.subdoc_key_sep )


    @staticmethod
    def utcnow():
        """MongoDB stores milliseconds, not microseconds.
        Drop microseconds from the standard utcnow() so comparisons can be made with database times.

        :returns: The current time with microseconds set to 0.
        :rtype: naive :class:`datetime.datetime`
        """
        now = datetime.utcnow()
        return now.replace( microsecond=(now.microsecond // 1000) * 1000 )



class PolymorphicMongoUserDict( MongoUserDict ):
    """Like MongoUserDict but supports polymorphic document objects within the same collection.

    Each subclass needs to define a unique subclass_key"""

    #: Map subclass_keys to subclasses
    #:
    #: Recommended: Override this with an empty dictionary in the base class
    #: of your subclass tree to create a separate namespace
    subclass_map = {}

    #: Must be unique and non-None for each subclass
    #: Base classes may define this key as well
    #:
    #: :meta hide-value:
    subclass_key = None

    #: Optional. Name of internal key added to each document to record the subclass_key
    subclass_key_name = '_sckey'



    @classmethod
    def __init_subclass__( cls, **kwargs):
        """auto-register every PolymorphicMongoUserDict subclass

        :raises MongoObjectsSubclassError: If a *subclass_key* is duplicated
        """

        super().__init_subclass__(**kwargs)
        try:
            if getattr( cls, 'subclass_key', None ) is not None:
                assert cls.subclass_key not in cls.subclass_map, f"duplicate subclass_key for {type(cls)}"
                cls.subclass_map[ cls.subclass_key ] = cls
        except Exception as e:
            raise MongoObjectsSubclassError( f"PolymorphicMongoUserDict(): unable to register subclass: {e!s}" ) from e


    @classmethod
    def find( cls, filter={}, projection=None, readonly=None, object_version=None, **kwargs ):
        """
        Return matching documents as appropriate subclass instances

        :param filter: as with :func:`MongoUserDict.find`
        :param projection: as with :func:`MongoUserDict.find`
        :param readonly: as with :func:`MongoUserDict.find`
        :param object_version: as with :func:`MongoUserDict.find`
        :returns: a generator for instances of the user-defined :class:`PolymorphicMongoUserDict` subclasses,
          each correct for the document being returned
        :raises MongoObjectsAuthFailed: if `authorize_pre_read()` has been overriden
          and does not return a truthy value
        """

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
            obj = cls.instantiate(doc, readonly=readonly)
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                yield obj


    @classmethod
    def find_one( cls, filter={}, projection=None, readonly=None, object_version=None, no_match=None, **kwargs ):
        """
        Return a single matching document as the appropriate subclass or None

        :param filter: as with :func:`MongoUserDict.find`
        :param projection: as with :func:`MongoUserDict.find`
        :param readonly: as with :func:`MongoUserDict.find`
        :param object_version: as with :func:`MongoUserDict.find`
        :param no_match: as with :func:`MongoUserDict.find_one`
        :returns: an instance of the user-defined :class:`PolymorphicMongoUserDict` subclass
          correct for this document
        :raises MongoObjectsAuthFailed: if `authorize_pre_read()` has been overriden
          and does not return a truthy value
        """

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
            obj = cls.instantiate( doc, readonly=readonly )
            # Authorize reading this particular document object before returning it
            if obj.authorize_read():
                return obj
        return no_match


    @classmethod
    def get_subclass_by_key( cls, subclass_key ):
        """Look up a subclass in the subclass_map by its subclass_key
        If the subclass can't be located, return the base class

        :meta private:
        """
        return cls.subclass_map.get( subclass_key, cls )


    @classmethod
    def get_subclass_from_doc( cls, doc ):
        """Return the correct subclass to represent this document.
        If the document doesn't contain a subclass_key_name value or the value
        doesn't exist in the subclass_map, return the base class

        :meta private:
        """
        return cls.get_subclass_by_key( doc.get( cls.subclass_key_name ) )


    @classmethod
    def instantiate( cls, doc, readonly=False ):
        """Instantiate a PolymorphicMongoUserDict subclass based on the content
        of the provided MongoDB document

        :meta private:
        """
        # Looks like a bug but isn't
        # The first function call determines the correct subclass
        # The second function call populates a new UserDict subclass with data from the document
        return cls.get_subclass_from_doc( doc )( doc, readonly=readonly )


    def save( self, **kwargs ):
        """Add the `subclass_key` to the document and call :func:`MongoUserDict.save`

        :param kwargs: passes to :func:`MongoUserDict.save`
        """
        if self.subclass_key is not None:
            self[ self.subclass_key_name ] = self.subclass_key
        return super().save( **kwargs )




################################################################################
## MongoDB subdocument proxies
################################################################################

class MongoBaseProxy( object ):
    """Base of all other proxy objects. Not intended to be directly subclassed."""

    #: Users must override this to provide the name of the dictionary or list container
    #:
    #: :meta hide-value:
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
    def create_key( cls, parent, subdoc ):
        """
        Create a unique key value for this subdocument.
        The default implementation requests a hex string for the next unique integer
        as saved in the ultimate MongoUserDict parent object.

        Users may override this using data from the subdoc or other methods to generate a unique key.
        It is recommended that the key not be changed once the object is created as it
        will invalidate any existing proxies and any subdocument_id strings.
        """
        return getattr( parent, 'ultimate_parent', parent ).get_unique_key( autosave=False )


    def data( self ):
        """Convenience function to behave similar to UserDict"""
        return self.get_subdoc()


    def get( self, key, default=None ):
        return self.get_subdoc().get( key, default )


    def id( self ):
        return self.proxy_id( include_parent_doc_id=True )


    def items( self ):
        return self.get_subdoc().items()


    def keys( self ):
        return self.get_subdoc().keys()


    def proxy_id( self, *args, include_parent_doc_id=False ):
        """Force the subdocument ID for single proxies to "0". We
        can't use the actual key as we risk exposing the actual
        dictionary key name."""
        return self.parent.proxy_id( self.key, *args, include_parent_doc_id=include_parent_doc_id )


    def setdefault( self, key, default=None ):
        return self.get_subdoc().setdefault( key, default )


    def update( self, values ):
        self.get_subdoc().update( values )


    def save( self ):
        """Saving the subdocument means saving the parent object,
        so we simply pass the save request up the line.
        """
        return self.parent.save()


    def values( self ):
        return self.get_subdoc().values()




class PolymorphicMongoBaseProxy( MongoBaseProxy ):
    """Like MongoBaseProxy but supports polymorphic subdocument objects within the same parent document.

    Each subclass needs to define a unique `proxy_subclass_key`

    Parent objects need to call `get_proxy()` to obtain the correct subclass type"""

    # Map proxy_subclass_keys to subclasses
    # Override this with an empty dictionary in the base class
    # of your subclass tree to create a separate namespace
    proxy_subclass_map = {}

    # Must be unique and non-None for each subclass
    # Base classes may define this key as well
    #:
    #: :meta hide-value:
    proxy_subclass_key = None

    # Name of internal key added to each subdocument to record the proxy_subclass_key
    proxy_subclass_key_name = '_psckey'


    @classmethod
    def __init_subclass__( cls, **kwargs):
        """auto-register every PolymorphicMongoBaseProxy subclass"""
        super().__init_subclass__(**kwargs)
        try:
            if getattr( cls, 'proxy_subclass_key', None ) is not None:
                assert cls.proxy_subclass_key not in cls.proxy_subclass_map, f"duplicate proxy_subclass_key for {type(cls)}"
                cls.proxy_subclass_map[ cls.proxy_subclass_key ] = cls
        except Exception as e:
            raise MongoObjectsSubclassError( f"PolymorphicMongoBaseProxy(): unable to register subclass: {e!s}" ) from e


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        """Add the proxy_subclass_key before passing to the base class create()"""
        if cls.proxy_subclass_key is not None:
            subdoc[ cls.proxy_subclass_key_name ] = cls.proxy_subclass_key
        return super().create( parent, subdoc, autosave=autosave )


    @classmethod
    def get_subclass_by_key( cls, proxy_subclass_key ):
        """Look up a proxy_subclass in the proxy_subclass_map by its proxy_subclass_key
        If the subclass can't be located, return the called class"""
        return cls.proxy_subclass_map.get( proxy_subclass_key, cls )


    @classmethod
    def get_subclass_from_doc( cls, doc ):
        """Return the correct subclass to represent this document.
        If the document doesn't contain a proxy_subclass_key_name value or the value
        doesn't exist in the proxy_subclass_map, return the base class"""
        return cls.get_subclass_by_key( doc.get( cls.proxy_subclass_key_name ) )




class AccessDictProxy( object ):
    """Intended for internal multiple-inheritance use.

    Organize functions to reference subdocuments within a parent MongoDB dictionary.
    Individual subdocuments are stored in a dictionary container.

    Keys must be strings as required by MongoDB documents.

    MongoUserDict.get_unique_key() is a convenient way to generate unique keys
    within a MongoDB document.
    """

    def __init__( self, parent, key ):
        self.parent = parent
        self.ultimate_parent = getattr( parent, 'ultimate_parent', parent )
        self.key = str(key)

        # make sure this key actually exists before we return successfully
        assert self.key in self.get_subdoc_container()


    @classmethod
    def create( cls, parent, subdoc={}, autosave=True ):
        """Add a new subdocument to the container.
        Auto-assign the ID and return the new proxy object"""
        key = cls.create_key( parent, subdoc )

        # insure the container exists before adding the document
        parent.setdefault( cls.container_name, {} )[ key ] = subdoc
        if autosave:
            parent.save()
        return cls.get_proxy( parent, key )



    def delete( self, autosave=True ):
        """Delete the subdocument from the container dictionary.
        Remove the key so the proxy can't be referenced again.
        By default save the parent document.
        """
        del self.get_subdoc_container()[ self.key ]
        if autosave:
            self.parent.save()
        self.key = None


    @classmethod
    def exists( cls, parent, key ):
        '''Return True if the key already exists in the dictionary container

        :param parent: parent document
        :param key: key being queried
        '''
        return key in parent.get( cls.container_name, {} )


    @classmethod
    def get_proxies( cls, parent ):
        return [ cls.get_proxy( parent, key ) for key in parent.get( cls.container_name, {} ).keys() ]


    def get_subdoc( self ):
        """
        Reference the subdocument dictionary in the parent object

        :meta private:
        """
        return self.get_subdoc_container()[ self.key ]


    def get_subdoc_container( self ):
        """
        Reference the container dictionary in the parent object

        :meta private:
        """
        return self.parent.get( self.container_name, {} )




class MongoDictProxy( MongoBaseProxy, AccessDictProxy ):
    """Implement proxy object using a dictionary as a container"""

    @classmethod
    def get_proxy( cls, parent, key ):
        """Return a single proxy object by calling :func:`__init__()`"""
        return cls( parent, key )




class PolymorphicMongoDictProxy( PolymorphicMongoBaseProxy, AccessDictProxy ):
    """Polymorphic version of MongoDictProxy"""

    @classmethod
    def get_proxy( cls, parent, key ):
        """Return a single polymorphic proxy object.
        Determines the correct subclass type and call __init__()"""
        # use an anonymous base-class proxy to get access to the subdocument
        # so that get_subclass_from_doc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        return cls.get_subclass_from_doc( cls( parent, key ) )( parent, key )




class AccessListProxy( object ):
    """Intended for internal multiple-inheritance use.

    Organize functions to reference subdocuments within a parent MongoDB dictionary.
    Individual subdocuments are stored in a list container.

    Since the container object is a list, not a dictionary, we can't use the key
    to look up items directly.

    Instead, we use get_key() to extract a key from a subdocument
    and use the result to determine if a given document matches.

    For convenience, if no key is given but a sequence provided, we initialize the key from
    the subdocument at that index"""

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
        """Add a new subdocument to the container.
        Auto-assign the ID and return the new proxy object
        """
        # Create a unique key for this subdocument
        key = cls.create_key( parent, subdoc )

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
        """Delete the subdocument from the container list.
        Remove the key and sequence so the proxy can't be referenced again.
        By default save the parent document.
        """

        # First make sure the sequence number is accurate
        self.get_subdoc()
        # Then pop that item from the list
        self.get_subdoc_container().pop( self.seq )
        if autosave:
            self.parent.save()
        self.key = self.seq = None


    @classmethod
    def exists( cls, parent, key ):
        '''Return True if the key already exists in the list container

        :param parent: parent document
        :param key: key being queried
        '''
        for subdoc in parent.get( cls.container_name, [] ):
            if cls.get_key( subdoc ) == key:
                return True
        return False


    @classmethod
    def get_key( cls, subdoc ):
        """
        Get the key from a subdocument dictionary.

        :meta private:
        """
        return subdoc[ cls.subdoc_key_name ]


    @classmethod
    def get_proxies( cls, parent ):
        return [ cls.get_proxy( parent, seq=seq ) for seq in range( len( parent.get( cls.container_name, [] ) ) ) ]


    def get_subdoc( self ):
        """
        Reference the subdocument dictionary in the parent object

        :meta private:
        """
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
        """
        Reference the container list in the parent object

        :meta private:
        """
        return self.parent.get( self.container_name, [] )


    @classmethod
    def set_key( cls, subdoc, key ):
        """
        Set the key in a subdocument dictionary

        :meta private:
        """
        subdoc[ cls.subdoc_key_name ] = key




class MongoListProxy( MongoBaseProxy, AccessListProxy ):
    """Implement proxy object using a list as a container"""

    @classmethod
    def get_proxy( cls, parent, key=None, seq=None ):
        """Return a single proxy object. This simply calls __init__()"""
        return cls( parent, key, seq )




class PolymorphicMongoListProxy( PolymorphicMongoBaseProxy, AccessListProxy ):
    """Polymorphic version of MongoListProxy"""

    @classmethod
    def get_proxy( cls, parent, key=None, seq=None ):
        """Return a single proxy object.
        Determine the correct subclass type and call __init__()"""
        # use an anonymous base-class proxy to get access to the subdocument
        # so that get_subclass_from_doc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        return cls.get_subclass_from_doc( cls( parent, key, seq ) )( parent, key, seq )




class AccessSingleProxy( AccessDictProxy ):
    """Intended for internal multiple-inheritance use.

    Organize functions to reference a single subdocument dictionary
    within a parent MongoDB dictionary.

    This is really just AccessDictProxy with the parent MongoDB document as the container.

    Keys must be strings as required by MongoDB documents.
    """

    @classmethod
    def create( cls, parent, subdoc={}, key=None, autosave=True ):
        """Add a new single subdocument dictionary to the parent object.
        No new key is auto-assigned as single subdocuments are assigned to fixed keys.
        The key can be defined in the class as "container_name"
        or overriden in the function call as "key".
        Return the new proxy object.
        """
        if key is None:
            key = cls.container_name
        parent[ key ] = subdoc
        if autosave:
            parent.save()
        return cls.get_proxy( parent, key )


    @classmethod
    def exists( cls, parent, key=None ):
        '''Return True if the key already exists in the parent document

        :param parent: parent document
        :param key: key being queried
        '''
        if key is None:
            key = cls.container_name
        return key in parent


    @classmethod
    def get_proxies( cls, parent ):
        """get_proxies() doesn't make sense for single proxy use."""
        raise Exception( 'single proxy objects do not support get_proxies()' )


    def get_subdoc_container( self ):
        """For a single subdocument dictionary, the container is the parent document."""
        return self.parent


    def proxy_id( self, *args, include_parent_doc_id=False ):
        """Force the subdocument ID for single proxies to "0". We
        can't use the actual key as we risk exposing the actual
        dictionary key name."""
        return self.parent.proxy_id( '0', *args, include_parent_doc_id=include_parent_doc_id )




class MongoSingleProxy( AccessSingleProxy, MongoBaseProxy ):
    """Implement proxy object for a single subdocument dictionary"""

    @classmethod
    def get_proxy( cls, parent, key=None ):
        """Return a single proxy object. This simply calls __init__()"""
        if key is None:
            key = cls.container_name
        return cls( parent, key )




class PolymorphicMongoSingleProxy( AccessSingleProxy, PolymorphicMongoBaseProxy ):
    """Polymorphic version of MongoSingleProxy"""

    @classmethod
    def create( cls, parent, subdoc={}, key=None, autosave=True ):
        """Add the proxy_subclass_key before passing to the base class create()
        AccessSingleProxy needs to be first in the object inheritance to get
        super() to work properly"""
        if cls.proxy_subclass_key is not None:
            subdoc[ cls.proxy_subclass_key_name ] = cls.proxy_subclass_key
        return super().create( parent, subdoc, key=key, autosave=autosave )


    @classmethod
    def get_proxy( cls, parent, key=None ):
        """Return a single proxy object.
        Determine the correct subclass type and call __init__()"""
        # use an anonymous base-class proxy to get access to the subdocument
        # so that get_subclass_from_doc can inspect the data and determine the
        # appropriate subclass.
        # Return a separate proxy object with that class
        if key is None:
            key = cls.container_name
        return cls.get_subclass_from_doc( cls( parent, key ) )( parent, key )



