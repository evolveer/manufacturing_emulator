"""
Shipping Services for ERP System
Handles shipment creation, status updates, and inventory management
"""
import datetime
from sqlalchemy.exc import SQLAlchemyError
from database import get_db_session, close_db_session
from shipping_models import Shipment, ShipmentItem
from models import Order, Product
from services import ProductService
from echotrace.integration import log_audit_trail

AUDIT_USER_ID = 0
AUDIT_USERNAME = "system"


class ShipmentService:
    """Service for managing shipments"""
    
    @staticmethod
    def get_all_shipments():
        """Get all shipments"""
        session = get_db_session()
        try:
            shipments = session.query(Shipment).all()
            return [shipment.to_dict() for shipment in shipments]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_shipment_by_id(shipment_id):
        """Get shipment by ID"""
        session = get_db_session()
        try:
            shipment = session.query(Shipment).filter(Shipment.id == shipment_id).first()
            return shipment.to_dict() if shipment else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_shipment_by_number(shipment_number):
        """Get shipment by shipment number"""
        session = get_db_session()
        try:
            shipment = session.query(Shipment).filter(Shipment.shipment_number == shipment_number).first()
            return shipment.to_dict() if shipment else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_shipments_by_order(order_id):
        """Get all shipments for an order"""
        session = get_db_session()
        try:
            shipments = session.query(Shipment).filter(Shipment.order_id == order_id).all()
            return [shipment.to_dict() for shipment in shipments]
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_shipment(shipment_data):
        """Create a new shipment"""
        session = get_db_session()
        try:
            # Validate order exists
            order = session.query(Order).filter(Order.id == shipment_data['order_id']).first()
            if not order:
                return None
            
            # Create shipment
            shipment = Shipment(
                shipment_number=shipment_data['shipment_number'],
                order_id=shipment_data['order_id'],
                status=shipment_data.get('status', 'pending'),
                carrier=shipment_data.get('carrier'),
                tracking_number=shipment_data.get('tracking_number'),
                shipping_address=shipment_data.get('shipping_address'),
                estimated_delivery=shipment_data.get('estimated_delivery'),
                notes=shipment_data.get('notes')
            )
            
            session.add(shipment)
            session.flush()  # Get shipment ID
            
            # Add shipment items if provided
            if 'items' in shipment_data:
                for item_data in shipment_data['items']:
                    item = ShipmentItem(
                        shipment_id=shipment.id,
                        product_id=item_data['product_id'],
                        quantity=item_data['quantity']
                    )
                    session.add(item)
            
            session.commit()
            try:
                log_audit_trail(
                    user_id=AUDIT_USER_ID,
                    username=AUDIT_USERNAME,
                    action="CREATE",
                    entity_type="Shipment",
                    entity_id=shipment.id,
                    source_system="ERP",
                    entity_name=shipment.shipment_number,
                    new_value=shipment.to_dict()
                )
            except Exception:
                pass
            return shipment.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_shipment_status(shipment_id, new_status, update_inventory=True):
        """
        Update shipment status with automatic timestamp updates and inventory management
        
        Status flow: pending -> packed -> shipped -> in_transit -> delivered
        
        Inventory is deducted when status changes to 'shipped'
        """
        session = get_db_session()
        try:
            shipment = session.query(Shipment).filter(Shipment.id == shipment_id).first()
            if not shipment:
                return None
            
            old_status = shipment.status
            shipment.status = new_status
            
            # Update timestamps based on status
            now = datetime.datetime.utcnow()
            
            if new_status == 'packed' and not shipment.packed_date:
                shipment.packed_date = now
            elif new_status == 'shipped' and not shipment.shipped_date:
                shipment.shipped_date = now
                # Deduct inventory when shipped
                if update_inventory and old_status != 'shipped':
                    ShipmentService._deduct_inventory_for_shipment(session, shipment)
            elif new_status == 'delivered' and not shipment.delivered_date:
                shipment.delivered_date = now
            
            session.commit()
            try:
                log_audit_trail(
                    user_id=AUDIT_USER_ID,
                    username=AUDIT_USERNAME,
                    action="UPDATE",
                    entity_type="Shipment",
                    entity_id=shipment.id,
                    source_system="ERP",
                    entity_name=shipment.shipment_number,
                    changes={'old_status': old_status, 'new_status': new_status}
                )
            except Exception:
                pass
            return shipment.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def _deduct_inventory_for_shipment(session, shipment):
        """Deduct product inventory when shipment is shipped"""
        for item in shipment.items:
            product = session.query(Product).filter(Product.id == item.product_id).first()
            if product:
                # Deduct from stock
                product.stock_quantity -= item.quantity
                
                # Create transaction record (using ProductService method if available)
                try:
                    ProductService.update_product_stock(
                        item.product_id,
                        -item.quantity,
                        transaction_type='shipment'
                    )
                except Exception as e:
                    print(f"Warning: Could not create transaction record: {e}")
    
    @staticmethod
    def simulate_shipment_lifecycle(shipment_id, timeframe_minutes=None):
        """
        Simulate a shipment going through its lifecycle with time delays
        
        Args:
            shipment_id: ID of the shipment
            timeframe_minutes: Dict with status durations, e.g.:
                {
                    'pending_to_packed': 5,
                    'packed_to_shipped': 10,
                    'shipped_to_in_transit': 2,
                    'in_transit_to_delivered': 30
                }
        
        Returns:
            Generator yielding status updates
        """
        import time
        
        if timeframe_minutes is None:
            timeframe_minutes = {
                'pending_to_packed': 0.1,  # 6 seconds
                'packed_to_shipped': 0.2,   # 12 seconds
                'shipped_to_in_transit': 0.1,  # 6 seconds
                'in_transit_to_delivered': 0.5  # 30 seconds
            }
        
        statuses = ['pending', 'packed', 'shipped', 'in_transit', 'delivered']
        transitions = [
            ('pending', 'packed', timeframe_minutes.get('pending_to_packed', 5)),
            ('packed', 'shipped', timeframe_minutes.get('packed_to_shipped', 10)),
            ('shipped', 'in_transit', timeframe_minutes.get('shipped_to_in_transit', 2)),
            ('in_transit', 'delivered', timeframe_minutes.get('in_transit_to_delivered', 30))
        ]
        
        for from_status, to_status, delay_minutes in transitions:
            # Wait for the specified time
            time.sleep(delay_minutes * 60)
            
            # Update status
            result = ShipmentService.update_shipment_status(shipment_id, to_status)
            if result:
                yield result
            else:
                break
    
    @staticmethod
    def update_shipment(shipment_id, shipment_data):
        """Update shipment details"""
        session = get_db_session()
        try:
            shipment = session.query(Shipment).filter(Shipment.id == shipment_id).first()
            if not shipment:
                return None
            
            # Update fields
            if 'carrier' in shipment_data:
                shipment.carrier = shipment_data['carrier']
            if 'tracking_number' in shipment_data:
                shipment.tracking_number = shipment_data['tracking_number']
            if 'shipping_address' in shipment_data:
                shipment.shipping_address = shipment_data['shipping_address']
            if 'estimated_delivery' in shipment_data:
                shipment.estimated_delivery = shipment_data['estimated_delivery']
            if 'notes' in shipment_data:
                shipment.notes = shipment_data['notes']
            
            session.commit()
            return shipment.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_shipment(shipment_id):
        """Delete a shipment"""
        session = get_db_session()
        try:
            shipment = session.query(Shipment).filter(Shipment.id == shipment_id).first()
            if not shipment:
                return False
            
            session.delete(shipment)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def add_shipment_item(shipment_id, product_id, quantity):
        """Add an item to a shipment"""
        session = get_db_session()
        try:
            shipment = session.query(Shipment).filter(Shipment.id == shipment_id).first()
            if not shipment:
                return None
            
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            item = ShipmentItem(
                shipment_id=shipment_id,
                product_id=product_id,
                quantity=quantity
            )
            
            session.add(item)
            session.commit()
            return item.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def remove_shipment_item(shipment_id, product_id):
        """Remove an item from a shipment"""
        session = get_db_session()
        try:
            item = session.query(ShipmentItem).filter(
                ShipmentItem.shipment_id == shipment_id,
                ShipmentItem.product_id == product_id
            ).first()
            
            if not item:
                return False
            
            session.delete(item)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
