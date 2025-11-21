"""
ERP Emulator - Data Models
Defines SQLAlchemy ORM models for the ERP database
"""
import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Material(Base):
    """Material model representing raw materials used in production"""
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    unit = Column(String, nullable=False)
    cost = Column(Float, nullable=False)
    stock_quantity = Column(Float, nullable=False, default=0)
    min_stock_level = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    bom_items = relationship("BOMItem", back_populates="material")
    
    def __repr__(self):
        return f"<Material(code='{self.code}', name='{self.name}', stock={self.stock_quantity} {self.unit})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'unit': self.unit,
            'cost': self.cost,
            'stock_quantity': self.stock_quantity,
            'min_stock_level': self.min_stock_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Product(Base):
    """Product model representing finished goods produced by the company"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Float, nullable=False, default=0)
    min_stock_level = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    bom_items = relationship("BOMItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product(code='{self.code}', name='{self.name}', price={self.price})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price': self.price,
            'stock_quantity': self.stock_quantity,
            'min_stock_level': self.min_stock_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BOMItem(Base):
    """Bill of Materials item linking products to their component materials"""
    __tablename__ = 'bom_items'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="bom_items")
    material = relationship("Material", back_populates="bom_items")
    
    # Constraints
    __table_args__ = (UniqueConstraint('product_id', 'material_id', name='_product_material_uc'),)
    
    def __repr__(self):
        return f"<BOMItem(product_id={self.product_id}, material_id={self.material_id}, quantity={self.quantity})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'material_id': self.material_id,
            'quantity': self.quantity,
            'product_code': self.product.code if self.product else None,
            'product': {
                'id': self.product.id,
                'code': self.product.code,
                'name': self.product.name
            } if self.product else None,
            'material_code': self.material.code if self.material else None,
            'material': {
                'id': self.material.id,
                'code': self.material.code,
                'name': self.material.name,
                'unit': self.material.unit
            } if self.material else None,
            'unit': self.material.unit if self.material else None
        }


class Order(Base):
    """Customer order for products"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # 'draft', 'confirmed', 'in_production', 'completed', 'cancelled'
    order_date = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    production_plans = relationship("ProductionPlan", back_populates="order")
    
    def __repr__(self):
        return f"<Order(order_number='{self.order_number}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_name': self.customer_name,
            'status': self.status,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(Base):
    """Line item in a customer order"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_code': self.product.code if self.product else None,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity
        }


class ProductionPlan(Base):
    """Production plan generated from customer orders"""
    __tablename__ = 'production_plans'
    
    id = Column(Integer, primary_key=True)
    plan_number = Column(String, unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'))
    status = Column(String, nullable=False)  # 'planned', 'in_progress', 'completed', 'cancelled'
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="production_plans")
    
    def __repr__(self):
        return f"<ProductionPlan(plan_number='{self.plan_number}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_number': self.plan_number,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MaterialTransaction(Base):
    __tablename__ = "material_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, nullable=False)
    quantity = Column(Float, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # "production" or "consumption"
    reference_id = Column(Integer, nullable=True)  # e.g., work_order_id
    reference_type = Column(String(50), nullable=True)  # "work_order", "mes_transaction", etc.
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
