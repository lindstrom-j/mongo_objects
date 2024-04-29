MongoDictProxy
==============

Data Structure
--------------

A :class:`MongoDictProxy` is suitable to manage a dictionary of subdocuments
as shown in the following structure::

    {                           # parent document
        '_id' : ...,
        'container' : {         # dictionary containing the subdocuments
            '1' : {
                ...             # subdocument with key '1'
                },
            '2' : {
                ...             # subdocument with key '2'
                },
            '3' : {
                ...             # subdocument with key '3'
                },
        },
    }

This data structure can be represented by::

    class MyDocument( mongo_objects.MongoUserDict ):
        collection_name = ...
        database = ...

    class MySubdocument( mongo_objects.MongoDictProxy ):
        container_name = 'container'



CRUD Operations
---------------

Since the subdocument data is proxied from the parent document,
the parent document object must exist first::

    my_doc = MyDocument()

Create
~~~~~~

Now we can create new subdocuments within the parent document.
Unique keys will be auto-assigned for each subdocument. ::

    a = MySubdocument.create( my_doc, { ... first subdoc data } )
    b = MySubdocument.create( my_doc, { ... second subdoc data } )
    c = MySubdocument.create( my_doc, { ... third subdoc data } )

Read
~~~~

If we know the proxy key, we can create an instance directly from the parent.
Keys are validated to make sure they actually exist within the container dictionary. ::

    d = MySubdocument( my_doc, '1' )

We can also use :func:`get_proxy`. This is required for :class:`PolymorphicMongoDictProxy`
subclasses in order to get the correct subclass type::

    e = MySubdocument.get_proxy( my_doc, '2' )

:func:`get_proxies` allows us to loop through all the proxies in a container::

    for f in MySubdocument.get_proxies():
        ...

Subdocuments have their own unique, URL-safe IDs. By default, the proxy subdocument
key is appended to the parent document ObjectId. This ID can be used to recreate
the proxy from the parent object.

Since the data for a proxy only exists in the parent document, :func:`load_proxy_by_id`
first loads the parent document and then uses the given class to instantiate
the subdocument proxy::

    subdocId = e.id()

    q = MyDocument.load_proxy_by_id( subdocId, MySubdocument )

It is safe to nest multiple levels of proxies. Provide the full set of subdocument
classes to :func:`load_proxy_by_id` starting with the topmost proxy. ::

    MyDocument.load_proxy_by_id(
        subdocId,
        OutermostProxyLevel1,
        ProxyLevel2,
        ...,
        InnermostProxyLevel
        )


Update
~~~~~~

Use any standard method of modifying a dictionary to update the data in a proxy
object. Call the :func:`save` function to save the subdocument. This in turn
calls :func:`MongoUserDict.save` to save the parent document to the database. ::

    g = MySubdocument( my_doc, '3' )
    g['z'] = "new string"
    g.update( { 'y' : 1, 'x' : 2.0, 'w' : False } )
    g.setdefault( 'v', 0 )

    g.save()


Delete
~~~~~~

Use :func:`delete` to delete a subdocument. By default the parent document
is saved so the database is updated immediately. ::

    h = MySubdocument( my_doc, '3' )
    h.delete()


Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoDictProxy
    :special-members: __init__
    :members:

.. autoclass:: PolymorphicMongoDictProxy
    :special-members: __init__
    :members:

