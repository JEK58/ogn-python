import os
import re

from manager import Manager
from ogn.commands.dbutils import session
from ogn.model import AircraftBeacon, ReceiverBeacon
from ogn.utils import open_file


manager = Manager()

PATTERN = '^.+\.txt\_(\d{4}\-\d{2}\-\d{2})(\.gz)?$'


@manager.command
def convert_logfile(path, logfile='main.log', loglevel='INFO'):
    """Convert ogn logfiles to csv logfiles (one for aircraft beacons and one for receiver beacons) <arg: path>. Logfile name: blablabla.txt_YYYY-MM-DD."""

    if os.path.isfile(path):
        head, tail = os.path.split(path)
        convert(tail, path=head)
        print("Finished")
    elif os.path.isdir(path):
        for filename in os.listdir(path):
            convert(filename, path=path)
        print("Finished")
    else:
        print("Not a file nor a path: {}".format(path))


def convert(sourcefile, path=''):
    import csv
    import gzip
    import datetime

    from ogn.gateway.process import message_to_beacon

    match = re.search(PATTERN, sourcefile)
    if match:
        reference_date_string = match.group(1)
        reference_date = datetime.datetime.strptime(reference_date_string, "%Y-%m-%d")

        aircraft_beacon_filename = os.path.join(path, 'aircraft_beacons.csv_' + reference_date_string + '.gz')
        receiver_beacon_filename = os.path.join(path, 'receiver_beacons.csv_' + reference_date_string + '.gz')

        if not os.path.exists(aircraft_beacon_filename) and not os.path.exists(receiver_beacon_filename):
            print("Reading file: {}".format(sourcefile))
            fout_ab = gzip.open(aircraft_beacon_filename, 'wt')
            fout_rb = gzip.open(receiver_beacon_filename, 'wt')
        else:
            print("Output files for file {} already exists. Skipping".format(sourcefile))
            return
    else:
        print("filename '{}' does not match pattern. Skipping".format(sourcefile))
        return

    fin = open_file(os.path.join(path, sourcefile))

    # get total lines of the input file
    total = 0
    for line in fin:
        total += 1
    fin.seek(0)

    aircraft_beacons = list()
    receiver_beacons = list()

    progress = -1
    num_lines = 0

    wr_ab = csv.writer(fout_ab, delimiter=',')
    wr_ab.writerow(AircraftBeacon.get_csv_columns())

    wr_rb = csv.writer(fout_rb, delimiter=',')
    wr_rb.writerow(ReceiverBeacon.get_csv_columns())

    print('Start importing ogn-logfile')
    for line in fin:
        num_lines += 1
        if int(100 * num_lines / total) != progress:
            progress = round(100 * num_lines / total)
            print("\rReading line {} ({}%)".format(num_lines, progress), end='')
            if len(aircraft_beacons) > 0:
                for beacon in aircraft_beacons:
                    wr_ab.writerow(beacon.get_csv_values())
                aircraft_beacons = list()
            if len(receiver_beacons) > 0:
                for beacon in receiver_beacons:
                    wr_rb.writerow(beacon.get_csv_values())
                receiver_beacons = list()

        beacon = message_to_beacon(line.strip(), reference_date=reference_date)
        if beacon is not None:
            if isinstance(beacon, AircraftBeacon):
                aircraft_beacons.append(beacon)
            elif isinstance(beacon, ReceiverBeacon):
                receiver_beacons.append(beacon)

    if len(aircraft_beacons) > 0:
        for beacon in aircraft_beacons:
            wr_ab.writerow(beacon.get_csv_values())
    if len(receiver_beacons) > 0:
        for beacon in receiver_beacons:
            wr_rb.writerow(beacon.get_csv_values())

    fin.close()
    fout_ab.close()
    fout_rb.close()


@manager.command
def drop_indices():
    """Drop indices of AircraftBeacon."""
    session.execute("""
        DROP INDEX IF EXISTS idx_aircraft_beacons_location;
        DROP INDEX IF EXISTS ix_aircraft_beacons_receiver_id;
        DROP INDEX IF EXISTS ix_aircraft_beacons_device_id;
        DROP INDEX IF EXISTS ix_aircraft_beacons_timestamp;
    """)
    print("Dropped indices of AircraftBeacon")

    # disable constraint trigger
    session.execute("""
        ALTER TABLE aircraft_beacons DISABLE TRIGGER ALL
    """)
    print("Disabled constraint triggers")


@manager.command
def create_indices():
    """Create indices for AircraftBeacon."""
    session.execute("""
        CREATE INDEX idx_aircraft_beacon_location ON aircraft_beacons USING GIST(location);
        CREATE INDEX ix_aircraft_beacon_receiver_id ON aircraft_beacons USING BTREE(receiver_id);
        CREATE INDEX ix_aircraft_beacon_device_id ON aircraft_beacons USING BTREE(device_id);
        CREATE INDEX ix_aircraft_beacon_timestamp ON aircraft_beacons USING BTREE(timestamp);
    """)
    print("Created indices for AircraftBeacon")

    session.execute("""
        ALTER TABLE aircraft_beacons ENABLE TRIGGER ALL
    """)
    print("Enabled constraint triggers")


@manager.command
def import_csv_logfile(path, logfile='main.log', loglevel='INFO'):
    """Import csv logfile <arg: csv logfile>."""

    import datetime

    import os
    if os.path.isfile(path):
        print("{}: Importing file: {}".format(datetime.datetime.now(), path))
        import_logfile(path)
    elif os.path.isdir(path):
        print("{}: Scanning path: {}".format(datetime.datetime.now(), path))
        for filename in os.listdir(path):
            print("{}: Importing file: {}".format(datetime.datetime.now(), filename))
            import_logfile(os.path.join(path, filename))
    else:
        print("{}: Path {} not found.".format(datetime.datetime.now(), path))

    print("{}: Finished.".format(datetime.datetime.now()))


def import_logfile(path):
    import os
    import re

    head, tail = os.path.split(path)
    match = re.search('^.+\.csv\_(\d{4}\-\d{2}\-\d{2}).+?$', tail)
    if match:
        reference_date_string = match.group(1)
    else:
        print("filename '{}' does not match pattern. Skipping".format(path))
        return

    f = open_file(path)
    header = f.readline().strip()
    f.close()

    aircraft_beacon_header = ','.join(AircraftBeacon.get_csv_columns())
    receiver_beacon_header = ','.join(ReceiverBeacon.get_csv_columns())

    if header == aircraft_beacon_header:
        if check_no_beacons('aircraft_beacons', reference_date_string):
            import_aircraft_beacon_logfile(path)
        else:
            print("For {} beacons already exist. Skipping".format(reference_date_string))
    elif header == receiver_beacon_header:
        if check_no_beacons('receiver_beacons', reference_date_string):
            import_receiver_beacon_logfile(path)
        else:
            print("For {} beacons already exist. Skipping".format(reference_date_string))
    else:
        print("Unknown file type: {}".format(tail))


def check_no_beacons(tablename, reference_date_string):
    result = session.execute("""SELECT * FROM {0} WHERE timestamp BETWEEN '{1} 00:00:00' AND '{1} 23:59:59' LIMIT 1""".format(tablename, reference_date_string))
    if result.fetchall():
        return False
    else:
        return True


def import_aircraft_beacon_logfile(csv_logfile):
    SQL_TEMPTABLE_STATEMENT = """
    DROP TABLE IF EXISTS aircraft_beacons_temp;
    CREATE TABLE aircraft_beacons_temp(
        location geometry,
        altitude integer,
        name character varying,
        receiver_name character varying(9),
        dstcall character varying,
        "timestamp" timestamp without time zone,
        track integer,
        ground_speed double precision,

        address_type smallint,
        aircraft_type smallint,
        stealth boolean,
        address character varying(6),
        climb_rate double precision,
        turn_rate double precision,
        flightlevel double precision,
        signal_quality double precision,
        error_count integer,
        frequency_offset double precision,
        gps_status character varying,
        software_version double precision,
        hardware_version smallint,
        real_address character varying(6),
        signal_power double precision,

        location_mgrs character varying(15)
        );
    """

    session.execute(SQL_TEMPTABLE_STATEMENT)

    SQL_COPY_STATEMENT = """
    COPY aircraft_beacons_temp(%s) FROM STDIN WITH
        CSV
        HEADER
        DELIMITER AS ','
    """

    file = open_file(csv_logfile)
    column_names = ','.join(AircraftBeacon.get_csv_columns())
    sql = SQL_COPY_STATEMENT % column_names

    print("Start importing logfile: {}".format(csv_logfile))

    conn = session.connection().connection
    cursor = conn.cursor()
    cursor.copy_expert(sql=sql, file=file)
    conn.commit()
    cursor.close()
    file.close()
    print("Read logfile into temporary table")

    # create device if not exist
    session.execute("""
        INSERT INTO devices(address)
        SELECT DISTINCT(t.address)
        FROM aircraft_beacons_temp t
        WHERE NOT EXISTS (SELECT 1 FROM devices d WHERE d.address = t.address)
    """)
    print("Inserted missing Devices")

    # create receiver if not exist
    session.execute("""
        INSERT INTO receivers(name)
        SELECT DISTINCT(t.receiver_name)
        FROM aircraft_beacons_temp t
        WHERE NOT EXISTS (SELECT 1 FROM receivers r WHERE r.name = t.receiver_name)
    """)
    print("Inserted missing Receivers")

    session.execute("""
        INSERT INTO aircraft_beacons(location, altitude, name, receiver_name, dstcall, timestamp, track, ground_speed,
                                    address_type, aircraft_type, stealth, address, climb_rate, turn_rate, flightlevel, signal_quality, error_count, frequency_offset, gps_status, software_version, hardware_version, real_address, signal_power,
                                    receiver_id, device_id)
        SELECT t.location, t.altitude, t.name, t.receiver_name, t.dstcall, t.timestamp, t.track, t.ground_speed,
               t.address_type, t.aircraft_type, t.stealth, t.address, t.climb_rate, t.turn_rate, t.flightlevel, t.signal_quality, t.error_count, t.frequency_offset, t.gps_status, t.software_version, t.hardware_version, t.real_address, t.signal_power,
               r.id, d.id
        FROM aircraft_beacons_temp t, receivers r, devices d
        WHERE t.receiver_name = r.name AND t.address = d.address
    """)
    print("Wrote AircraftBeacons from temporary table into final table")

    session.execute("""DROP TABLE aircraft_beacons_temp""")
    print("Dropped temporary table")

    session.commit()
    print("Finished")


def import_receiver_beacon_logfile(csv_logfile):
    """Import csv logfile <arg: csv logfile>."""

    SQL_TEMPTABLE_STATEMENT = """
    DROP TABLE IF EXISTS receiver_beacons_temp;
    CREATE TABLE receiver_beacons_temp(
        location geometry,
        altitude integer,
        name character varying,
        receiver_name character varying(9),
        dstcall character varying,
        "timestamp" timestamp without time zone,
        track integer,
        ground_speed double precision,

        version character varying,
        platform character varying,
        cpu_load double precision,
        free_ram double precision,
        total_ram double precision,
        ntp_error double precision,
        rt_crystal_correction double precision,
        voltage double precision,
        amperage double precision,
        cpu_temp double precision,
        senders_visible integer,
        senders_total integer,
        rec_input_noise double precision,
        senders_signal double precision,
        senders_messages integer,
        good_senders_signal double precision,
        good_senders integer,
        good_and_bad_senders integer
        );
    """

    session.execute(SQL_TEMPTABLE_STATEMENT)

    SQL_COPY_STATEMENT = """
    COPY receiver_beacons_temp(%s) FROM STDIN WITH
        CSV
        HEADER
        DELIMITER AS ','
    """

    file = open_file(csv_logfile)
    column_names = ','.join(ReceiverBeacon.get_csv_columns())
    sql = SQL_COPY_STATEMENT % column_names

    print("Start importing logfile: {}".format(csv_logfile))

    conn = session.connection().connection
    cursor = conn.cursor()
    cursor.copy_expert(sql=sql, file=file)
    conn.commit()
    cursor.close()
    file.close()
    print("Read logfile into temporary table")

    # create receiver if not exist
    session.execute("""
        INSERT INTO receivers(name)
        SELECT DISTINCT(t.name)
        FROM receiver_beacons_temp t
        WHERE NOT EXISTS (SELECT 1 FROM receivers r WHERE r.name = t.name)
    """)
    print("Inserted missing Receivers")

    session.execute("""
        INSERT INTO receiver_beacons(location, altitude, name, receiver_name, dstcall, timestamp, track, ground_speed,
                                    version, platform, cpu_load, free_ram, total_ram, ntp_error, rt_crystal_correction, voltage,amperage, cpu_temp, senders_visible, senders_total, rec_input_noise, senders_signal, senders_messages, good_senders_signal, good_senders, good_and_bad_senders,
                                    receiver_id)
        SELECT t.location, t.altitude, t.name, t.receiver_name, t.dstcall, t.timestamp, t.track, t.ground_speed,
               t.version, t.platform, t.cpu_load, t.free_ram, t.total_ram, t.ntp_error, t.rt_crystal_correction, t.voltage,amperage, t.cpu_temp, t.senders_visible, t.senders_total, t.rec_input_noise, t.senders_signal, t.senders_messages, t.good_senders_signal, t.good_senders, t.good_and_bad_senders,
               r.id
        FROM receiver_beacons_temp t, receivers r
        WHERE t.name = r.name
    """)
    print("Wrote ReceiverBeacons from temporary table into final table")

    session.execute("""DROP TABLE receiver_beacons_temp""")
    print("Dropped temporary table")

    session.commit()
    print("Finished")
