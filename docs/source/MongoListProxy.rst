MongoListProxy
=============================

Data Structure
--------------

A :class:`MongoListProxy` manages a **list** of subdocuments
as shown in the following structure. See :doc:`proxy_overview` for a list of all
supported data structures. ::

    {                              # parent document
        '_id' : ...,
        'tickets' : [              # container is a list
            {
                '_sdkey' : '1',    # subdocument with key '1'
                ...
            },
            {
                '_sdkey' : '2',    # subdocument with key '2'
                ...
            },
            {
                '_sdkey' : '3',    # subdocument with key '3'
                ...
            },
        ],
    }

This data structure can be accessed as::

    class Tickets( mongo_objects.MongoListProxy ):
        container_name = 'tickets'

    class Events( mongo_objects.MongoUserDict ):
        collection_name = 'events'
        database = ... pymongo database connection object ...


Proxy Keys
----------

Assigning Keys on Create
~~~~~~~~~~~~~~~~~~~~~~~~

Python lists don't natively use keys to access content, so the
subdocument proxy key is added to each subdocument dictionary
under the key `_sdkey`.

We recommend using the built-in system of auto-assigning
unique integers as proxy keys to avoid changing keys and
invalidating existing documents or URLs.

Locating Subdocuments
~~~~~~~~~~~~~~~~~~~~~

It is too slow to iterate through the list of subdocuments on every
access to find the correct key. :class:`MongoListProxy` makes the
following look-up optimization.

Each proxy object stores both the key and a sequence number representing
the list index that held that key during the most recent data access.

1) When accessing the proxy object, the subdocument at the currently
   saved sequence number is examined. If the key matches the key for
   the proxy object, that subdocument is immediately returned.

2) Otherwise, the list is rescanned from the front until a subdocument is
   located with the correct proxy key. Once the key is located, the sequence
   number is stored as a hint for next time and the subdocument
   at the sequence location is returned.

Initializing Objects
~~~~~~~~~~~~~~~~~~~~

:meth:`__init__` accepts three arguments, `parent`, `key` and `seq`. `parent`
is required. At least one of `key` and `seq` must also be provided.

# If only `key` is provided, the key is saved in the object. No validation is
  performed. The first time the proxy is accessed, the list will be scanned for
  the correct subdocument.

# If only `seq` is provided, the key for the subdocument currently at that location
  in the list is saved as the proxy key. The `seq` value is saved as a hint for
  the next access. If the list changes, the proxy key will be located again and
  the sequence number updated.

# If both `key` and `seq` are provided, the key is saved in the proxy object but
  not validated. The sequence number is saved as a hint for the next access
  and will be validated at that time.


Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoListProxy
    :special-members: __init__
    :members:
    :inherited-members:

Polymorphic Class Reference
---------------------------

Polymorphic proxies are supported by :class:`PolymorphicMongoListProxy`. All the
attributes and methods of :class:`MongoListProxy` are supported with the following
overrides.

.. autoclass:: PolymorphicMongoListProxy
    :special-members: __init__
    :members:

