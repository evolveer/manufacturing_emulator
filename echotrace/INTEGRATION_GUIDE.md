# EchoTrace Integration Guide

## Overview

This guide explains how to integrate EchoTrace audit trail logging into existing services (ERP, MES, PCS).

## Integration Methods

### Method 1: Direct Function Calls

Add audit logging directly in service functions:

```python
from echotrace.integration import log_audit_trail, AuditAction, EntityType

def create_order(user_id, username, order_data):
    # Create order logic
    order = Order(**order_data)
    db.session.add(order)
    db.session.commit()
    
    # Log audit trail
    log_audit_trail(
        user_id=user_id,
        username=username,
        action=AuditAction.CREATE,
        entity_type=EntityType.ORDER,
        entity_id=str(order.id),
        source_system='ERP',
        entity_name=order.order_number,
        new_value={'order_number': order.order_number, 'customer': order.customer}
    )
    
    return order
```

### Method 2: Decorator-Based Logging

Use the `@audit_log` decorator for automatic logging:

```python
from echotrace.integration import audit_log, AuditAction, EntityType

@audit_log(
    action=AuditAction.UPDATE,
    entity_type=EntityType.ORDER,
    source_system='ERP',
    get_entity_id=lambda args, kwargs, result: kwargs.get('order_id'),
    get_old_value=lambda args, kwargs, result: result.get('old_value'),
    get_new_value=lambda args, kwargs, result: result.get('new_value')
)
def update_order_status(user_id, username, order_id, new_status):
    # Update logic
    order = Order.query.get(order_id)
    old_status = order.status
    order.status = new_status
    db.session.commit()
    
    return {
        'order_id': order_id,
        'old_value': {'status': old_status},
        'new_value': {'status': new_status}
    }
```

## Integration Points by Service

### ERP Service

Key operations to audit:
- Order creation/update/deletion
- Material creation/update
- Product creation/update
- Production plan creation/update
- Shipment status changes
- Stock adjustments

### MES Service

Key operations to audit:
- Work order creation/start/complete
- Batch execution steps
- Material consumption
- Equipment assignment
- Quality checks

### PCS Service

Key operations to audit:
- Alarm acknowledgment/resolution
- Machine start/stop
- Parameter changes
- Error conditions

## Example: ERP Order Creation with Audit

```python
# In erp/services.py

from echotrace.integration import log_audit_trail, AuditAction, EntityType

def create_sales_order(user_id, username, customer, product_id, quantity, delivery_date):
    """Create a new sales order with audit logging"""
    
    # Create order
    order = Order(
        order_number=generate_order_number(),
        customer=customer,
        product_id=product_id,
        quantity=quantity,
        delivery_date=delivery_date,
        status='pending'
    )
    
    db.session.add(order)
    db.session.commit()
    
    # Log audit trail
    log_audit_trail(
        user_id=user_id,
        username=username,
        action=AuditAction.CREATE,
        entity_type=EntityType.ORDER,
        entity_id=str(order.id),
        source_system='ERP',
        entity_name=order.order_number,
        new_value={
            'order_number': order.order_number,
            'customer': customer,
            'product_id': product_id,
            'quantity': quantity,
            'delivery_date': delivery_date.isoformat(),
            'status': 'pending'
        }
    )
    
    return order
```

## Example: Shipment Status Update with Audit

```python
# In erp/shipping_services.py

from echotrace.integration import log_audit_trail, AuditAction, EntityType

def update_shipment_status(user_id, username, shipment_id, new_status, reason=None):
    """Update shipment status with audit logging"""
    
    shipment = Shipment.query.get(shipment_id)
    old_status = shipment.status
    
    # Update status
    shipment.status = new_status
    shipment.updated_at = datetime.utcnow()
    
    # Set status-specific timestamps
    if new_status == 'packed':
        shipment.packed_date = datetime.utcnow()
    elif new_status == 'shipped':
        shipment.shipped_date = datetime.utcnow()
        # Deduct inventory
        deduct_inventory(shipment.order_id, shipment.quantity)
    elif new_status == 'delivered':
        shipment.delivered_date = datetime.utcnow()
    
    db.session.commit()
    
    # Log audit trail
    log_audit_trail(
        user_id=user_id,
        username=username,
        action=AuditAction.UPDATE,
        entity_type=EntityType.SHIPMENT,
        entity_id=str(shipment.id),
        source_system='ERP',
        entity_name=shipment.shipment_number,
        old_value={'status': old_status},
        new_value={'status': new_status},
        changes={'status': {'from': old_status, 'to': new_status}},
        reason=reason,
        order_number=shipment.order.order_number if shipment.order else None
    )
    
    return shipment
```

## Example: PCS Alarm Acknowledgment with Audit

```python
# In pcs/services.py

from echotrace.integration import log_audit_trail, AuditAction, EntityType

def acknowledge_alarm(user_id, username, alarm_id, reason):
    """Acknowledge alarm with audit logging"""
    
    alarm = Alarm.query.get(alarm_id)
    
    # Update alarm
    alarm.status = 'acknowledged'
    alarm.acknowledged_by = user_id
    alarm.acknowledged_at = datetime.utcnow()
    alarm.acknowledgment_reason = reason
    
    db.session.commit()
    
    # Log audit trail
    log_audit_trail(
        user_id=user_id,
        username=username,
        action=AuditAction.APPROVE,  # Acknowledgment is a form of approval
        entity_type=EntityType.ALARM,
        entity_id=str(alarm.id),
        source_system='PCS',
        entity_name=f"Alarm {alarm.id} - {alarm.alarm_type}",
        old_value={'status': 'active'},
        new_value={'status': 'acknowledged'},
        reason=reason
    )
    
    return alarm
```

## Testing Integration

Test audit logging with curl:

```bash
# Create an audit trail entry
curl -X POST http://localhost:5004/api/v1/audit-trail \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "username": "admin",
    "action": "CREATE",
    "entity_type": "Order",
    "entity_id": "123",
    "source_system": "ERP",
    "entity_name": "ORD-001",
    "new_value": {"order_number": "ORD-001", "customer": "Test Customer"}
  }'

# Search audit trails
curl "http://localhost:5004/api/v1/audit-trail/search?entity_type=Order&limit=10"

# Get entity history
curl "http://localhost:5004/api/v1/audit-trail/entity/Order/123"

# Get user activity
curl "http://localhost:5004/api/v1/audit-trail/user/1"

# Get statistics
curl "http://localhost:5004/api/v1/audit-trail/statistics"
```

## Best Practices

1. **Always log critical operations**: CREATE, UPDATE, DELETE, APPROVE, REJECT
2. **Include reason for changes**: Especially for GxP-critical operations
3. **Capture before/after values**: For UPDATE operations
4. **Use consistent entity types**: Use EntityType constants
5. **Use consistent action types**: Use AuditAction constants
6. **Include traceability links**: batch_number, order_number for manufacturing traceability
7. **Handle errors gracefully**: Audit logging should not break main operations

## Compliance Considerations

EchoTrace implements FDA 21 CFR Part 11 requirements:

- **Attributable**: user_id and username captured
- **Legible**: Clear action descriptions
- **Contemporaneous**: Timestamp at time of action
- **Original**: Immutable records with hash verification
- **Accurate**: Validated data with before/after values
- **Complete**: All required fields captured
- **Consistent**: Standardized format
- **Enduring**: Permanent storage with archival
- **Available**: Searchable and reportable

## Next Steps

1. Review existing service functions
2. Identify critical operations requiring audit trails
3. Add audit logging using direct calls or decorators
4. Test audit trail creation and search
5. Verify audit trail integrity
6. Generate audit reports for regulatory inspections
