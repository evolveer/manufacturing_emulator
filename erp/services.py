"""
ERP Emulator - Service Layer
Provides business logic for the ERP emulator
"""
from datetime import datetime
import uuid
from sqlalchemy.exc import SQLAlchemyError
from database import get_db_session, close_db_session
from models import Material, Product, BOMItem, Order, OrderItem, ProductionPlan, MaterialTransaction

class MaterialService:
    """Service for material management"""
    
    @staticmethod
    def get_all_materials():
        """Get all materials"""
        session = get_db_session()
        try:
            materials = session.query(Material).all()
            return [material.to_dict() for material in materials]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_material_by_id(material_id):
        """Get material by ID"""
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            return material.to_dict() if material else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_material_by_code(code):
        """Get material by code"""
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.code == code).first()
            return material.to_dict() if material else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_material(material_data):
        """Create a new material"""
        session = get_db_session()
        try:
            material = Material(
                code=material_data['code'],
                name=material_data['name'],
                description=material_data.get('description'),
                unit=material_data['unit'],
                cost=material_data['cost'],
                stock_quantity=material_data.get('stock_quantity', 0),
                min_stock_level=material_data.get('min_stock_level', 0)
            )
            session.add(material)
            session.commit()
            return material.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_material(material_id, material_data):
        """Update an existing material"""
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            if not material:
                return None
            
            # Update fields
            for key, value in material_data.items():
                if hasattr(material, key) and key not in ['id', 'created_at', 'updated_at']:
                    setattr(material, key, value)
            
            session.commit()
            return material.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_stock(material_id, quantity_change, transaction_type):
        """Update material stock quantity"""
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            if not material:
                return None
            
            # Update stock quantity
            material.stock_quantity += quantity_change
            
            # Check if stock is below minimum level
            is_below_min = material.stock_quantity < material.min_stock_level
            
            session.commit()
            return {
                'material': material.to_dict(),
                'is_below_min': is_below_min,
                'transaction_type': transaction_type
            }
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_material(material_id):
        """Delete a material"""
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            if not material:
                return False
            
            session.delete(material)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
            
class MaterialTransactionService:
    
    @staticmethod
    def create_transaction(material_id, quantity, transaction_type, reference_id=None, reference_type=None):
        session = get_db_session()
        try:
            transaction = MaterialTransaction(
                material_id=material_id,
                quantity=quantity,
                transaction_type=transaction_type,
                reference_id=reference_id,
                reference_type=reference_type
            )
            session.add(transaction)
            session.commit()
            return transaction
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_by_reference(reference_id):
        session = get_db_session()
        try:
            return session.query(MaterialTransaction).filter(
                MaterialTransaction.reference_id == reference_id
            ).first()
        finally:
            close_db_session(session)

class ProductService:
    """Service for product management"""
    
    @staticmethod
    def get_all_products():
        """Get all products"""
        session = get_db_session()
        try:
            products = session.query(Product).all()
            return [product.to_dict() for product in products]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_product_by_id(product_id):
        """Get product by ID"""
        session = get_db_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            return product.to_dict() if product else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_product_by_code(code):
        """Get product by code"""
        session = get_db_session()
        try:
            product = session.query(Product).filter(Product.code == code).first()
            return product.to_dict() if product else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_product(product_data):
        """Create a new product"""
        session = get_db_session()
        try:
            product = Product(
                code=product_data['code'],
                name=product_data['name'],
                description=product_data.get('description'),
                category=product_data.get('category'),
                price=product_data['price'],
                stock_quantity=product_data.get('stock_quantity', 0),
                min_stock_level=product_data.get('min_stock_level', 0)
            )
            session.add(product)
            session.commit()
            return product.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_product(product_id, product_data):
        """Update an existing product"""
        session = get_db_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            # Update fields
            for key, value in product_data.items():
                if hasattr(product, key) and key not in ['id', 'created_at', 'updated_at']:
                    setattr(product, key, value)
            
            session.commit()
            return product.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_product(product_id):
        """Delete a product"""
        session = get_db_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return False
            
            session.delete(product)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def update_product_stock(product_id, quantity_change, transaction_type='production'):
        """Update product stock quantity"""
        session = get_db_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None

            product.stock_quantity += quantity_change
            below_min = product.stock_quantity < product.min_stock_level
            session.commit()
            return {
                'product': product.to_dict(),
                'is_below_min': below_min,
                'transaction_type': transaction_type
            }
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_product_bom(product_id):
        """Get bill of materials for a product"""
        session = get_db_session()
        try:
            bom_items = session.query(BOMItem).filter(BOMItem.product_id == product_id).all()
            return [item.to_dict() for item in bom_items]
        finally:
            close_db_session(session)
    
    @staticmethod
    def add_bom_item(product_id, material_id, quantity):
        """Add a material to a product's bill of materials"""
        session = get_db_session()
        try:
            # Check if product and material exist
            product = session.query(Product).filter(Product.id == product_id).first()
            material = session.query(Material).filter(Material.id == material_id).first()
            if not product or not material:
                return None
            
            # Check if BOM item already exists
            existing_item = session.query(BOMItem).filter(
                BOMItem.product_id == product_id,
                BOMItem.material_id == material_id
            ).first()
            
            if existing_item:
                # Update quantity if item exists
                existing_item.quantity = quantity
                session.commit()
                return existing_item.to_dict()
            else:
                # Create new BOM item
                bom_item = BOMItem(
                    product_id=product_id,
                    material_id=material_id,
                    quantity=quantity
                )
                session.add(bom_item)
                session.commit()
                return bom_item.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def remove_bom_item(product_id, material_id):
        """Remove a material from a product's bill of materials"""
        session = get_db_session()
        try:
            bom_item = session.query(BOMItem).filter(
                BOMItem.product_id == product_id,
                BOMItem.material_id == material_id
            ).first()
            
            if not bom_item:
                return False
            
            session.delete(bom_item)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_all_bom():
        """Get all BOM entries"""
        session = get_db_session()
        try:
            bom_entries = session.query(BOMItem).all()
            result = []
            for entry in bom_entries:
                result.append({
                    'product_id': entry.product_id,
                    'material_id': entry.material_id,
                    'quantity': entry.quantity
                })
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            close_db_session(session)

class OrderService:
    """Service for order management"""
    
    @staticmethod
    def get_all_orders():
        """Get all orders"""
        session = get_db_session()
        try:
            orders = session.query(Order).all()
            return [order.to_dict() for order in orders]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_order_by_id(order_id):
        """Get order by ID"""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            return order.to_dict() if order else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_order_by_number(order_number):
        """Get order by order number"""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.order_number == order_number).first()
            return order.to_dict() if order else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_order(order_data):
        """Create a new order"""
        session = get_db_session()
        try:
            # Generate order number if not provided
            if 'order_number' not in order_data:
                order_data['order_number'] = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            # Convert ISO format strings to datetime objects
            order_date = order_data.get("order_date", datetime.utcnow())
            if isinstance(order_date, str):
                order_date = datetime.fromisoformat(order_date.replace("Z", "+00:00"))

            due_date = order_data.get("due_date")
            if due_date and isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            # Create order
            order = Order(
                order_number=order_data["order_number"],
                customer_name=order_data["customer_name"],
                status=order_data["status"],
                order_date=order_date,
                due_date=due_date
            )
            session.add(order)
            session.flush()  # Flush to get the order ID
            
            # Add order items if provided
            if 'items' in order_data and isinstance(order_data['items'], list):
                for item_data in order_data['items']:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item_data['product_id'],
                        quantity=item_data['quantity']
                    )
                    session.add(order_item)
            
            session.commit()
            return order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_order(order_id, order_data):
        """Update an existing order"""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            
            # Update order fields
            for key, value in order_data.items():
                if hasattr(order, key) and key not in ['id', 'created_at', 'updated_at', 'items']:
                    setattr(order, key, value)
            
            # Update order items if provided
            if 'items' in order_data and isinstance(order_data['items'], list):
                # Remove existing items
                session.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
                
                # Add new items
                for item_data in order_data['items']:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item_data['product_id'],
                        quantity=item_data['quantity']
                    )
                    session.add(order_item)
            
            session.commit()
            return order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_order(order_id):
        """Delete an order"""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False
            
            session.delete(order)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def add_order_item(order_id, product_id, quantity):
        """Add an item to an order"""
        session = get_db_session()
        try:
            # Check if order and product exist
            order = session.query(Order).filter(Order.id == order_id).first()
            product = session.query(Product).filter(Product.id == product_id).first()
            if not order or not product:
                return None
            
            # Check if order item already exists
            existing_item = session.query(OrderItem).filter(
                OrderItem.order_id == order_id,
                OrderItem.product_id == product_id
            ).first()
            
            if existing_item:
                # Update quantity if item exists
                existing_item.quantity = quantity
                session.commit()
                return existing_item.to_dict()
            else:
                # Create new order item
                order_item = OrderItem(
                    order_id=order_id,
                    product_id=product_id,
                    quantity=quantity
                )
                session.add(order_item)
                session.commit()
                return order_item.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def remove_order_item(order_id, product_id):
        """Remove an item from an order"""
        session = get_db_session()
        try:
            order_item = session.query(OrderItem).filter(
                OrderItem.order_id == order_id,
                OrderItem.product_id == product_id
            ).first()
            
            if not order_item:
                return False
            
            session.delete(order_item)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_order_status(order_id, status):
        """Update order status"""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            
            order.status = status
            session.commit()
            return order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)


class ProductionPlanService:
    """Service for production planning"""

    @staticmethod
    def _parse_datetime(value):
        """Convert incoming values (string/date/datetime) to datetime or None"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Accept YYYY-MM-DD by appending midnight
                if len(value) == 10:
                    return datetime.strptime(value, "%Y-%m-%d")
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            # date object -> datetime at midnight
            return datetime(value.year, value.month, value.day)
        return None
    
    @staticmethod
    def get_all_production_plans():
        """Get all production plans"""
        session = get_db_session()
        try:
            plans = session.query(ProductionPlan).all()
            return [plan.to_dict() for plan in plans]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_production_plan_by_id(plan_id):
        """Get production plan by ID"""
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.id == plan_id).first()
            return plan.to_dict() if plan else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_production_plan_by_number(plan_number):
        """Get production plan by plan number"""
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.plan_number == plan_number).first()
            return plan.to_dict() if plan else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_production_plan(plan_data):
        """Create a new production plan"""
        session = get_db_session()
        try:
            # Generate plan number if not provided
            if 'plan_number' not in plan_data:
                plan_data['plan_number'] = f"PP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

            start_dt = ProductionPlanService._parse_datetime(plan_data.get('start_date'))
            end_dt = ProductionPlanService._parse_datetime(plan_data.get('end_date'))
            
            # Create production plan
            plan = ProductionPlan(
                plan_number=plan_data['plan_number'],
                order_id=plan_data.get('order_id'),
                status=plan_data.get('status', 'planned'),
                start_date=start_dt,
                end_date=end_dt
            )
            session.add(plan)
            session.commit()
            
            # If plan is created from an order, update order status
            if plan.order_id:
                order = session.query(Order).filter(Order.id == plan.order_id).first()
                if order and order.status == 'confirmed':
                    order.status = 'in_production'
                    session.commit()
            
            return plan.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_production_plan(plan_id, plan_data):
        """Update an existing production plan"""
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.id == plan_id).first()
            if not plan:
                return None
            
            # Update fields
            for key, value in plan_data.items():
                if key in ['id', 'created_at', 'updated_at']:
                    continue
                if key in ['start_date', 'end_date']:
                    setattr(plan, key, ProductionPlanService._parse_datetime(value))
                elif hasattr(plan, key):
                    setattr(plan, key, value)
            
            session.commit()
            
            # Update order status if plan status changes
            if 'status' in plan_data and plan.order_id:
                order = session.query(Order).filter(Order.id == plan.order_id).first()
                if order:
                    if plan.status == 'completed' and order.status == 'in_production':
                        order.status = 'completed'
                    elif plan.status == 'cancelled' and order.status == 'in_production':
                        order.status = 'confirmed'  # Revert to confirmed status
                    session.commit()
            
            return plan.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_production_plan(plan_id):
        """Delete a production plan"""
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.id == plan_id).first()
            if not plan:
                return False
            
            # Update order status if plan is deleted
            if plan.order_id:
                order = session.query(Order).filter(Order.id == plan.order_id).first()
                if order and order.status == 'in_production':
                    order.status = 'confirmed'  # Revert to confirmed status
            
            session.delete(plan)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_plan_from_order(order_id, start_date=None, end_date=None):
        """Create a production plan from an order"""
        session = get_db_session()
        try:
            # Check if order exists
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            
            # Check if order is in confirmed status
            if order.status != 'confirmed':
                return None
            
            # Generate plan number
            plan_number = f"PP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Create production plan
            plan = ProductionPlan(
                plan_number=plan_number,
                order_id=order_id,
                status='planned',
                start_date=start_date,
                end_date=end_date
            )
            session.add(plan)
            
            # Update order status
            order.status = 'in_production'
            
            session.commit()
            return plan.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def check_material_availability(order_id):
        """Check if materials are available for an order"""
        session = get_db_session()
        try:
            # Get order items
            order_items = session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            if not order_items:
                return {'available': False, 'message': 'No items in order'}
            
            # Check material availability for each product in the order
            materials_needed = {}
            
            for order_item in order_items:
                product_id = order_item.product_id
                quantity = order_item.quantity
                
                # Get BOM items for the product
                bom_items = session.query(BOMItem).filter(BOMItem.product_id == product_id).all()
                
                for bom_item in bom_items:
                    material_id = bom_item.material_id
                    material_quantity = bom_item.quantity * quantity
                    
                    if material_id in materials_needed:
                        materials_needed[material_id] += material_quantity
                    else:
                        materials_needed[material_id] = material_quantity
            
            # Check if materials are available in stock
            unavailable_materials = []
            
            for material_id, quantity_needed in materials_needed.items():
                material = session.query(Material).filter(Material.id == material_id).first()
                
                if material.stock_quantity < quantity_needed:
                    unavailable_materials.append({
                        'material_id': material_id,
                        'material_code': material.code,
                        'material_name': material.name,
                        'available': material.stock_quantity,
                        'needed': quantity_needed,
                        'shortage': quantity_needed - material.stock_quantity
                    })
            
            if unavailable_materials:
                return {
                    'available': False,
                    'message': 'Some materials are not available in sufficient quantity',
                    'unavailable_materials': unavailable_materials
                }
            else:
                return {
                    'available': True,
                    'message': 'All materials are available',
                    'materials_needed': [
                        {
                            'material_id': material_id,
                            'quantity': quantity
                        } for material_id, quantity in materials_needed.items()
                    ]
                }
        finally:
            close_db_session(session)
    
    @staticmethod
    def reserve_materials(order_id):
        """Reserve materials for an order"""
        session = get_db_session()
        try:
            # Check material availability
            availability = ProductionPlanService.check_material_availability(order_id)
            if not availability['available']:
                return availability
            
            # Get order items
            order_items = session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            
            # Calculate materials needed
            materials_needed = {}
            
            for order_item in order_items:
                product_id = order_item.product_id
                quantity = order_item.quantity
                
                # Get BOM items for the product
                bom_items = session.query(BOMItem).filter(BOMItem.product_id == product_id).all()
                
                for bom_item in bom_items:
                    material_id = bom_item.material_id
                    material_quantity = bom_item.quantity * quantity
                    
                    if material_id in materials_needed:
                        materials_needed[material_id] += material_quantity
                    else:
                        materials_needed[material_id] = material_quantity
            
            # Reserve materials (reduce stock)
            for material_id, quantity_needed in materials_needed.items():
                material = session.query(Material).filter(Material.id == material_id).first()
                material.stock_quantity -= quantity_needed
            
            session.commit()
            return {
                'success': True,
                'message': 'Materials reserved successfully',
                'materials_reserved': [
                    {
                        'material_id': material_id,
                        'quantity': quantity
                    } for material_id, quantity in materials_needed.items()
                ]
            }
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
