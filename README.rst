*************
mongo_objects
*************

A lightweight wrapper around pymongo to access MongoDB documents and subdocuments through custom user-defined classes.

Documents are returned as UserDict subclasses:

* convenient pass-through to ``find()`` and ``find_one()``
* convenient ``load_by_id()`` to locate documents by ObjectId
* smart ``save()`` function to insert, upsert or replace documents as appropriate
* automatically record document creation and update times
* track separate object schema versions
* support polymorphic user objects loaded from the same collection

Subdocuments are accessed through dictionary proxy objects:

* returned as their own classes independent of the parent MongoDB document class
* data access is proxied back to the parent so no separate database access is performed
* subdocuments have their own unique URL-safe ID useful for loading the data
* subdocuments can be grouped in either dictionary or list containers
* polymorphic subdocuments are supported within the same container
* using subdocuments avoids "JOIN-like" additional database queries across collections


Example
=======

Imagine an event ticketing system with a single MongoDB collection containing documents like the following::

    {
        'name' : 'Fabulous Event',
        'date' : '...',      # datetime
        'desc' : 'This will be a lot of fun'
        'ticketTypes' : {
            '1' : {
                'name' : 'VIP Ticket',
                'desc' : 'Front-row seating; comes with a free plushie',
                'cost' : 200,
                'quantity' : 10,
            },
            '2' : {
                'name' : 'General Seating',
                'desc' : 'Everyone is welcome!',
                'cost' : 100,
                'quantity' : 100,
            },
        },
        'tickets' : [
            {
                'holder' : 'Fred',
                'purchased' : '...'      # datetime
                'ticketType' : 2,
            },
            {
                'holder' : 'Susan',
                'purchased' : '...'      # datetime
                'ticketType' : 1,
            },
        ]
    }


MongoUserDict
-------------

``mongo_objects`` allows us to create our own class for viewing these event documents::

    class Event( mongo_objects.MongoUserDict ):

        db = ...     # provide your MongoDB database object here
        collection_name = 'events'

        def isFuture( self ):
            return self['date'] >= datetime.utcnow()

Loop through all events::

    for event in Event.find():
        ...

Create a new event::

    myevent = Event( {
        'name' : '...',
        'date' : '...',
    } )
    myevent.save()

Record the unique ID (ObjectId) of an event::

    eventId = myevent.id()

Locate an event by its ID::

    myevent = Event.load_by_id( eventId )

Call a method on our custom object::

    myevent.isFuture()



MongoDictProxy
--------------

``mongo_objects`` allows us to create additional proxy classes for managing subdocuments. The proxy classes
behave like dictionaries but redirect all access back to the parent MongoUserDict object. No additional
database access is performed.::

    class TicketTypes( mongo_objects.MongoDictProxy ):
        container_name = 'ticketTypes'

First load an Event document object::

    event = Event.find_one()

Loop through the existing ticket type subdocuments within the parent ``Event``::

    for tt in TicketTypes.get_proxies( event ):
        ...

Obtain a specific proxy by key::

    tt = TicketType.get_proxy( event, '1' )

Get the unique ID of a proxy item::

    ticket_type_id = tt.id()

Loading a proxy object by ID is a classmethod of the parent document class;
the proxy can only exist once the parent document is loaded::

    tt = Event.load_proxy_by_id( ticket_type_id, TicketTypes )

Create a new ticket type. A unique per-document key will be assigned automatically::

    TicketType.create( event, {
        'name' : 'Student Ticket',
        'desc' : 'For our student friends',
        'cost' : 50,
        'quantity' : 25,
    } )


Credits
-------

Development sponsored by `Headwaters Entrepreneurs Pte Ltd <https://headwaters.com.sg>`_.

Originally developed by `Frontier Tech Team LLC <https://frontiertechteam.com>`_
for the `Wasted Minutes <https://wasted-minutes.com>`_ ™️ language study tool.


License
-------
mongo_objects is made available to the community under the "MIT License".
