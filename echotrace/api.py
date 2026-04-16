"""
EchoTrace API
RESTful API for audit trail management and search
"""

from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
from datetime import datetime
from typing import Optional

from echotrace.services import AuditTrailService, AuditTrailSearchService
from echotrace.database import init_db


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
api = Api(app)


class AuditTrailResource(Resource):
    """Resource for creating and retrieving audit trail records"""
    
    def post(self):
        """Create a new audit trail entry"""
        try:
            data = request.get_json()
            
            # Required fields
            required_fields = ['user_id', 'username', 'action', 'entity_type', 'entity_id', 'source_system']
            for field in required_fields:
                if field not in data:
                    return {'error': f'Missing required field: {field}'}, 400
            
            # Create audit trail record
            audit_record = AuditTrailService.log_action(
                user_id=data['user_id'],
                username=data['username'],
                action=data['action'],
                entity_type=data['entity_type'],
                entity_id=data['entity_id'],
                source_system=data['source_system'],
                user_role=data.get('user_role'),
                entity_name=data.get('entity_name'),
                reason=data.get('reason'),
                old_value=data.get('old_value'),
                new_value=data.get('new_value'),
                changes=data.get('changes'),
                source_ip=data.get('source_ip', request.remote_addr),
                session_id=data.get('session_id'),
                parent_id=data.get('parent_id'),
                batch_number=data.get('batch_number'),
                order_number=data.get('order_number'),
                signature=data.get('signature'),
                signature_meaning=data.get('signature_meaning')
            )
            
            return audit_record.to_dict(), 201
        
        except Exception as e:
            return {'error': str(e)}, 500


class AuditTrailSearchResource(Resource):
    """Resource for searching audit trail records"""
    
    def get(self):
        """Search audit trail records with filters"""
        try:
            # Get query parameters
            user_id = request.args.get('user_id', type=int)
            username = request.args.get('username')
            action = request.args.get('action')
            entity_type = request.args.get('entity_type')
            entity_id = request.args.get('entity_id')
            source_system = request.args.get('source_system')
            batch_number = request.args.get('batch_number')
            order_number = request.args.get('order_number')
            search_text = request.args.get('search_text')
            
            # Date filters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            
            start_date = None
            end_date = None
            
            if start_date_str:
                try:
                    start_date = datetime.fromisoformat(start_date_str)
                except ValueError:
                    return {'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}, 400
            
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str)
                except ValueError:
                    return {'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}, 400
            
            # Pagination
            limit = request.args.get('limit', default=100, type=int)
            offset = request.args.get('offset', default=0, type=int)
            
            # Ordering
            order_by = request.args.get('order_by', default='timestamp')
            order_direction = request.args.get('order_direction', default='desc')
            
            # Perform search
            results = AuditTrailSearchService.search(
                user_id=user_id,
                username=username,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                source_system=source_system,
                batch_number=batch_number,
                order_number=order_number,
                start_date=start_date,
                end_date=end_date,
                search_text=search_text,
                limit=limit,
                offset=offset,
                order_by=order_by,
                order_direction=order_direction
            )
            
            return results, 200
        
        except Exception as e:
            return {'error': str(e)}, 500


class EntityHistoryResource(Resource):
    """Resource for retrieving entity history"""
    
    def get(self, entity_type, entity_id):
        """Get complete history for a specific entity"""
        try:
            limit = request.args.get('limit', default=100, type=int)
            
            history = AuditTrailSearchService.get_entity_history(
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit
            )
            
            return {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'history': history,
                'count': len(history)
            }, 200
        
        except Exception as e:
            return {'error': str(e)}, 500


class UserActivityResource(Resource):
    """Resource for retrieving user activity"""
    
    def get(self, user_id):
        """Get all activity for a specific user"""
        try:
            # Date filters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            limit = request.args.get('limit', default=100, type=int)
            
            start_date = None
            end_date = None
            
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str)
            
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str)
            
            activity = AuditTrailSearchService.get_user_activity(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            return {
                'user_id': user_id,
                'activity': activity,
                'count': len(activity)
            }, 200
        
        except Exception as e:
            return {'error': str(e)}, 500


class AuditTrailStatisticsResource(Resource):
    """Resource for audit trail statistics"""
    
    def get(self):
        """Get audit trail statistics"""
        try:
            # Date filters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            
            start_date = None
            end_date = None
            
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str)
            
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str)
            
            stats = AuditTrailSearchService.get_statistics(
                start_date=start_date,
                end_date=end_date
            )
            
            return stats, 200
        
        except Exception as e:
            return {'error': str(e)}, 500


class AuditTrailVerifyResource(Resource):
    """Resource for verifying audit trail integrity"""
    
    def get(self, audit_id):
        """Verify the integrity of an audit record"""
        try:
            result = AuditTrailService.verify_integrity(audit_id)
            return result, 200
        
        except Exception as e:
            return {'error': str(e)}, 500


class HealthCheckResource(Resource):
    """Health check endpoint"""
    
    def get(self):
        return {
            'status': 'healthy',
            'service': 'EchoTrace',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        }, 200


# Register API resources
api.add_resource(AuditTrailResource, '/api/v1/audit-trail')
api.add_resource(AuditTrailSearchResource, '/api/v1/audit-trail/search')
api.add_resource(EntityHistoryResource, '/api/v1/audit-trail/entity/<string:entity_type>/<string:entity_id>')
api.add_resource(UserActivityResource, '/api/v1/audit-trail/user/<int:user_id>')
api.add_resource(AuditTrailStatisticsResource, '/api/v1/audit-trail/statistics')
api.add_resource(AuditTrailVerifyResource, '/api/v1/audit-trail/verify/<int:audit_id>')
api.add_resource(HealthCheckResource, '/api/v1/health')


@app.route('/')
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        'service': 'EchoTrace - Audit Trail Microservice',
        'version': '1.0.0',
        'description': 'Comprehensive audit trail system for pharmaceutical GxP compliance (FDA 21 CFR Part 11)',
        'endpoints': {
            'POST /api/v1/audit-trail': 'Create audit trail entry',
            'GET /api/v1/audit-trail/search': 'Search audit trail with filters',
            'GET /api/v1/audit-trail/entity/<type>/<id>': 'Get entity history',
            'GET /api/v1/audit-trail/user/<user_id>': 'Get user activity',
            'GET /api/v1/audit-trail/statistics': 'Get audit trail statistics',
            'GET /api/v1/audit-trail/verify/<audit_id>': 'Verify audit record integrity',
            'GET /api/v1/health': 'Health check'
        },
        'features': [
            'ALCOA+ compliant audit trails',
            'Blockchain-style integrity verification',
            'Advanced search and filtering',
            'Entity history tracking',
            'User activity monitoring',
            'Statistical analysis',
            'Immutable audit logs'
        ]
    })


if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run application
    app.run(host='0.0.0.0', port=5004, debug=True)
