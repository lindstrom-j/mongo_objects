MongoUserDict
=============================

Typical Use Case
----------------
By subclassing ``MongoUserDict`` you can manage MongoDB documents with your own
custom classes. ``MongoUserDict`` is itself a subclass of ``UserDict`` and
supports all dictionary access methods.

To define you class, provide the pymongo database object and the name of the
collection::

    import mongo_objects

    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'


CRUD Operations
---------------

``mongo_objects`` supports all CRUD (create, read, update, delete) operations

Create an object by creating an instance of your ``MongoUserDict`` subclass::

    event = Event( {
        ... document data here ...
    } )

Saving a new object will write it to the database and assign it a MongoDB ObjectId.
``_created`` and ``_updated`` timestamps will also be added to the document::

    event.save()

To load multiple documents, use the familiar ``find()`` method. Filter, template
and other arguments are passed to the underlying ``pymongo.find()`` method.
The resulting documents are returned as instances of your MongoUserDict subclass::

    for event in Event.find():
        ...

Single documents may be loaded with ``find_one()``::

    event = Event.find_one()

``load_by_id()`` is a convenience function to load a document by its MongoDB ObjectId.
The method accepts either a string or BSON ObjectId::

    event = Event.load_by_id( '662b0d705a4c657820625300' )

To update an document, simply update the instance of your document class using all
the usual methods for modifying dictionaries. For existing documents (i.e. documents
that already have a MongoDB ObjectId),
``save()`` automatically uses ``pymongo.find_one_and_replace()`` to update the existing
document in place.

To prevent overwriting modified data, ``save()`` will only replace objects that haven't
already been modified in the database.
See the ``save()`` function reference for more details on this behavior.

``save()`` updates the ``_updated`` timestamp to the current UTC time for all objects
successfully saved.::

    event['new-key'] = 'add some content to the object'
    event.save()

Deleting an object is accomplished with the ``delete()`` method. The document is removed from
the database and the ObjectId is removed from the in-memory object. If the object is
saved again, it will be treated as a new document.::

    event.delete()


Read-Only Documents
-------------------

It is possible to use projections that return incomplete documents that can't be safely
saved without data loss. ``mongo_objects`` doesn't attempt to determine whether a projection
is safe or not.

The ``find()`` and ``find_one()`` methods accept a ``readonly`` keyword argument with
three potential values:

* ``None`` (the default): All documents created with a projection are marked readonly. All other documents are considered read-write.
* ``True``: The documents will be marked as readonly.
* ``False``: The documents will be considered read-write. This is a potentially dangerous choice. With great power comes great responsibility.

``save()`` will refuse to save a readonly object and raise a ``MongoObjectsReadOnly``
exception instead.


Document IDs
------------

Once a document has been saved and an ObjectId assigned by MongoDB, the ``id()``
method returns a string representation of the ObjectId.

``load_by_id()`` may be used to load a specific document by its ObjectId or
the string returned by ``id()``::

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

**Create**

Creating new objects is authorized by the ``authorize_init()`` method. The function
may inspect the contents of the document to see if creating it is allowed. Since
reading documents from the database also involves creating a new object, this
function will be called for each ``find()`` and ``find_one()`` document as well.
If the function does not return ``True``, a ``MongoObjectsAuthFailed`` exception is raised.

**Read**

There are two read hooks:

``authorize_pre_read()`` is a ``classmethod`` that is called once per ``find()``
or ``find_one()`` call before any data is read. If the function does not return
``True``, a ``MongoObjectsAuthFailed`` exception is raised.

``authorize_read()`` is called after a document is read but before the data is
returned to the user. The function may inspect to contents of the document to see
if the user is permitted to access the data. If ``authorize_read()`` does not
return ``True``, the document will be suppressed. For ``find_one()``, if the first
document found is suppressed, ``None`` will be returned. No additional
(potentially authorized) documents will be evaluated.

**Update**

``authorize_save()`` is called by ``save()`` before new or updated documents
are saved. If the function does not return ``True``, a ``MongoObjectsAuthFailed``
exception is raised.

**Delete**

``authorize_delete()`` is called by ``delete()`` before a document is deleted.
If the function does not return ``True``, a ``MongoObjectsAuthFailed`` exception is raised.



Object Versions
---------------

``mongo_objects`` supports an optional object schema versioning system. If 

Polymorphism
------------

Proxy Support
-------------

Advanced Considerations
-----------------------

Overriding separator or key

Method Reference
----------------

save():
if the ``_updated``
timestamp in the current object matches the ``_updated`` timestamp in the database. A
``MongoObjectsDocumentModified`` exception is raised if the ``_updated`` timestamps don't match.