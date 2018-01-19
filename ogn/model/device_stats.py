from sqlalchemy import Column, Integer, Date, DateTime, Float, ForeignKey, SmallInteger, Boolean, String
from sqlalchemy.orm import relationship

from .base import Base


class DeviceStats(Base):
    __tablename__ = "device_stats"

    id = Column(Integer, primary_key=True)

    date = Column(Date)
    max_altitude = Column(Float)
    receiver_count = Column(Integer)
    aircraft_beacon_count = Column(Integer)
    firstseen = Column(DateTime)
    lastseen = Column(DateTime)
    aircraft_type = Column(SmallInteger)
    stealth = Column(Boolean)
    software_version = Column(Float)
    hardware_version = Column(SmallInteger)
    real_address = Column(String(6))

    # Relations
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='SET NULL'), index=True)
    device = relationship('Device', foreign_keys=[device_id], backref='stats')

    def __repr__(self):
        return "<DeviceStats: %s,%s,%s,%s>" % (
            self.date,
            self.receiver_count,
            self.aircraft_beacon_count,
            self.max_altitude)
