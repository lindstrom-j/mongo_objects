MongoSingleProxy
=============================

Data Structure
--------------

A :class:`MongoDictProxy` is suitable to manage a single subdocument
as shown in the following structure. See Proxy Overview for a list of all
supported data structures. ::

    {                           # parent document
        '_id' : ...,
                                # no container dictionary or list
        'venue' : {
            ...                 # subdocument with key 'venue'
            },
    }

This data structure can be accessed as::

    class Venue( mongo_objects.MongoSingleProxy ):
        container_name = 'venue'

    class Events( mongo_objects.MongoUserDict ):
        collection_name = 'events'
        database = ... pymongo database connection object ...


Proxy Keys
----------

Assigning Key on Create
~~~~~~~~~~~~~~~~~~~~~~~~

The subdocument proxy key is the actual dictionary key used to identify
the subdocument in the parent dictionary. Since there is no separate container,
this is usually the parent document itself.

The key is usually defined in the class with `container_name`. However, for
utility classes (perhaps address, phone number or currency amount), the data
may occur in multiple locations. In that case, a key name can be provided to the
constructor or :func:`get_proxy`::

    alternate_venue = Venue( event, 'alternate' )


Subdocument IDs
~~~~~~~~~~~~~~~

Since the proxy key is an actual dictionary key in our document schema, it is not
necessarily safe to share with users in a URL, for example. To protect against
data schema leakage, the :func:`id` function always uses ``"0"`` when constructing
subdocument IDs for :class:`MongoSingleProxy` instances.

Since the *container_name* is typically provided in the class definition,
:func:`load_proxy_by_id` can create these proxies without problem. ::

    class Event( mongo_objects.MongoUserDict ):

        @classmethod
        def load_venue_by_id( cls, venueId ):
            return cls.load_proxy_by_id( venueId, Venue )


:func:`get_proxies`
~~~~~~~~~~~~~~~~~~~

Since :class:`MongoSingleProxy` by definition is a single subdocument, the
:func:`get_proxies` function is not supported and raises an :exc:`Exception`.


Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoSingleProxy
    :special-members: __init__
    :members:
    :inherited-members:

.. autoclass:: PolymorphicMongoSingleProxy
    :special-members: __init__
    :members:
    :inherited-members:
