"""
Shipping Models for ERP System
"""
import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from models import Base


class Shipment(Base):
    """Shipment tracking for orders"""
    __tablename__ = 'shipments'
    
    id = Column(Integer, primary_key=True)
    shipment_number = Column(String, unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    status = Column(String, nullable=False)  # 'pending', 'packed', 'shipped', 'in_transit', 'delivered', 'cancelled'
    carrier = Column(String)
    tracking_number = Column(String)
    shipping_address = Column(Text)
    packed_date = Column(DateTime)
    shipped_date = Column(DateTime)
    estimated_delivery = Column(DateTime)
    delivered_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    order = relationship("Order", backref="shipments")
    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Shipment(shipment_number='{self.shipment_number}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'shipment_number': self.shipment_number,
            'order_id': self.order_id,
            'status': self.status,
            'carrier': self.carrier,
            'tracking_number': self.tracking_number,
            'shipping_address': self.shipping_address,
            'packed_date': self.packed_date.isoformat() if self.packed_date else None,
            'shipped_date': self.shipped_date.isoformat() if self.shipped_date else None,
            'estimated_delivery': self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            'delivered_date': self.delivered_date.isoformat() if self.delivered_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items] if self.items else []
        }


class ShipmentItem(Base):
    """Items in a shipment"""
    __tablename__ = 'shipment_items'
    
    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey('shipments.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    shipment = relationship("Shipment", back_populates="items")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<ShipmentItem(shipment_id={self.shipment_id}, product_id={self.product_id}, quantity={self.quantity})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'product': {
                'id': self.product.id,
                'code': self.product.code,
                'name': self.product.name
            } if self.product else None
        }
