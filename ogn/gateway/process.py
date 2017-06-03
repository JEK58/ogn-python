import logging
from ogn.commands.dbutils import session
from ogn.model import AircraftBeacon, ReceiverBeacon, Location
from ogn.parser import parse_aprs, parse_ogn_receiver_beacon, parse_ogn_aircraft_beacon, ParseError

logger = logging.getLogger(__name__)


def replace_lonlat_with_wkt(message):
    location = Location(message['longitude'], message['latitude'])
    message['location_wkt'] = location.to_wkt()
    del message['latitude']
    del message['longitude']
    return message


def message_to_beacon(raw_message, reference_date):
    beacon = None

    if raw_message[0] != '#':
        try:
            message = parse_aprs(raw_message, reference_date)
            # symboltable / symbolcodes used by OGN:
            # I&: used as receiver
            # /X: helicopter_rotorcraft
            # /': glider_or_motorglider
            # \^: powered_aircraft
            # /g: para_glider
            # /O: ?
            # /^: ?
            # \n: ?
            # /z: ?
            # /o: ?
            if 'symboltable' not in message and 'symbolcode' not in message:
                # we have a receiver_beacon (status message)
                message.update(parse_ogn_receiver_beacon(message['comment']))
                beacon = ReceiverBeacon(**message)
            elif message['symboltable'] == "I" and message['symbolcode'] == '&':
                # ... we have a receiver_beacon
                if message['comment']:
                    message.update(parse_ogn_receiver_beacon(message['comment']))
                message = replace_lonlat_with_wkt(message)
                beacon = ReceiverBeacon(**message)
            else:
                # ... we have a aircraft_beacon
                message.update(parse_ogn_aircraft_beacon(message['comment']))
                message = replace_lonlat_with_wkt(message)
                beacon = AircraftBeacon(**message)
        except ParseError as e:
            logger.error('Received message: {}'.format(raw_message))
            logger.error('Drop packet, {}'.format(e.message))
        except TypeError as e:
            logger.error('TypeError: {}'.format(raw_message))

    return beacon


def process_beacon(raw_message, reference_date=None):
    beacon = message_to_beacon(raw_message, reference_date)
    if beacon is not None:
        session.add(beacon)
        session.commit()
        logger.debug('Received message: {}'.format(raw_message))
