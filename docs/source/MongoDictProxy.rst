MongoDictProxy
==============


Data Structure
--------------

A :class:`MongoDictProxy` is suitable to manage a dictionary of subdocuments
as shown in the following structure. See Proxy Overview for a list of all
supported data structures. ::

    {                           # parent document
        '_id' : ...,
        'ticketTypes' : {       # container is a dictionary
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

This data structure can be accessed as::

    class TicketTypes( mongo_objects.MongoDictProxy ):
        container_name = 'ticket_types'

    class Events( mongo_objects.MongoUserDict ):
        collection_name = 'events'
        database = ... pymongo database connection object ...


Proxy Keys
----------

Assigning Keys on Create
~~~~~~~~~~~~~~~~~~~~~~~~

The subdocument proxy key is the actual dictionary key used to identify
the subdocument in the containing dictionary.

We recommend using the built-in system of auto-assigning
unique integers as proxy keys. While it is tempting to generate the key
from something in the content of the subdocument, this means changing
keys when the subdocument changes. Changing keys invalidates already existing
proxy objects as well as any subdocument IDs already published as URLs.


Validating Keys
~~~~~~~~~~~~~~~

Proxy keys must already exist when creating objects by constructor or by :func:`get_proxy`.
To create a new object and assign a new key, use :func:`create`. ::

    freds_ticket = Ticket( event, '1' )
    sallys_ticket = Ticket.get_proxy( event, '2' )



Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoDictProxy
    :special-members: __init__
    :members:
    :inherited-members:

.. autoclass:: PolymorphicMongoDictProxy
    :special-members: __init__
    :members:
    :inherited-members:

