# mongo_objects Sample App
#
# https://mongo-objects.headwaters.com.sg
# https://pypi.org/project/mongo-objects/
#
# Copyright 2024 Jonathan Lindstrom
# Headwaters Entrepreneurs Pte Ltd
#
# Released under the MIT License


from bson import ObjectId
from collections import UserDict
from datetime import datetime
from flask import flash, Flask, redirect, render_template, request, url_for
from flask_pymongo import PyMongo
from flask_wtf import FlaskForm
import mongo_objects
import os
import secrets
from wtforms import DateField, HiddenField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


# create and configure the app
app = Flask(__name__)

# Save a MongoDB client connection on the app
# Use a URI in the MONGO_CONNECT_URI environment variable, if provided
# Otherwise, just connect locally to a "mongo_objects_sample" database
app.mongo = PyMongo(app, os.environ.get('MONGO_CONNECT_URI', 'mongodb://127.0.0.1:27017/mongo_objects_sample' ) )

# Create a random secret key
app.config['SECRET_KEY'] = secrets.token_urlsafe(32)


################################################################################
# mongo_objects Classes
################################################################################

# Use a polymorphic list proxy to track features and gift
# benefits for the same ticket type.
#
# A feature is an intangible benefit included with the ticket,
# like a front-row seat.
#
# A gift is a tangible benefit like a gift bag or free
# bucket of popcorn.

class Benefit( mongo_objects.PolymorphicMongoListProxy ):
    container_name = 'benefits'
    proxy_subclass_map = {}

class Feature( Benefit ):
    proxy_subclass_key = 'ft'

class Gift( Benefit ):
    proxy_subclass_key = 'gt'



class TicketType( mongo_objects.MongoDictProxy ):
    '''Use a MongoDictProxy to record all the available ticket
    types for this event as subdocuments.'''

    container_name = 'ticketTypes'

    def isSoldOut( self ):
        '''Return True if tickets of this type are not available for this event'''
        return (self.ticketsAvailable() == 0)


    def countGifts( self ):
        return len( Gift.get_proxies( self ) )


    def getBenefits( self ):
        return Benefit.get_proxies( self )


    def getFeatures( self ):
        return Feature.get_proxies( self )


    def getGifts( self ):
        return Gift.get_proxies( self )


    def getTickets( self ):
        return self.parent.getTicketsByType( self.key )


    def giftNames( self ):
        names = [ x['name'] for x in Gift.get_proxies( self ) ]
        if len( names ) == 0:
            return ''
        elif len( names ) == 1:
            return names[0]
        else:
            return ' and '.join( [ ', '.join( names[:-1] ), names[-1] ] )


    def sell( self, name ):
        return self.parent.createTicket( self.key, name )


    def ticketsAvailable( self ):
        '''Return the number of tickets of this type available for this event but never less than 0'''
        return max( 0, self.get('ticketsTotal', 0) - self.ticketsSold() )


    def ticketsSold( self ):
        return self.parent.countTicketsByType( self.key )



class Ticket( mongo_objects.MongoListProxy ):
    '''Use a MongoListProxy to track each ticket sold as a subdocument'''
    container_name = 'tickets'

    def displayIssuedTime( self ):
        return self['issued'].strftime('%Y-%m-%d %H:%M')



class Venue( mongo_objects.MongoSingleProxy ):
    container_name = 'venue'



class Event( mongo_objects.MongoUserDict ):
    '''Record information about an upcoming event or presentation'''

    database = app.mongo.db
    collection_name = 'events'


    def countTicketsByType( self, ticketTypeKey ):
        return len( self.getTicketsByType( ticketTypeKey ) )


    def createTicket( self, ticketTypeKey, name, autosave=True ):
        '''Issue a ticket for the customer.
        Here we control whether `create()` saves the parent document or not.'''
        return Ticket.create(
            self,
            {
                'name' : name,
                'ticketTypeKey' : ticketTypeKey,
                'issued' : self.utcnow(),
            },
            autosave=autosave )


    def createTicketType( self, subdoc ):
        '''Save a new ticket type subdocument.
        `create()` will automatically save the parent document by default.'''
        return TicketType.create( self, subdoc )


    def displayDate( self ):
        return self['eventDate'].strftime('%Y-%m-%d')


    def getTicket( self, key ):
        return Ticket.get_proxy( self, key )


    def getTickets( self ):
        return Ticket.get_proxies( self )


    def getTicketsByType( self, ticketTypeKey ):
        return [ t for t in self.getTickets() if t['ticketTypeKey'] == ticketTypeKey ]


    def getTicketType( self, key ):
        return TicketType( self, key )


    def getTicketTypes( self ):
        return TicketType.get_proxies( self )


    def getVenue( self ):
        return Venue( self )


    def hasTicketTypes( self ):
        return len( self.getTicketTypes() ) > 0


    def hasVenue( self ):
        return Venue.exists( self )


    def isFutureEvent( self ):
        '''Return True if this event is in the future'''
        return (self.get('eventDate') and self['eventDate'] > datetime.utcnow())


    def isSoldOut( self ):
        '''Return False if any tickets of any type are available for this event'''
        return (self.ticketsAvailable() == 0)


    @classmethod
    def loadBenefitById( cls, benefitId ):
        '''Load by generic benefitId, although the returned object
        will be either a Feature or a Gift as appropriate.'''
        return cls.load_proxy_by_id( benefitId, TicketType, Benefit )


    @classmethod
    def loadTicketTypeById( cls, ticketTypeId ):
        return cls.load_proxy_by_id( ticketTypeId, TicketType )


    @classmethod
    def loadVenueById( cls, venueId ):
        return cls.load_proxy_by_id( venueId, Venue )


    def ticketsAvailable( self ):
        '''Return the number of tickets available across all types for this event'''
        return sum( [ tt.ticketsAvailable() for tt in self.getTicketTypes() ] )


    def ticketsSold( self ):
        '''Return the number of tickets sold across all types for this event'''
        # We could also just check the length of the tickets container list
        return sum( [ tt.ticketsSold() for tt in self.getTicketTypes() ] )


    def ticketsTotal( self ):
        '''Return the total number of tickets available across all types for this event'''
        return sum( [ tt['ticketsTotal'] for tt in self.getTicketTypes() ] )



################################################################################
# Forms
################################################################################

class CreateUpdateEventForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    description = TextAreaField( 'Description', validators=[DataRequired()])
    eventDate = DateField( 'Date', validators=[DataRequired()] )
    submitButton = SubmitField( 'Create Event' )


class CreateUpdateFeatureForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    description = TextAreaField( 'Description', validators=[DataRequired()])
    submitButton = SubmitField( 'Add Gift' )


class CreateUpdateGiftForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    description = TextAreaField( 'Description', validators=[DataRequired()])
    value = IntegerField( 'Value', validators=[DataRequired()] )
    submitButton = SubmitField( 'Add Gift' )


class CreateUpdateTicketTypeForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    description = TextAreaField( 'Description', validators=[DataRequired()])
    ticketsTotal = IntegerField( 'Total Tickets Available', validators=[DataRequired(), NumberRange(min=0)], default=0 )
    cost = IntegerField( 'Cost', validators=[DataRequired()] )
    submitButton = SubmitField( 'Create Event' )


class CreateUpdateVenueForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    address = TextAreaField( 'Address', validators=[DataRequired()])
    phone = StringField( 'Phone', validators=[DataRequired(), Length(max=20)] )
    submitButton = SubmitField( 'Create Venue' )


class ConfirmForm( FlaskForm ):
    updated = HiddenField( 'Updated' )
    submitButton = SubmitField( 'Confirm' )


class CustomerPurchaseForm( FlaskForm ):
    ticketTypeId = HiddenField( 'Ticket Type ID' )
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    submitButton = SubmitField( 'Confirm' )



################################################################################
# Routes / Implementation
################################################################################

@app.route('/admin-create-event', methods=['GET', 'POST'])
def adminCreateEvent():
    '''Create a new event'''

    form = CreateUpdateEventForm()
    if request.method == 'POST':
        if form.validate():
            ed = form.eventDate.data
            event = Event( {
                'name' : form.name.data,
                'description' : form.description.data,
                'eventDate' : datetime( ed.year, ed.month, ed.day ),
            } )
            event.save()
            flash( f'Created new event "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )

    return render_template( 'create-update-event.jinja', form=form )



@app.route('/admin-create-feature/<ticketTypeId>', methods=['GET', 'POST'])
def adminCreateFeature( ticketTypeId ):
    '''Add a feature to a ticket type.'''

    # Try to locate the existing ticket type
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
        assert ticketType is not None
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateFeatureForm()
    if request.method == 'POST':
        if form.validate():
            feature = Feature.create( ticketType, {
                'name' : form.name.data,
                'description' : form.description.data,
            } )
            flash( f'Added feature "{feature['name']}"' )
            return redirect( url_for( 'adminTicketDetail', ticketTypeId=ticketType.id() ) )

    return render_template( 'create-update-feature.jinja', form=form, ticketType=ticketType )



@app.route('/admin-create-gift/<ticketTypeId>', methods=['GET', 'POST'])
def adminCreateGift( ticketTypeId ):
    '''Add a gift to a ticket type.'''

    # Try to locate the existing ticket type
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
        assert ticketType is not None
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateGiftForm()
    if request.method == 'POST':
        if form.validate():
            gift = Gift.create( ticketType, {
                'name' : form.name.data,
                'description' : form.description.data,
                'value' : form.value.data,
            } )
            flash( f'Added gift "{gift['name']}"' )
            return redirect( url_for( 'adminTicketDetail', ticketTypeId=ticketType.id() ) )

    return render_template( 'create-update-gift.jinja', form=form, ticketType=ticketType )



@app.route('/admin-create-ticket-type/<eventId>', methods=['GET', 'POST'])
def adminCreateTicketType( eventId ):
    '''Create a new ticket type for an existing event'''

    # Try to locate the existing event
    try:
        event = Event.load_by_id( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateTicketTypeForm()
    if request.method == 'POST':
        if form.validate():
            event.createTicketType( {
                'name' : form.name.data,
                'description' : form.description.data,
                'cost' : form.cost.data,
                'ticketsTotal' : form.ticketsTotal.data,
            } )
            flash( f'Created new ticket type "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=eventId ) )

    return render_template( 'create-update-ticket-type.jinja', form=form, event=event )



@app.route('/admin-create-venue/<eventId>', methods=['GET', 'POST'])
def adminCreateVenue( eventId ):
    '''Add venue information to an event.'''

    # Try to locate the existing event
    try:
        event = Event.load_by_id( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateVenueForm()
    if request.method == 'POST':
        if form.validate():
            venue = Venue.create( event, {
                'name' : form.name.data,
                'address' : form.address.data,
                'phone' : form.phone.data,
            } )
            venue.save()
            flash( f'Added venue information' )
            return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )

    return render_template( 'create-update-venue.jinja', form=form, event=event )



@app.route('/admin-delete-benefit/<benefitId>', methods=['POST'])
def adminDeleteBenefit( benefitId ):
    '''Delete a Benefit subclass, either a Feature or a Gift.
    This is a post-only page from the adminUpdateFeature and
    adminUpdateGift pages'''
    # Try to locate the benefit
    try:
        benefit = Event.loadBenefitById( benefitId )
        ticketType = benefit.parent
    except:
        flash( 'Unable to locate the requested benefit information. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = ConfirmForm()
    if form.validate():
        # Preserve the name as the proxy data won't be
        # available once it is deleted
        name = benefit['name']
        benefit.delete()
        flash( f"Deleted {name} information" )
    else:
        flash( f"Unable to delete {name} information" )

    return redirect( url_for( 'adminTicketDetail', ticketTypeId=ticketType.id() ) )



@app.route('/admin-delete-event/<eventId>', methods=['POST'])
def adminDeleteEvent( eventId ):
    '''Delete an event. This is a post-only page from the
    adminUpdateEvent page'''
    # Try to locate the existing event
    try:
        event = Event.load_by_id( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = ConfirmForm()
    if form.validate():
        # MongoUserDict objects retain all values (except _id)
        # after deletion
        event.delete()
        flash( f"Deleted event \"{event['name']}\"" )
        return redirect( url_for( 'adminEventList' ) )

    else:
        flash( f"Unable to delete event \"{event['name']}\"" )
        return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )



@app.route('/admin-delete-ticket-type/<ticketTypeId>', methods=['POST'])
def adminDeleteTicketType( ticketTypeId ):
    '''Delete a ticket type from an event. This is a post-only
    page from the adminUpdateTicketType page'''
    # Try to locate the existing ticket type
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
        event = ticketType.parent
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    # Make sure no tickets of this type have been sold
    if ticketType.ticketsSold() > 0:
        flash( f"{ticketType['name']} have already been sold. The ticket type can't be deleted." )
        return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )

    form = ConfirmForm()
    if form.validate():
        # Preserve the name as the data in the proxy
        # won't exist once it is deleted
        name = ticketType['name']
        ticketType.delete()
        flash( f'Deleted ticket type "{name}"' )
    else:
        flash( f'Unable to delete ticket type "{name}"' )

    return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )



@app.route('/admin-delete-venue/<venueId>', methods=['POST'])
def adminDeleteVenue( venueId ):
    '''Delete venue information for an event. This is a post-only
    page from the adminUpdateVenue page'''
    # Try to locate the existing venue
    try:
        venue = Event.loadVenueById( venueId )
        event = venue.parent
    except:
        flash( 'Unable to locate the requested venue information. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = ConfirmForm()
    if form.validate():
        venue.delete()
        flash( f"Deleted venue information" )
    else:
        flash( f"Unable to delete venue information" )

    return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )



@app.route('/admin-event-detail/<eventId>')
def adminEventDetail( eventId ):
    '''Display event information as an administrator'''
    # Try to locate the existing event
    try:
        event = Event.load_by_id( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    return render_template( 'admin-event-detail.jinja', event=event )



@app.route('/admin-event-list')
def adminEventList():
    '''Loop through the events in the database as an administrator'''
    return render_template( 'admin-event-list.jinja', events=Event.find() )



@app.route('/admin-ticket-detail/<ticketTypeId>')
def adminTicketDetail( ticketTypeId ):
    '''List all tickets of a specific type'''
    # Locate the existing ticket type within its event
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
        assert ticketType is not None
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    return render_template( 'admin-ticket-detail.jinja', ticketType=ticketType )



@app.route('/admin-update-event/<eventId>', methods=['GET', 'POST'])
def adminUpdateEvent( eventId ):
    '''Update an existing event'''
    # Try to locate the existing event
    try:
        event = Event.load_by_id( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateEventForm( data=event )
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if event['_updated'].isoformat() != form.updated.data:
                flash( 'The event has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateEvent', eventId=eventId ) )

            # Update event document with new data
            ed = form.eventDate.data
            # update() is just the plain vanilla dictionary method
            event.update( {
                'name' : form.name.data,
                'description' : form.description.data,
                'eventDate' : datetime( ed.year, ed.month, ed.day ),
            } )
            # We need to save the updated event ourselves
            event.save()
            flash( f'Updated event "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( event['_updated'].isoformat() )
    return render_template(
        'create-update-event.jinja',
        delform=ConfirmForm(),
        event=event,
        form=form,
    )



@app.route('/admin-update-feature/<featureId>', methods=['GET', 'POST'])
def adminUpdateFeature( featureId ):
    '''Update an existing feature'''
    # Locate the existing feature within its ticket type and event
    try:
        feature = Event.loadBenefitById( featureId )
        ticketType = feature.parent
        event = ticketType.parent
    except:
        flash( 'Unable to locate the requested feature. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateFeatureForm( data=feature.data() )
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if event['_updated'].isoformat() != form.updated.data:
                flash( 'The event has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateTicketType', ticketTypeId=ticketType.id() ) )

            # Update ticket type proxy document with new data
            feature.update( {
                'name' : form.name.data,
                'description' : form.description.data,
            } )
            # Saving the proxy saves the entire parent document
            feature.save()
            flash( f'Updated feature "{form.name.data}"' )
            return redirect( url_for( 'adminTicketDetail', ticketTypeId=ticketType.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( event['_updated'].isoformat() )
    return render_template(
        'create-update-feature.jinja',
        delform=ConfirmForm(),
        feature=feature,
        form=form,
    )



@app.route('/admin-update-gift/<giftId>', methods=['GET', 'POST'])
def adminUpdateGift( giftId ):
    '''Update an existing gift'''
    # Locate the existing gift within its ticket type and event
    try:
        gift = Event.loadBenefitById( giftId )
        ticketType = gift.parent
        event = ticketType.parent
    except:
        flash( 'Unable to locate the requested gift. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateGiftForm( data=gift.data() )
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if event['_updated'].isoformat() != form.updated.data:
                flash( 'The event has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateTicketType', ticketTypeId=ticketType.id() ) )

            # Update ticket type proxy document with new data
            gift.update( {
                'name' : form.name.data,
                'description' : form.description.data,
                'value' : form.value.data,
            } )
            # Saving the proxy saves the entire parent document
            gift.save()
            flash( f'Updated gift "{form.name.data}"' )
            return redirect( url_for( 'adminTicketDetail', ticketTypeId=ticketType.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( event['_updated'].isoformat() )
    return render_template(
        'create-update-gift.jinja',
        delform=ConfirmForm(),
        gift=gift,
        form=form,
    )



@app.route('/admin-update-ticket-type/<ticketTypeId>', methods=['GET', 'POST'])
def adminUpdateTicketType( ticketTypeId ):
    '''Update an existing ticket type'''
    # Locate the existing ticket type within its event
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
        event = ticketType.parent
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateTicketTypeForm( data=ticketType.data() )
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if event['_updated'].isoformat() != form.updated.data:
                flash( 'The event has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateEvent', eventId=event.id() ) )

            # Update ticket type proxy document with new data
            ticketType.update( {
                'name' : form.name.data,
                'description' : form.description.data,
                'cost' : form.cost.data,
                'ticketsTotal' : form.ticketsTotal.data,
            } )
            # Saving the proxy saves the entire parent document
            ticketType.save()
            flash( f'Updated ticket type "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=event.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( event['_updated'].isoformat() )
    return render_template(
        'create-update-ticket-type.jinja',
        delform=ConfirmForm(),
        form=form,
        ticketType=ticketType,
    )



@app.route('/admin-update-venue/<venueId>', methods=['GET', 'POST'])
def adminUpdateVenue( venueId ):
    '''Add venue information to an event.'''
    # Try to locate the existing event
    try:
        venue = Event.loadVenueById( venueId )
        assert venue is not None
    except Exception as e:
        flash( 'Unable to locate the requested venue. Please try again' )
        print( f"Exception {e}" )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateVenueForm( data=venue )
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if venue.parent['_updated'].isoformat() != form.updated.data:
                flash( 'The event has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateEvent', eventId=venue.parent.id() ) )

            venue.update( {
                'name' : form.name.data,
                'address' : form.address.data,
                'phone' : form.phone.data,
            } )
            # We need to save the updated data ourselves
            venue.save()
            flash( f'Updated venue information for event "{venue.parent['name']}"' )
            return redirect( url_for( 'adminEventDetail', eventId=venue.parent.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( venue.parent['_updated'].isoformat() )
    return render_template(
        'create-update-venue.jinja',
        delform=ConfirmForm(),
        form=form,
        venue=venue,
    )



@app.route('/customer-event-detail/<eventId>')
def customerEventDetail( eventId ):
    '''Display event information as a customer'''
    # Try to locate the existing event
    try:
        event = Event.load_by_id( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'customerEventList') )

    return render_template( 'customer-event-detail.jinja', event=event )



@app.route('/customer-event-list')
def customerEventList():
    '''Loop through the events in the database as a customer'''
    return render_template( 'customer-event-list.jinja', events=Event.find() )



@app.route('/customer-purchase-ticket/<ticketTypeId>', methods=['GET', 'POST'])
def customerPurchaseTicket( ticketTypeId ):
    '''Purchase a ticket'''
    # Locate the ticket type within its event
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
        event = ticketType.parent
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'customerEventList') )

    # Make sure this type of ticket isn't already sold out
    if ticketType.isSoldOut():
        flash( f"Sorry! {ticketType['name']} are already sold out." )
        return redirect( url_for( 'customerEventDetail', eventId=event.id() ) )

    form = CustomerPurchaseForm()
    if request.method == 'POST':
        if form.validate():
            ticket = ticketType.sell( form.name.data )
            flash( f"""{ticketType['name']} {ticket.id()} ticket to {event['name']} has been issued for {form.name.data}""" )
            giftNames = ticketType.giftNames()
            if len( giftNames ) > 0:
                flash( f"Don't forget to get your {giftNames}" )
            return redirect( url_for( 'customerEventList' ) )

    return render_template( 'customer-purchase-ticket.jinja', ticketType=ticketType, form=form )


@app.route('/')
def indexPage():
    return render_template( 'index.jinja' )
