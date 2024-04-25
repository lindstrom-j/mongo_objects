Quickstart
========================

MongoDB Documents
-----------------

Subclass :doc:`MongoUserDict` and provide the class with two pieces of information,
the pymongo object for your MongoDB database and the name of the collection.

To illustrate we'll use snippets of the event management application
from the sample code.::

    import mongo_objects

    class Event( mongo_objects.MongoUserDict ):
        db = ...          # provide your MongoDB database object here
        collection_name = 'events'


You can now manage your data as follows::

    # Initialize a new, empty MongoDB document as an Event object,
    # a subclass of UserDict with full dictionary features.
    new_event = Event()

    # Query MongoDB for all events. Each document is returned
    # as an Event object
    events = Event.find()

    # Query a single MongoDB document. The result is returned as,
    # you guessed it, an Event object.
    an_event = Event.find_one()

    # Obtain the BSON ObjectId for a document object as a string.
    # IDs contain only hex digits and are therefore URL safe.
    eventId = an_event.id()

    # Load a MongoDB document by its ID
    another_event = Event.load_by_id( '66276931d1bbccd13fb20cad' )

    # Delete an object from the database
    another_event.delete()

    # Intelligently save the document object. New documents use
    # insert_one() while existing documents use replace_one() or
    # find_one_and_replace() as appropriate.
    new_event.save()
    an_event.save()

You can read more in the :doc:`MongoUserDict` documentation or see a working
example in the :doc:`sample` code.



Sub-Document Proxies
--------------------

To manage a dictionary of subdocuments, subclass :doc:`MongoDictProxy` and provide
the class with the name of the containing dictionary::

    import mongo_objects

    class Ticket( mongo_objects.MongoDictProxy ):
        container_name = 'tickets'


This configures a proxy for subdocuments in the following layout::

    document = {
        ... other top-level content ...
        tickets : {
            key1 : { ... content for first ticket ... },
            key2 : { ... content for second ticket ... },
            key3 : { ... content for third ticket ... },
        }

Subdocument proxy objects don't contain any data themselves. Instead, they act as
dictionary-like objects that redirect all data access back to the parent document.

In this context *parent* is used to describe the outer MongoDB document that contains
the subdocument. This is unrelated to any object-oriented inheritance.

Common use patterns::

    # Create a parent object
    event = Event()

    # Create a new subdocument with event as the parent
    # a unique key is automatically assigned
    new_ticket = Ticket.create( event, { ... my subdocument data ... } )

    # List all the subdocuments in a parent document
    # Results are returned as Ticket objects
    tickets = Ticket.get_proxies( event )

    # Look up an existing subdocument by key
    ticket = Ticket.get_proxy( event, "1" )

    # Perform all the usual dictionary operations
    if 'paid' in ticket:
        ... your code ...
    for key in ticket.keys():
        ... your code ...
    ticket['isUsed'] = True
    ticket.get( 'dateSold' )
    ticket.setdefault( 'name', 'Oscar' )
    del ticket['seatNumber']

    # Look up and remove an existing subdocument by key
    another_ticket = Ticket.get_proxy( event, "2" )
    another_ticket.delete()

    # Save the parent document through the proxy subdocument
    ticket.save()

    # Get the unique, URL-safe ID of the proxy object
    ticketId = ticket.id()

    # Load a subdocument from its ID
    # Since the parent must be loaded first, this is actually
    # a classmethod on the parent document
    ticket = Event.load_proxy_by_id(
        '66277dcce66752e012bf62e6g73',
        Ticket
        )


You can read more in the :doc:`MongoDictProxy` documentation. Lists
can also be used as subdocument containers with :doc:`MongoListProxy`.
Single dictionary proxies are managed with :doc:`MongoSingleProxy`.
