Proxy Overview
==============

:mod:`mongo_objects` provides proxy classes to manage MongoDB subdocuments
(sub-dictionaries) as their own custom classes.
Proxying offers several advantages:

* Once the parent document is loaded, no additional database access is required
  to access the subdocuments
* No data is copied from parent to proxy, so the parent document remains
  the single source of truth
* All proxies built from the same parent document object refer to the same
  in-memory data reducing the risk of duplicate, inconsistent objects.
* Proxy subdocument classes organize the methods required for the subdocument
  separate from methods for the parent document itself

Note that *parent* here refers to the top-level MongoDB document that may contain
various levels of subdocuments. No object oriented inheritance between the
top-level document and subdocument classes is implied.


Proxy Data Structures
---------------------

:mod:`mongo_objects` supports three different types of proxies. See the specific
class documentation for usage details.

* :class:`MongoDictProxy` uses a **dictionary** to contain a group of related subdocuments::

    {                     # parent document
        {                 # container is a dictionary
            { ... },      # proxies point to individual subdocuments
            { ... },
        }
    }

* :class:`MongoListProxy` uses a **list** to contain a group of related subdocuments::

    {                     # parent document
        [                 # container is a list
            { ... },      # proxies point to individual subdocuments
            { ... },
        ]
    }

* :class:`MongoSingleProxy` references a **single** subdocument as its own class::

    {                     # parent document
                          # no container; the subdocument is a direct
                          # member of the parent document
        { ... },          # proxy points to a single subdocument
    }

You can create as many proxies as needed to describe the data structure of
your document. Proxies can also be nested to access subdocuments within
subdocuments.

The same proxy may be used as a subdocument in multiple document collections,
for example, a :class:`MongoSingleProxy` *Address* subdocument might used in the
Customer, Vendor and Employee collections.


CRUD Operations
---------------

All :mod:`mongo_objects` proxy classes support the full set of CRUD operations.

We'll use the following classes from the sample code to demonstrate
CRUD operations on all proxy types. ::

    # Subdocument classes are typically defined first
    # so the parent document class can reference them
    class TicketType( mongo_objects.MongoDictProxy ):
        container_name = 'ticket_types'

    class Ticket( mongo_objects.MongoListProxy ):
        container_name = 'tickets'

    class Venue( mongo_objects.MongoSingleProxy ):
        container_name = 'venue'

    class Seat( mongo_objects.MongoListProxy ):
        """a list of seats within the venue subdocument"""
        container_name = 'seats'


    # The parent document class
    class Events( mongo_objects.MongoUserDict ):
        collection_name = 'events'
        database = ... pymongo database connection object ...

Since the subdocument data is proxied from the parent document,
the parent document object must exist first before any proxies can be
used. ::

    # Create a new event
    event = Event()


Create
~~~~~~

Now we can create new subdocuments within the parent document.
Unique keys will be auto-assigned to distinguish each
:class:`MongoDictProxy` and :class:`MongoListProxy`
subdocument. :class:`MongoSingleProxy` doesn't need unique keys. ::

    tt = TicketTypes.create( event, { 'name' : 'VIP Ticket', ... } )
    ticket = Ticket.create( event, { 'name' : 'Fred', ... } )
    venue = Venue.create( event, { 'name' : 'Grand Auditorium', ... } )

    # as a second-level proxy, seats are created
    # using the venue object as the parent
    seat = Seat.create( venue, { 'position' : 'A1', ... } )

Since the proxied subdocument data only exists within the parent, saving
a subdocument actually saves the entire parent document. These four
method calls are identical and save the *event* object created above. ::

    tt.save()
    ticket.save()
    venue.save()
    seat.save()

Read
~~~~

If we know the proxy key, we can initialize an instance directly from the parent. ::

    freds_ticket = Ticket( event, '1' )

:meth:`get_proxy` accomplishes the same thing. For polymorphic subdocument classes
you must use :meth:`get_proxy` to create the correct subclass type. ::

    sallys_ticket = Ticket.get_proxy( event, '2' )

:meth:`get_proxies` allows us to loop through all the proxies in a container::

    for tickets in Ticket.get_proxies( event ):
        ...


Update
~~~~~~

Use any standard method of modifying a dictionary to update the data in a proxy
object. Call the :meth:`save` method to save the subdocument. This in turn
calls :meth:`MongoUserDict.save` to save the parent document to the database. ::

    # updating the VIP Ticket subdocument created above
    tt['desc'] = "Includes wider seats and a free plushie"
    tt.update( { 'cost' : 200 } )
    tt.setdefault( 'currency', 'eur' )

    tt.save()


Delete
~~~~~~

Use :meth:`delete` to delete a subdocument. By default the parent document
is saved so the database is updated immediately. ::

    freds_ticket.delete()



Best Practices
--------------

Passing Objects
~~~~~~~~~~~~~~~

Each proxy object contains a reference to its immediate parent in the :attr:`parent`
attribute. The top-level MongoDB document is referenced in the :attr:`ultimate_parent`
attribute.

Instead of passing multiple objects between functions, pass the lowest level proxy object
and determine the others based on that. In the example classes above, iterate the
ticket types for the event from a seat object with the following code. ::

    # seat.ultimate_parent is an Event object
    TicketTypes.get_proxies( seat.ultimate_parent )

Subdocument IDs
~~~~~~~~~~~~~~~

Each proxy object has a unique identifier generated by :meth:`id`. This ID is simply
the parent document ObjectId and the proxy key joined with ``g``. For multi-level
proxies, the ID for each proxy is appended in order from top-level proxy on down.

This ID can be passed to the class method :meth:`load_proxy_by_id` to load the
parent document and return the proxy object. ::

    ticket_type_id = tt.id()

    vip_tickets = Event.load_proxy_by_id( ticket_type_id, TicketType )

It is common to add convenience classmethods to the parent
document :class:`MongoUserDict` class that wrap
:meth:`load_proxy_by_id` for specific subdocuments. For example::

    class Event( mongo_objects.MongoUserDict ):

        ... other configuration and code ...

        @classmethod
        def load_ticket_type_by_id( cls, ticket_type_id ):
            """Conveniently load ticket types from an ID"""
            return cls.load_proxy_by_id( ticket_type_id, TicketType )

It is safe to nest multiple levels of proxies. Provide the full set of subdocument
classes to :meth:`.load_proxy_by_id` starting with the topmost proxy. We can
load a seat proxy with::

    # this will return an instance of "Seat"
    seat = Event.load_proxy_by_id(
        seatId,
        Venue,   # start with the top-level proxy class
        Seat     # end with the lowest-level proxy class
        )

There is also a parallel set of methods :meth:`proxy_id` and :meth:`load_proxy_by_local_id`
that omit the parent document ObjectId. These "local IDs" server as convenient
subdocument foreign keys within the same document.

Note that for a top-level proxy, the result of :meth:`proxy_id` is the proxy key.
:meth:`get_proxy` and :meth:`load_proxy_by_local_id` then perform the same function.
Assuming *ticketId* is the ticket proxy key, the following two lines of code are identical::

    ticket = Ticket.get_proxy( event, ticketId )
    ticket = Event.load_proxy_by_local_id( ticketId, Ticket )


Polymorphism
------------

Each proxy class has a polymorphic variant that supports returning separate
subdocument classes from the same container.

Polymorphism is entirely mix-and-match. A polymorphic parent document may have
non-polymorphic proxies and a non-polymorphic parent document may include
polymorphic proxies.

Subclass Keys
~~~~~~~~~~~~~

Each polymorphic subdocument subclass must define a unique proxy subclass key
which :meth:`create` adds to the subdocument. :meth:`get_proxy` inspects
the subclass key and instantiates the correct subclass type.

As a special case, one subclass may define a ``None`` key. Usually this is the
base class for the rest of the subclass tree. Any subdocuments with a missing
or invalid proxy subclass key will be instantiated as this default class.

Note the strong recommendation to define an empty *proxy_subclass_map* so each set of
polymorphic classes use their own namespace for proxy subclass keys. ::

    # create a base proxy class for the container
    class Ticket( mongo_objects.PolymorphicMongoListProxy ):
        container_name = 'tickets'

        # Recommended: define an empty proxy_subclass_map in the base class
        # This creates a separate namespace for the polymorphic
        # proxy subclass keys.
        # Otherwise, subclasses will share the base proxy subclass namespace
        # from PolymorphicMongoBaseProxy and risk name collisions with other proxies.
        proxy_subclass_map = {}

        .. your generally useful ticket methods ...

    # now create subclasses for each object variation
    # each subclass requires a unique key
    class OneWayTicket( Ticket ):
        proxy_subclass_key = 'single'

        .. your one-way specific ticket methods ...

    class RoundTripTicket( Ticket ):
        proxy_subclass_key = 'return'

        .. your round-trip specific ticket methods ...

    class MultiCityTicket( Ticket ):
        proxy_class_key = 'multi'

        .. your multi-city specific ticket methods ...


Creating Subdocuments
~~~~~~~~~~~~~~~~~~~~~

Create and save the objects using a subclass. ::

    multi = MultiCityTicket( event )
    multi.save()

    # save the subdocument ID for later
    ticketId = multi.id()

Loading Subdocuments
~~~~~~~~~~~~~~~~~~~~

If you load subdocuments using the base class, all available documents
will be returned. The resulting objects will each be an instance
of the correct subclass based on the proxy subclass key. ::

    # multi_again is an instance of MultiCityTicket
    multi_again = Event.load_proxy_by_id( ticketId, Ticket )

    # retrieve all proxies as the correct type
    Ticket.get_proxies( event )

If you load subdocuments using a subclass, only those documents
of that subclass type will be returned. ::

    # Only retrieve multi-city ticket subdocuments
    MultiCityTicket.get_proxies( event )

If a subdocument has a missing or invalid proxy subclass key, an instance of
the subclass with a ``None`` proxy subclass key is returned.
If no such subclass is defined, :exc:`MongoObjectsPolymorphicMismatch` is raised.
