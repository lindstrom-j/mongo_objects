MongoSingleProxy
=============================

Data Structure
--------------

A :class:`MongoDictProxy` manages a **single subdocument**
as shown in the following structure. See :doc:`proxy_overview` for a list of all
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

The same :class:`MongoSingleProxy` proxy definition may be used
as a subdocument in multiple document collections,
for example, an *Address* subdocument used in the
Customer, Vendor and Employee collections.


Proxy Keys
----------

Assigning Key on Create
~~~~~~~~~~~~~~~~~~~~~~~~

The subdocument proxy key is the actual dictionary key used to identify
the subdocument in the parent dictionary. Since there is no separate container,
this is usually the parent document itself.

The key is defined in the class as `container_name`. To keep the parallel with
:class:`MongoDictProxy` and :class:`MongoListProxy`, :meth:`MongoSingleProxy.get_proxy` accepts
a `key` argument when initializing a new proxy object but it is ignored.


Subdocument IDs
~~~~~~~~~~~~~~~

Since the proxy key is an actual dictionary key in our document schema, it is not
necessarily safe to share with users in a URL, for example. To protect against
data schema leakage, the :meth:`id` and
:meth:`proxy_id` methods always use ``"0"``
when constructing subdocument IDs for :class:`MongoSingleProxy` instances.

Since the *container_name* is provided in the class definition,
:meth:`.load_proxy_by_id` can create these proxies without problem. ::

    class Event( mongo_objects.MongoUserDict ):

        @classmethod
        def load_venue_by_id( cls, venueId ):
            return cls.load_proxy_by_id( venueId, Venue )


:meth:`get_proxies`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since :class:`MongoSingleProxy` by definition is a single subdocument, the
:meth:`get_proxies` method is not supported
and raises an :exc:`Exception`.


Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoSingleProxy
    :special-members: __init__
    :members:
    :inherited-members:

Polymorphic Class Reference
---------------------------

Polymorphic proxies are supported by :class:`PolymorphicMongoSingleProxy`. All the
attributes and methods of :class:`MongoSingleProxy` are supported with the following
overrides.

.. autoclass:: PolymorphicMongoSingleProxy
    :special-members: __init__
    :members:
