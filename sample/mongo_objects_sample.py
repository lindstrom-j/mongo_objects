# mongo_objects Sample App
# Copyright 2024 Headwaters Entrepreneurs Pte Ltd
# https://headwaters.com.sg
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
# Use a URI if provided as the MONGO_CONNECT_URI environment variable
# Otherwise, just connect locally to a "mongo_objects_sample" database
app.mongo = PyMongo(app, os.environ.get('MONGO_CONNECT_URI', 'mongodb://127.0.0.1:27017/mongo_objects_sample' ) )

# Create a random secret key
app.config['SECRET_KEY'] = secrets.token_urlsafe(32)



# Form classes
class CreateUpdateEventForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    description = TextAreaField( 'Description', validators=[DataRequired()])
    eventDate = DateField( 'Date', validators=[DataRequired()] )
    submitButton = SubmitField( 'Create Event' )


class CreateUpdateTicketTypeForm( FlaskForm ):
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    updated = HiddenField( 'Updated' )
    description = TextAreaField( 'Description', validators=[DataRequired()])
    ticketsTotal = IntegerField( 'Total Tickets Available', validators=[DataRequired(), NumberRange(min=0)], default=0 )
    cost = IntegerField( 'Cost', validators=[DataRequired()] )
    submitButton = SubmitField( 'Create Event' )


class ConfirmForm( FlaskForm ):
    updated = HiddenField( 'Updated' )
    submitButton = SubmitField( 'Confirm' )


class CustomerPurchaseForm( FlaskForm ):
    ticketTypeId = HiddenField( 'Ticket Type ID' )
    name = StringField( 'Name', validators=[DataRequired(), Length(max=50)] )
    submitButton = SubmitField( 'Confirm' )


# Classes
class TicketType( mongo_objects.MongoDictProxy ):
    containerName = 'ticketTypes'

    def isSoldOut( self ):
        '''Return True if tickets of this type are not available for this event'''
        return (self.ticketsAvailable() == 0)


    def getTickets( self ):
        return self.parent.getTicketsByType( self.key )


    def sell( self, name ):
        return self.parent.createTicket( self.key, name )


    def ticketsAvailable( self ):
        '''Return the number of tickets of this type available for this event but never less than 0'''
        return max( 0, self.get('ticketsTotal', 0) - self.ticketsSold() )


    def ticketsSold( self ):
        return self.parent.countTicketsByType( self.key )



class Ticket( mongo_objects.MongoListProxy ):
    containerName = 'tickets'

    def displayIssuedTime( self ):
        return self['issued'].strftime('%Y-%m-%d %H:%M')



class Event( mongo_objects.MongoUserDict ):
    database = app.mongo.db
    collection_name = 'events'


    def countTicketsByType( self, ticketTypeKey ):
        return len( self.getTicketsByType( ticketTypeKey ) )


    def createTicket( self, ticketTypeKey, name, autosave=True ):
        '''Generate a unique key and issue a ticket for the customer'''
        return Ticket.create(
            self,
            {
                'name' : name,
                'ticketTypeKey' : ticketTypeKey,
                'issued' : self.utcnow(),
            },
            autosave=autosave )


    def createTicketType( self, subdoc ):
        '''Generate a unique key and save this new ticket type subdocument'''
        return TicketType.create( self, subdoc )


    def displayDate( self ):
        return self['eventDate'].strftime('%Y-%m-%d')


    def getTicket( self, key ):
        return Ticket.getProxy( self, key )


    def getTickets( self ):
        return Ticket.getProxies( self )


    def getTicketsByType( self, ticketTypeKey ):
        return [ t for t in self.getTickets() if t['ticketTypeKey'] == ticketTypeKey ]


    def getTicketType( self, key ):
        return TicketType( self, key )


    def getTicketTypes( self ):
        return TicketType.getProxies( self )


    def hasTicketTypes( self ):
        return len( self.getTicketTypes() ) > 0


    def isFutureEvent( self ):
        '''Return True if this event is in the future'''
        return (self.get('eventDate') and self['eventDate'] > datetime.utcnow())


    def isSoldOut( self ):
        '''Return True if any tickets of any type are available for this event'''
        return (self.ticketsAvailable() == 0)


    @classmethod
    def loadTicketTypeById( cls, ticketTypeId ):
        return cls.loadProxyById( ticketTypeId, TicketType )


    def ticketsAvailable( self ):
        '''Return the number of tickets available across all types for this event'''
        return sum( [ tt.ticketsAvailable() for tt in self.getTicketTypes() ] )


    def ticketsSold( self ):
        '''Return the number of tickets sold across all types for this event'''
        # We could theoretically just check the length of the tickets container list
        # This method weeds out any bad data from invalid ticket type keys
        return sum( [ tt.ticketsSold() for tt in self.getTicketTypes() ] )


    def ticketsTotal( self ):
        '''Return the total number of tickets available across all types for this event'''
        return sum( [ tt['ticketsTotal'] for tt in self.getTicketTypes() ] )





# Implementation functions for routes

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



@app.route('/admin-create-ticket-type/<eventId>', methods=['GET', 'POST'])
def adminCreateTicketType( eventId ):
    '''Create a new ticket type for an existing event'''

    # Try to locate the existing event
    try:
        event = Event.loadById( eventId )
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
            event.save()
            flash( f'Created new ticket type "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=eventId ) )

    return render_template( 'create-update-ticket-type.jinja', form=form, event=event )



@app.route('/admin-delete-event/<eventId>', methods=['GET', 'POST'])
def adminDeleteEvent( eventId ):
    '''Delete an event'''
    # Try to locate the existing event
    try:
        event = Event.loadById( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = ConfirmForm()
    if request.method == 'POST':
        if form.validate():
            event.delete()
            flash( f"Deleted event \"{event['name']}\"" )
            return redirect( url_for( 'adminEventList' ) )

    return render_template( 'admin-delete-event.jinja', event=event, form=form )



@app.route('/admin-delete-ticket-type/<ticketTypeId>', methods=['GET', 'POST'])
def adminDeleteTicketType( ticketTypeId ):
    '''Delete a ticket type.'''
    # Locate the existing ticket type within its event
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    # Make sure no tickets of this type have been sold
    if ticketType.ticketsSold() > 0:
        flash( f"{ticketType['name']} have already been sold. The ticket type can't be deleted." )
        return redirect( url_for( 'adminEventDetail', eventId=ticketType.parent.id() ) )

    form = ConfirmForm()
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if ticketType.parent['_updated'].isoformat() != form.updated.data:
                flash( 'The ticket type has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateEvent', eventId=ticketType.parent.id() ) )

            name = ticketType['name']
            ticketType.delete()
            flash( f'Deleted ticket type "{name}"' )
            return redirect( url_for( 'adminEventDetail', eventId=ticketType.parent.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( ticketType.parent['_updated'].isoformat() )
    return render_template( 'admin-delete-ticket-type.jinja', ticketType=ticketType, form=form )



@app.route('/admin-event-detail/<eventId>')
def adminEventDetail( eventId ):
    '''Display event information as an administrator'''
    # Try to locate the existing event
    try:
        event = Event.loadById( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'adminEventList') )

    return render_template( 'admin-event-detail.jinja', event=event )



@app.route('/admin-event-list')
def adminEventList():
    '''Loop through the events in the database as an administrator'''
    return render_template( 'admin-event-list.jinja', events=Event.find() )



@app.route('/admin-ticket-list/<ticketTypeId>')
def adminTicketList( ticketTypeId ):
    '''List all tickets of a specific type'''
    # Locate the existing ticket type within its event
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    return render_template( 'admin-ticket-list.jinja', ticketType=ticketType )



@app.route('/admin-update-event/<eventId>', methods=['GET', 'POST'])
def adminUpdateEvent( eventId ):
    '''Update an existing event'''
    # Try to locate the existing event
    try:
        event = Event.loadById( eventId )
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
            event.update( {
                'name' : form.name.data,
                'description' : form.description.data,
                'eventDate' : datetime( ed.year, ed.month, ed.day ),
            } )
            event.save()
            flash( f'Updated event "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=event['_id'] ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( event['_updated'].isoformat() )
    return render_template( 'create-update-event.jinja', eventId=eventId, form=form )



@app.route('/admin-update-ticket-type/<ticketTypeId>', methods=['GET', 'POST'])
def adminUpdateTicketType( ticketTypeId ):
    '''Update an existing event'''
    # Locate the existing ticket type within its event
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'adminEventList') )

    form = CreateUpdateTicketTypeForm( data=ticketType.data() )
    if request.method == 'POST':
        if form.validate():
            # Verify the document hasn't been updated in the meantime
            # If so, redirect back to this page with a GET so we reload the data
            if ticketType.parent['_updated'].isoformat() != form.updated.data:
                flash( 'The ticket type has been updated elsewhere. Please check your changes.' )
                return redirect( url_for( 'adminUpdateEvent', eventId=ticketType.parent.id() ) )

            # Update event document with new data
            ticketType.update( {
                'name' : form.name.data,
                'description' : form.description.data,
                'cost' : form.cost.data,
                'ticketsTotal' : form.ticketsTotal.data,
            } )
            ticketType.save()
            flash( f'Updated ticket type "{form.name.data}"' )
            return redirect( url_for( 'adminEventDetail', eventId=ticketType.parent.id() ) )

    # Save the timestamp of current document for later reference
    form.updated.process_data( ticketType.parent['_updated'].isoformat() )
    return render_template( 'create-update-ticket-type.jinja', ticketType=ticketType, form=form )



@app.route('/customer-event-detail/<eventId>')
def customerEventDetail( eventId ):
    '''Display event information as a customer'''
    # Try to locate the existing event
    try:
        event = Event.loadById( eventId )
        assert event is not None
    except:
        flash( 'Unable to locate the requested event. Please try again' )
        return redirect( url_for( 'customerEventList') )

    return render_template( 'customer-event-detail.jinja', event=event )



@app.route('/customer-event-list')
@app.route('/')
def customerEventList():
    '''Loop through the events in the database as a customer'''
    return render_template( 'customer-event-list.jinja', events=Event.find() )



@app.route('/customer-purchase-ticket/<ticketTypeId>', methods=['GET', 'POST'])
def customerPurchaseTicket( ticketTypeId ):
    '''Purchase a ticket'''
    # Locate the ticket type within its event
    # Try a simple assert to make sure the data is valid
    try:
        ticketType = Event.loadTicketTypeById( ticketTypeId )
    except:
        flash( 'Unable to locate the requested ticket type. Please try again' )
        return redirect( url_for( 'customerEventList') )

    # Make sure no tickets of this type have been sold
    if ticketType.ticketsSold() > ticketType['ticketsTotal']:
        flash( f"Sorry! {ticketType['name']} are already sold out." )
        return redirect( url_for( 'customerEventDetail', eventId=ticketType.parent.id() ) )

    form = CustomerPurchaseForm()
    if request.method == 'POST':
        if form.validate():
            ticket = ticketType.sell( form.name.data )
            flash( f"""{ticketType['name']} {ticket.id()} to {ticketType.parent['name']} has been issued for {form.name.data}""" )
            return redirect( url_for( 'customerEventList' ) )

    return render_template( 'customer-purchase-ticket.jinja', ticketType=ticketType, form=form )






