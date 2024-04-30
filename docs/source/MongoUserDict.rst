MongoUserDict
=============================

Basic Usage
-----------
By subclassing :class:`MongoUserDict` you can manage MongoDB documents with your own
custom classes. :class:`MongoUserDict` is itself a subclass of :class:`UserDict` and
supports all dictionary access methods.

To define your class, provide the :mod:`pymongo` database object and the name of the
collection::

    import mongo_objects

    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'


CRUD Operations
---------------

:mod:`mongo_objects` supports all CRUD (create, read, update, delete) operations.

Create an object by creating an instance of your :class:`MongoUserDict` subclass::

    event = Event( {
        ... document data here ...
    } )

Saving a new object will write it to the database and assign it a MongoDB ObjectId.
*_created* and *_updated* timestamps will also be added to the document::

    event.save()

To load multiple documents, use the familiar :func:`.find` function. Filter, template
and other arguments are passed to the underlying :func:`pymongo.find`.
The resulting documents are returned as instances of your :class:`MongoUserDict` document
subclass::

    for event in Event.find():
        ...

Single documents may be loaded with :func:`.find_one`::

    event = Event.find_one()

:func:`.load_by_id` is a convenience function to load a document by its MongoDB ObjectId.
The method accepts either a string or BSON ObjectId::

    event = Event.load_by_id( '662b0d705a4c657820625300' )

To update an document, simply update the instance of your document class with
the usual methods for modifying dictionaries and then :func:`.save` it.
For existing documents (i.e. documents that already have a MongoDB ObjectId),
:func:`.save` automatically uses :func:`pymongo.find_one_and_replace` to update the existing
document in place.

To prevent overwriting modified data, :func:`.save` will only replace objects that haven't
already been modified in the database.
See the :func:`.save` function reference for more details on this behavior.

:func:`.save` updates the *_updated* timestamp to the current UTC time for all objects
successfully saved. ::

    event['new-key'] = 'add some content to the object'
    event.save()

Deleting an object is accomplished with the :func:`.delete` method. The document is deleted from
the database and the ObjectId is removed from the in-memory object. If the object is
saved again, it will be treated as a new document. ::

    event.delete()


Read-Only Documents
-------------------

It is possible to use projections that return incomplete documents
that can't be safely be saved by :mod:`mongo_objects` without data loss.
:mod:`mongo_objects` doesn't attempt to determine whether a projection
is safe or not.

The :func:`.find` and :func:`.find_one` methods accept a *readonly* keyword argument with
three potential values:

* ``None`` (default): All documents created with a projection are marked readonly.
  All other documents are considered read-write.
* ``True``: The documents will be marked as readonly.
* ``False``: The documents will be considered read-write.
  This is a potentially dangerous choice. With great power comes great responsibility.

:func:`.save` refuses to save a readonly object and raises a :exc:`MongoObjectsReadOnly`
exception instead.


Document IDs
------------

Once a document has been saved and an ObjectId assigned by MongoDB, the :func:`.id`
method returns a string representation of the ObjectId.

:func:`.load_by_id` may be used to load a specific document by its ObjectId or
by the string returned by :func:`.id`::

    # load a random document
    event = Event.find_one()

    # save the ObjectId for later
    eventId = event.id()

    ... time passes ...

    # reload the document from its ObjectId
    event_again = Event.load_by_id( eventId )

ObjectIds are represented as lowercase hex digits, so the result of :func:`.id`
is safe to use in URLs.


Authorization
-------------

:mod:`mongo_objects` does not implement any authorization itself, but does provide
the following hooks that the user may override to implement access control over
each CRUD action.

Create
~~~~~~

Creating new objects is authorized by the :func:`.authorize_init` method. The function
may inspect the contents of the document to see if creating it is allowed. Since
reading documents from the database also involves creating a new object, this
function will also be called for each :func:`.find` and :func:`.find_one` document as well.
If the function does not return ``True``, a :exc:`MongoObjectsAuthFailed` exception is raised.

Read
~~~~

There are two read hooks:

:func:`.authorize_pre_read` is a classmethod that is called once per :func:`.find`
or :func:`.find_one` call before any data is read. If the function does not return
``True``, a :exc:`MongoObjectsAuthFailed` exception is raised.

:func:`.authorize_read` is called after a document is read but before the data is
returned to the user. The function may inspect to contents of the document to see
if the user is permitted to access this particular document. If :func:`.authorize_read` does not
return ``True``, the document will be suppressed. For :func:`.find_one`, if the first
document found is suppressed, ``None`` will be returned. No additional
(potentially authorized) documents will be evaluated.

Update
~~~~~~

:func:`.authorize_save` is called by :func:`.save` before new or updated documents
are saved. If the function does not return ``True``, a :exc:`MongoObjectsAuthFailed`
exception is raised.

Delete
~~~~~~

:func:`.authorize_delete` is called by :func:`.delete` before a document is deleted.
If the function does not return ``True``, a :exc:`MongoObjectsAuthFailed` exception is raised.



Object Versions
---------------

:mod:`mongo_objects` supports an optional document schema versioning system. To enable this
functionality, provide an *object_version* value when defining the class::

    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'
        object_version = 3

The current *object_version* will automatically be added by :func:`.save` to each document as *_objver*.

By default :func:`.find` and :func:`.find_one` will then automatically adjust each query
to restrict the results to the current *object_version*. This guarantees that only objects
at the current object version will be returned. This is equivalent to the following::

    Event.find( {
        ... other filters ...,
        '_objver' : Event.object_version
        } )

To manage this functionality, :func:`.find` and :func:`.find_one`
accept an optional *object_version* parameter with the following meaning:

* ``None`` (default): documents will automatically be filtered to the current *object_version*
* ``False``: no filtering for object version will be performed
* any other value: only documents with this value as the object version will be returned

Object versioning provides a convenient workflow for migrating database schemas
and protecting the application from inadvertently reading data in an obsolete format.
First increment the *object_version* of the :class:`MongoUserDict` document subclass,
then loop through all objects at the previous version and perform the migration.

For example, to update the layout of the object defined above::

    # object_version is now 4
    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'
        object_version = 4

    # loop through all objects at version 3
    for event in Event.find( object_version=3 ):
        ... perform migration steps ...

        # saving the document object automatically updates _objver
        # to the current value
        event.save()


Polymorphism
------------

Subclass the :class:`PolymorphicMongoUserDict` class to enable :mod:`mongo_objects` support
for polymorphic user document classes. Specifically, from the same MongoDB collection
:func:`.find` and :func:`.find_one` will return instances of different document classes.

Each polymorphic subclass defines a separate key which :func:`.save` adds to the document.
When the document is read back from the database, the key is compared to a list of
potential classes and the correct instance type returned.

Note the recommendation to define an empty *subclass_map* so each set of
polymorphic classes use their own namespace for subclass keys. ::

    import mongo_objects

    # create a base class for the collection
    class Event( mongo_objects.PolymorphicMongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'

        # Recommended: define an empty subclass_map in the base class
        # This creates a separate namespace for the polymorphic
        # subclass keys.
        # Otherwise, subclasses will share the PolymorphicMongoUserDict
        # subclass namespace and risk collisions with other subclasses
        # from other collections.
        subclass_map = {}

        .. your generally useful event functions ...

    # now create subclasses for each object variation
    # each subclass requires a unique key
    class OnSiteEvent( Event ):
        subclass_key = 'onsite'

        .. your onsite-specific event functions ...

    class OnlineEvent( Event ):
        subclass_key = 'online'

        .. your online-specific event functions ...

    class HybridEvent( Event ):
        subclass_key = 'hybrid'

        .. your hybrid-specific event functions ...

Create and save the objects using a subclass. :func:`.save` automatically
adds the appropriate subclass key to the document. ::

    hybrid = HybridEvent()
    hybrid.save()
    # save the document ID for later
    hybridId = hybrid.id()

Load documents from the base class. The resulting object will be an instance
of the correct subclass based on the subclass key. ::

    # event is an instance of HybridEvent
    event = Event.load_by_id( hybridId )

If the document has a missing or invalid subclass key, an instance of the
base class is returned.


Proxy Support
-------------

:class:`MongoUserDict` seamlessly supports the subdocument proxy objects also
included in this module.

:func:`get_unique_integer` provides per-document unique integer values.

:func:`get_unique_key` uses these unique integers to create unique string
values suitable for subdocument proxy keys.

:func:`split_id` separates a full subdocument ID value into its components:
a parent document ObjectId plus one or more proxy keys.

:func:`load_proxy_by_id` accepts a subdocument ID and a list of one or more
proxy classes. The parent document is loaded and the proxy objects are
instantiated. See :class:`MongoDictProxy` and :class:`MongoListProxy` for more
details.


Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoUserDict
    :special-members: __init__
    :members:

.. autoclass:: PolymorphicMongoUserDict
    :special-members: __init__
    :members:
