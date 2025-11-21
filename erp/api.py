"""
ERP Emulator - API Endpoints
Provides REST API endpoints for the ERP emulator
"""
import os
import yaml
from flask import Flask, request, jsonify,render_template, send_from_directory
from flask_restful import Api, Resource
from services import MaterialService, ProductService, OrderService, ProductionPlanService,MaterialTransactionService, BOMItem



# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')


    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# Create Flask app
app = Flask(__name__)

# CORS configuration
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

api = Api(app)

# API version prefix
api_version = config['erp']['api_version']
API_PREFIX = f"/api/{api_version}"

# Error handling
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404

@app.errorhandler(400)
def bad_request(error):
    return {'error': 'Bad request'}, 400

@app.errorhandler(500)
def server_error(error):
    return {'error': 'Internal server error'}, 500
@app.route('/api/v1/status')
def status():
    return {'status': 'ok', 'service': 'ERP'}, 200


#masterdata page
# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# Serve master data management interface
@app.route('/master_data')
def master_data_page():
    return render_template('master_data.html')

# Serve documentation
@app.route('/docs/<path:path>')
def send_docs(path):
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
    return send_from_directory(docs_dir, path)

# Redirect root to master data page
#@app.route('/')
#def index():
#   return render_template('master_data.html')




# Materials API
class MaterialListAPI(Resource):
    def get(self):
        """Get all materials"""
        try:
            materials = MaterialService.get_all_materials()
            return materials
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new material"""
        try:
            material_data = request.get_json()
            if not material_data:
                return {'error': 'No data provided'}, 400
            
            material = MaterialService.create_material(material_data)
            return material, 201
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialAPI(Resource):
    def get(self, material_id):
        """Get material by ID"""
        try:
            material = MaterialService.get_material_by_id(material_id)
            if not material:
                return {'error': 'Material not found'}, 404
            
            return material
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, material_id):
        """Update a material"""
        try:
            material_data = request.get_json()
            if not material_data:
                return {'error': 'No data provided'}, 400
            
            material = MaterialService.update_material(material_id, material_data)
            if not material:
                return {'error': 'Material not found'}, 404
            
            return material
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, material_id):
        """Delete a material"""
        try:
            result = MaterialService.delete_material(material_id)
            if not result:
                return {'error': 'Material not found'}, 404
            
            return {'message': 'Material deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500
class MaterialTransactionAPI(Resource):
    #@app.route('', methods=['POST'])
    def post(self):
        data = request.get_json()
        try:
            transaction = MaterialTransactionService.create_transaction(
                material_id=data['material_id'],
                quantity=data['quantity'],
                transaction_type=data['transaction_type'],
                reference_id=data.get('reference_id'),
                reference_type=data.get('reference_type')
            )
            return jsonify({
                "id": transaction.id,
                "material_id": transaction.material_id,
                "quantity": transaction.quantity,
                "transaction_type": transaction.transaction_type,
                "reference_id": transaction.reference_id,
                "reference_type": transaction.reference_type,
                "timestamp": transaction.timestamp.isoformat()
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        
class MaterialTransactionByReferenceAPI(Resource):
    #@app.route('/mes/<int:reference_id>', methods=['GET'])
    def get(self,reference_id):
        transaction = MaterialTransactionService.get_by_reference(reference_id)
        if transaction:
            return {
                "id": transaction.id,
                "material_id": transaction.material_id,
                "quantity": transaction.quantity,
                "transaction_type": transaction.transaction_type,
                "reference_id": transaction.reference_id,
                "reference_type": transaction.reference_type,
                "timestamp": transaction.timestamp.isoformat()
            }
        else:
            return {"error": "Not found"}, 404


class MaterialByCodeAPI(Resource):
    def get(self, code):
        """Get material by code"""
        try:
            material = MaterialService.get_material_by_code(code)
            if not material:
                return {'error': 'Material not found'}, 404
            
            return material
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialStockAPI(Resource):
    def put(self, material_id):
        """Update material stock"""
        try:
            data = request.get_json()
            if not data or 'quantity_change' not in data:
                return {'error': 'No quantity_change provided'}, 400
            
            transaction_type = data.get('transaction_type', 'manual')
            result = MaterialService.update_stock(material_id, data['quantity_change'], transaction_type)
            if not result:
                return {'error': 'Material not found'}, 404
            
            return result
        except Exception as e:
            return {'error': str(e)}, 500

# Products API
class ProductListAPI(Resource):
    def get(self):
        """Get all products"""
        try:
            products = ProductService.get_all_products()
            return products
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new product"""
        try:
            product_data = request.get_json()
            if not product_data:
                return {'error': 'No data provided'}, 400
            
            product = ProductService.create_product(product_data)
            return product, 201
        except Exception as e:
            return {'error': str(e)}, 500

class ProductAPI(Resource):
    def get(self, product_id):
        """Get product by ID"""
        try:
            product = ProductService.get_product_by_id(product_id)
            if not product:
                return {'error': 'Product not found'}, 404
            
            return product
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, product_id):
        """Update a product"""
        try:
            product_data = request.get_json()
            if not product_data:
                return {'error': 'No data provided'}, 400
            
            product = ProductService.update_product(product_id, product_data)
            if not product:
                return {'error': 'Product not found'}, 404
            
            return product
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, product_id):
        """Delete a product"""
        try:
            result = ProductService.delete_product(product_id)
            if not result:
                return {'error': 'Product not found'}, 404
            
            return {'message': 'Product deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class ProductByCodeAPI(Resource):
    def get(self, code):
        """Get product by code"""
        try:
            product = ProductService.get_product_by_code(code)
            if not product:
                return {'error': 'Product not found'}, 404
            
            return product
        except Exception as e:
            return {'error': str(e)}, 500

class ProductBOMAPI(Resource):
    def get(self, product_id):
        """Get bill of materials for a product"""
        try:
            bom = ProductService.get_product_bom(product_id)
            return bom
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self, product_id):
        """Add a material to a product's bill of materials"""
        try:
            data = request.get_json()
            if not data or 'material_id' not in data or 'quantity' not in data:
                return {'error': 'Missing material_id or quantity'}, 400
            
            bom_item = ProductService.add_bom_item(product_id, data['material_id'], data['quantity'])
            if not bom_item:
                return {'error': 'Product or material not found'}, 404
            
            return bom_item, 201
        except Exception as e:
            return {'error': str(e)}, 500

class ProductBOMItemAPI(Resource):
    def delete(self, product_id, material_id):
        """Remove a material from a product's bill of materials"""
        try:
            result = ProductService.remove_bom_item(product_id, material_id)
            if not result:
                return {'error': 'BOM item not found'}, 404
            
            return {'message': 'BOM item removed successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class BOMAPI(Resource):
    def get(self):
        try:
            bom = BOMItem.get_all_bom()
            return bom
        except Exception as e:
            return {'error': str(e)}, 500    


# Orders API
class OrderListAPI(Resource):
    def get(self):
        """Get all orders"""
        try:
            orders = OrderService.get_all_orders()
            return orders
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new order"""
        try:
            order_data = request.get_json()
            if not order_data:
                return {'error': 'No data provided'}, 400
            
            order = OrderService.create_order(order_data)
            return order, 201
        except Exception as e:
            return {'error': str(e)}, 500

class OrderAPI(Resource):
    def get(self, order_id):
        """Get order by ID"""
        try:
            order = OrderService.get_order_by_id(order_id)
            if not order:
                return {'error': 'Order not found'}, 404
            
            return order
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, order_id):
        """Update an order"""
        try:
            order_data = request.get_json()
            if not order_data:
                return {'error': 'No data provided'}, 400
            
            order = OrderService.update_order(order_id, order_data)
            if not order:
                return {'error': 'Order not found'}, 404
            
            return order
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, order_id):
        """Delete an order"""
        try:
            result = OrderService.delete_order(order_id)
            if not result:
                return {'error': 'Order not found'}, 404
            
            return {'message': 'Order deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class OrderByNumberAPI(Resource):
    def get(self, order_number):
        """Get order by order number"""
        try:
            order = OrderService.get_order_by_number(order_number)
            if not order:
                return {'error': 'Order not found'}, 404
            
            return order
        except Exception as e:
            return {'error': str(e)}, 500

class OrderItemAPI(Resource):
    def post(self, order_id):
        """Add an item to an order"""
        try:
            data = request.get_json()
            if not data or 'product_id' not in data or 'quantity' not in data:
                return {'error': 'Missing product_id or quantity'}, 400
            
            order_item = OrderService.add_order_item(order_id, data['product_id'], data['quantity'])
            if not order_item:
                return {'error': 'Order or product not found'}, 404
            
            return order_item, 201
        except Exception as e:
            return {'error': str(e)}, 500

class OrderItemDeleteAPI(Resource):
    def delete(self, order_id, product_id):
        """Remove an item from an order"""
        try:
            result = OrderService.remove_order_item(order_id, product_id)
            if not result:
                return {'error': 'Order item not found'}, 404
            
            return {'message': 'Order item removed successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class OrderStatusAPI(Resource):
    def put(self, order_id):
        """Update order status"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return {'error': 'No status provided'}, 400
            
            order = OrderService.update_order_status(order_id, data['status'])
            if not order:
                return {'error': 'Order not found'}, 404
            
            return order
        except Exception as e:
            return {'error': str(e)}, 500

# Production Plans API
class ProductionPlanListAPI(Resource):
    def get(self):
        """Get all production plans"""
        try:
            plans = ProductionPlanService.get_all_production_plans()
            return plans
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new production plan"""
        try:
            plan_data = request.get_json()
            if not plan_data:
                return {'error': 'No data provided'}, 400
            
            plan = ProductionPlanService.create_production_plan(plan_data)
            return plan, 201
        except Exception as e:
            return {'error': str(e)}, 500

class ProductionPlanAPI(Resource):
    def get(self, plan_id):
        """Get production plan by ID"""
        try:
            plan = ProductionPlanService.get_production_plan_by_id(plan_id)
            if not plan:
                return {'error': 'Production plan not found'}, 404
            
            return plan
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, plan_id):
        """Update a production plan"""
        try:
            plan_data = request.get_json()
            if not plan_data:
                return {'error': 'No data provided'}, 400
            
            plan = ProductionPlanService.update_production_plan(plan_id, plan_data)
            if not plan:
                return {'error': 'Production plan not found'}, 404
            
            return plan
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, plan_id):
        """Delete a production plan"""
        try:
            result = ProductionPlanService.delete_production_plan(plan_id)
            if not result:
                return {'error': 'Production plan not found'}, 404
            
            return {'message': 'Production plan deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class ProductionPlanByNumberAPI(Resource):
    def get(self, plan_number):
        """Get production plan by plan number"""
        try:
            plan = ProductionPlanService.get_production_plan_by_number(plan_number)
            if not plan:
                return {'error': 'Production plan not found'}, 404
            
            return plan
        except Exception as e:
            return {'error': str(e)}, 500

class ProductionPlanFromOrderAPI(Resource):
    def post(self, order_id):
        """Create a production plan from an order"""
        try:
            data = request.get_json() or {}
            plan_data = {
                "order_id": order_id,
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "status": "planned"
            }

            plan = ProductionPlanService.create_production_plan(plan_data)
            return plan, 201

        except Exception as e:
            return {'error': str(e)}, 500
class ProductionPlanUpdateCountsAPI(Resource):
    def put(self, plan_id):
        data = request.get_json()
        # You'll need to implement: find the plan, match the work order, update counts.
        print(f"Received counts update for plan {plan_id}: {data}")
        return {"message": "Counts updated"}, 200


class MaterialAvailabilityAPI(Resource):
    def get(self, order_id):
        """Check material availability for an order"""
        try:
            availability = ProductionPlanService.check_material_availability(order_id)
            return availability
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialReservationAPI(Resource):
    def post(self, order_id):
        """Reserve materials for an order"""
        try:
            result = ProductionPlanService.reserve_materials(order_id)
            return result
        except Exception as e:
            return {'error': str(e)}, 500

# Register API resources
api.add_resource(MaterialListAPI, f'{API_PREFIX}/materials')
api.add_resource(MaterialAPI, f'{API_PREFIX}/materials/<int:material_id>')
api.add_resource(MaterialByCodeAPI, f'{API_PREFIX}/materials/code/<string:code>')
api.add_resource(MaterialStockAPI, f'{API_PREFIX}/materials/<int:material_id>/stock')

api.add_resource(ProductListAPI, f'{API_PREFIX}/products')
api.add_resource(ProductAPI, f'{API_PREFIX}/products/<int:product_id>')
api.add_resource(ProductByCodeAPI, f'{API_PREFIX}/products/code/<string:code>')
api.add_resource(ProductBOMAPI, f'{API_PREFIX}/products/<int:product_id>/bom')

api.add_resource(ProductBOMItemAPI, f'{API_PREFIX}/products/<int:product_id>/bom/<int:material_id>')

api.add_resource(BOMAPI, f'{API_PREFIX}/bom')

api.add_resource(OrderListAPI, f'{API_PREFIX}/orders')
api.add_resource(OrderAPI, f'{API_PREFIX}/orders/<int:order_id>')
api.add_resource(OrderByNumberAPI, f'{API_PREFIX}/orders/number/<string:order_number>')
api.add_resource(OrderItemAPI, f'{API_PREFIX}/orders/<int:order_id>/items')
api.add_resource(OrderItemDeleteAPI, f'{API_PREFIX}/orders/<int:order_id>/items/<int:product_id>')
api.add_resource(OrderStatusAPI, f'{API_PREFIX}/orders/<int:order_id>/status')

api.add_resource(ProductionPlanListAPI, f'{API_PREFIX}/production-plans')
api.add_resource(ProductionPlanAPI, f'{API_PREFIX}/production-plans/<int:plan_id>')
api.add_resource(ProductionPlanByNumberAPI, f'{API_PREFIX}/production-plans/number/<string:plan_number>')
api.add_resource(
    ProductionPlanFromOrderAPI,
    f'{API_PREFIX}/orders/<int:order_id>/create-plan',
    f'{API_PREFIX}/orders/<int:order_id>/production-plan'
)
api.add_resource(ProductionPlanUpdateCountsAPI, '/api/v1/production-plans/<int:plan_id>/update-counts')

api.add_resource(MaterialAvailabilityAPI, f'{API_PREFIX}/orders/<int:order_id>/material-availability')
api.add_resource(MaterialReservationAPI, f'{API_PREFIX}/orders/<int:order_id>/reserve-materials')
api.add_resource(MaterialTransactionAPI, f'{API_PREFIX}/material-transactions')
api.add_resource(MaterialTransactionByReferenceAPI, f'{API_PREFIX}/material-transactions/mes/<int:reference_id>')

# Root endpoint
@app.route('/')
def index():
    return {
        'name': 'ERP Emulator API',
        'version': api_version,
        'endpoints': [
            f'{API_PREFIX}/materials',
            f'{API_PREFIX}/products',
            f'{API_PREFIX}/orders',
            f'{API_PREFIX}/production-plans',
             f'{API_PREFIX}/status'
        ]
    }

def run_app():
    """Run the Flask application"""
    host = config['erp']['host']
    port = config['erp']['port']
    app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    run_app()
