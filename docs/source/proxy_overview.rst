Proxy Overview
==============

:mod:`mongo_objects` provides proxy classes to manage MongoDB subdocuments
(sub-dictionaries) as their own custom classes.
Proxying offers several advantages:

* Once the parent document is loaded, no additional database access is required
  to access the subdocuments
* No data is copied from parent to proxy, so the parent document remains
  the single source of truth
* Proxy subdocument classes organize the functions required for the subdocument
  separate from functions for the parent document itself

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
                          # no container
        { ... },          # proxy points to a single subdocument
    }

You can create as many proxies as needed to describe the data structure of
your document. Proxies can also be nested to access subdocuments within
subdocuments.

The same proxy may be used as a subdocument in multiple document collections,
for example, a :class:`MongoSingleProxy` *Address* subdocument used in the
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

Since the proxied subdocument data only exists within the parent, saving
a subdocument actually saves the entire parent document. These three
function calls are identical and save the *event* object created above. ::

    tt.save()
    ticket.save()
    venue.save()

Read
~~~~

If we know the proxy key, we can create an instance directly from the parent. ::

    freds_ticket = Ticket( event, '1' )

:func:`get_proxy` accomplishes the same thing but is required
for polymorphic subdocument classes in order to create the correct subclass type. ::

    sallys_ticket = Ticket.get_proxy( event, '2' )

:func:`get_proxies` allows us to loop through all the proxies in a container::

    for tickets in Ticket.get_proxies( event ):
        ...

Subdocuments have their own unique, URL-safe IDs. By default, the proxy subdocument
key is appended to the parent document ObjectId. This ID can be used to recreate
the proxy from the parent object.

Since the data for a proxy only exists in the parent document, :func:`load_proxy_by_id`
first loads the parent document and then uses the given class to instantiate
the subdocument proxy::

    ticket_type_id = tt.id()

    vip_tickets = Event.load_proxy_by_id( ticket_type_id, TicketType )

It is safe to nest multiple levels of proxies. Provide the full set of subdocument
classes to :func:`load_proxy_by_id` starting with the topmost proxy. If we have
a Seat proxy within the Venue proxy, we could load it by ID with::

    # this will return an instance of "Seat"
    seat = Event.load_proxy_by_id(
        seatId,
        Venue,   # start with the top-level proxy class
        Seat     # end with the lowest-level proxy class
        )

It is common practice to add convenience classmethods to the parent
document :class:`MongoUserDict` class to load proxy objects. For example::

    class Event( mongo_objects.MongoUserDict ):

        ... other configuration and code ...

        @classmethod
        def load_ticket_type_by_id( cls, ticket_type_id ):
            return cls.load_proxy_by_id( ticket_type_id, TicketType )


Update
~~~~~~

Use any standard method of modifying a dictionary to update the data in a proxy
object. Call the :func:`save` function to save the subdocument. This in turn
calls :func:`MongoUserDict.save` to save the parent document to the database. ::

    # updating the VIP Ticket subdocument created above
    tt['desc'] = "Includes wider seats and a free plushie"
    tt.update( { 'cost' : 200 } )
    tt.setdefault( 'currency', 'eur' )

    tt.save()


Delete
~~~~~~

Use :func:`delete` to delete a subdocument. By default the parent document
is saved so the database is updated immediately. ::

    freds_ticket.delete()



Polymorphism
------------

Each proxy class has a polymorphic variant that supports returning separate
subdocument classes from the same container.

Each polymorphic subdocument subclass must define a unique proxy subclass key
which :func:`.create` adds to the subdocument. :func:`.get_proxy` inspects
the subclass key and instantiates the correct subclass type.

Polymorphism is entirely mix-and-match. A polymorphic parent document may have
non-polymorphic proxies and a non-polymorphic parent document may include
polymorphic proxies.

Note the recommendation to define an empty *proxy_subclass_map* so each set of
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

        .. your generally useful ticket functions ...

    # now create subclasses for each object variation
    # each subclass requires a unique key
    class OneWayTicket( Ticket ):
        proxy_subclass_key = 'single'

        .. your one-way specific ticket functions ...

    class RoundTripTicket( Ticket ):
        proxy_subclass_key = 'return'

        .. your round-trip specific ticket functions ...

    class MultiCityTicket( Ticket ):
        proxy_class_key = 'multi'

        .. your multi-city specific ticket functions ...


Create and save the objects using a subclass. ::

    multi = MultiCityTicket( event )
    multi.save()

    # save the subdocument ID for later
    ticketId = multi.id()

Load subdocuments using the base class. The resulting object will be an instance
of the correct subclass based on the proxy subclass key. ::

    # multi_again is an instance of MultiCityTicket
    multi_again = Event.load_proxy_by_id( ticketId, Ticket )

If the subdocument has a missing or invalid proxy subclass key, an instance of your
proxy base class is returned.
