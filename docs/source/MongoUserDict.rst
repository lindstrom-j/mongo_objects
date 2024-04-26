MongoUserDict
=============================

Basic Usage
-----------
By subclassing ``MongoUserDict`` you can manage MongoDB documents with your own
custom classes. ``MongoUserDict`` is itself a subclass of ``UserDict`` and
supports all dictionary access methods.

To define your class, provide the pymongo database object and the name of the
collection::

    import mongo_objects

    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'


CRUD Operations
---------------

``mongo_objects`` supports all CRUD (create, read, update, delete) operations.

Create an object by creating an instance of your ``MongoUserDict`` subclass::

    event = Event( {
        ... document data here ...
    } )

Saving a new object will write it to the database and assign it a MongoDB ObjectId.
``_created`` and ``_updated`` timestamps will also be added to the document::

    event.save()

To load multiple documents, use the familiar ``find()`` function. Filter, template
and other arguments are passed to the underlying ``pymongo.find()``.
The resulting documents are returned as instances of the MongoUserDict document
subclass::

    for event in Event.find():
        ...

Single documents may be loaded with ``find_one()``::

    event = Event.find_one()

``load_by_id()`` is a convenience function to load a document by its MongoDB ObjectId.
The method accepts either a string or BSON ObjectId::

    event = Event.load_by_id( '662b0d705a4c657820625300' )

To update an document, simply update the instance of your document class with
the usual methods for modifying dictionaries and then ``save()`` it.
For existing documents (i.e. documents that already have a MongoDB ObjectId),
``save()`` automatically uses ``pymongo.find_one_and_replace()`` to update the existing
document in place.

To prevent overwriting modified data, ``save()`` will only replace objects that haven't
already been modified in the database.
See the ``save()`` function reference for more details on this behavior.

``save()`` updates the ``_updated`` timestamp to the current UTC time for all objects
successfully saved.::

    event['new-key'] = 'add some content to the object'
    event.save()

Deleting an object is accomplished with the ``delete()`` method. The document is deleted from
the database and the ObjectId is removed from the in-memory object. If the object is
saved again, it will be treated as a new document.::

    event.delete()


Read-Only Documents
-------------------

Projections that return incomplete documents that can't be safely be
saved by ``mongo_objects`` without data loss.
``mongo_objects`` doesn't attempt to determine whether a projection
is safe or not.

The ``find()`` and ``find_one()`` methods accept a ``readonly`` keyword argument with
three potential values:

* ``None`` (default): All documents created with a projection are marked readonly. All other documents are considered read-write.
* ``True``: The documents will be marked as readonly.
* ``False``: The documents will be considered read-write. This is a potentially dangerous choice. With great power comes great responsibility.

``save()`` refuses to save a readonly object and raises a ``MongoObjectsReadOnly``
exception instead.


Document IDs
------------

Once a document has been saved and an ObjectId assigned by MongoDB, the ``id()``
method returns a string representation of the ObjectId.

``load_by_id()`` may be used to load a specific document by its ObjectId or
by the string returned by ``id()``::

    # load a random document
    event = Event.find_one()

    # save the ObjectId for later
    eventId = event.id()

    ... time passes ...

    # reload the document from its ObjectId
    event_again = Event.load_by_id( eventId )

ObjectIds are represented as lowercase hex digits, so the result of ``id()``
is safe to use in URLs.


Authorization
-------------

``mongo_objects`` does not implement any authorization itself, but does provide
the following hooks that the user may override to implement access control over
each CRUD action.

Create
~~~~~~

Creating new objects is authorized by the ``authorize_init()`` method. The function
may inspect the contents of the document to see if creating it is allowed. Since
reading documents from the database also involves creating a new object, this
function will also be called for each ``find()`` and ``find_one()`` document as.
If the function does not return ``True``, a ``MongoObjectsAuthFailed`` exception is raised.

Read
~~~~

There are two read hooks:

``authorize_pre_read()`` is a ``classmethod`` that is called once per ``find()``
or ``find_one()`` call before any data is read. If the function does not return
``True``, a ``MongoObjectsAuthFailed`` exception is raised.

``authorize_read()`` is called after a document is read but before the data is
returned to the user. The function may inspect to contents of the document to see
if the user is permitted to access this particular document. If ``authorize_read()`` does not
return ``True``, the document will be suppressed. For ``find_one()``, if the first
document found is suppressed, ``None`` will be returned. No additional
(potentially authorized) documents will be evaluated.

Update
~~~~~~

``authorize_save()`` is called by ``save()`` before new or updated documents
are saved. If the function does not return ``True``, a ``MongoObjectsAuthFailed``
exception is raised.

Delete
~~~~~~

``authorize_delete()`` is called by ``delete()`` before a document is deleted.
If the function does not return ``True``, a ``MongoObjectsAuthFailed`` exception is raised.



Object Versions
---------------

``mongo_objects`` supports an optional document schema versioning system. To enable this
functionality, define an ``object_version`` value when defining the class::

    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'
        object_version = 3

The current ``object_version`` will automatically be added by ``save()`` to each document as ``_objver``.

In addition, by default ``find()`` and ``find_one()`` will automatically adjust each filter
to restrict the results to the current ``object_version``. This guarantees that only objects
at the current object version will be returned. This is equivalent to the following::

    Event.find( {
        ... other filters ...,
        '_objver' : Event.object_version
        } )

``find()`` and ``find_one()`` accept an optional ``object_version`` parameter with the following meaning:

* ``None`` (default): documents will automatically be filtered to the current ``object_version``
* ``False``: no filtering for object version will be performed
* any other value: only documents with this value as the object version will be returned

Object versioning provides a convenient workflow for migrating database schemas
and protecting the application from inadvertently reading data in an obsolete format.
First increment the ``object_version`` of the ``MongoUserDict`` document subclass,
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

Proxy Support
-------------

Advanced Considerations
-----------------------

.. Overriding separator or key

Method Reference
----------------

..
    save():
    if the ``_updated``
    timestamp in the current object matches the ``_updated`` timestamp in the database. A
    ``MongoObjectsDocumentModified`` exception is raised if the ``_updated`` timestamps don't match.