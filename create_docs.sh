mkdir -p docs
echo "# API Documentation

This document provides detailed information about the APIs available in the Manufacturing Emulator System.

## ERP API

Base URL: `http://localhost:5001/api/v1`

### Materials

- `GET /materials` - Get all materials
- `GET /materials/{id}` - Get material by ID
- `POST /materials` - Create a new material
- `PUT /materials/{id}` - Update a material
- `DELETE /materials/{id}` - Delete a material

### Products

- `GET /products` - Get all products
- `GET /products/{id}` - Get product by ID
- `POST /products` - Create a new product
- `PUT /products/{id}` - Update a product
- `DELETE /products/{id}` - Delete a product

### BOMs (Bill of Materials)

- `GET /boms` - Get all BOMs
- `GET /boms/{id}` - Get BOM by ID
- `GET /boms/product/{product_id}` - Get BOM by product ID
- `POST /boms` - Create a new BOM
- `PUT /boms/{id}` - Update a BOM
- `DELETE /boms/{id}` - Delete a BOM

### Production Plans

- `GET /production-plans` - Get all production plans
- `GET /production-plans/{id}` - Get production plan by ID
- `POST /production-plans` - Create a new production plan
- `PUT /production-plans/{id}` - Update a production plan
- `DELETE /production-plans/{id}` - Delete a production plan
- `PUT /production-plans/{id}/update-counts` - Update production counts for a plan

### Orders

- `GET /orders` - Get all orders
- `GET /orders/{id}` - Get order by ID
- `POST /orders` - Create a new order
- `PUT /orders/{id}` - Update an order
- `DELETE /orders/{id}` - Delete an order
- `PUT /orders/{id}/status` - Update order status

## MES API

Base URL: `http://localhost:5002/api/v1`

### Work Orders

- `GET /work-orders` - Get all work orders
- `GET /work-orders/{id}` - Get work order by ID
- `GET /work-orders/number/{number}` - Get work order by number
- `GET /work-orders/active` - Get active work orders
- `POST /work-orders` - Create a new work order
- `PUT /work-orders/{id}` - Update a work order
- `DELETE /work-orders/{id}` - Delete a work order
- `PUT /work-orders/{id}/status` - Update work order status
- `POST /production-plans/{id}/create-work-orders` - Create work orders from production plan

### Machines

- `GET /machines` - Get all machines
- `GET /machines/{id}` - Get machine by ID
- `GET /machines/code/{code}` - Get machine by code
- `GET /machines/available` - Get available machines
- `GET /machines/type/{type}` - Get machines by type
- `POST /machines` - Create a new machine
- `PUT /machines/{id}` - Update a machine
- `DELETE /machines/{id}` - Delete a machine
- `PUT /machines/{id}/status` - Update machine status

### Production Schedule

- `GET /schedule` - Get all schedule entries
- `GET /schedule/{id}` - Get schedule entry by ID
- `GET /machines/{id}/schedule` - Get schedule for a machine
- `GET /work-orders/{id}/schedule` - Get schedule for a work order
- `POST /schedule` - Create a new schedule entry
- `PUT /schedule/{id}` - Update a schedule entry
- `DELETE /schedule/{id}` - Delete a schedule entry
- `GET /machines/{id}/availability` - Check machine availability
- `POST /work-orders/{id}/auto-schedule` - Auto-schedule a work order

### Quality Control

- `GET /quality-checks` - Get all quality checks
- `GET /quality-checks/{id}` - Get quality check by ID
- `GET /work-orders/{id}/quality-checks` - Get quality checks for a work order
- `GET /work-orders/{id}/quality-summary` - Get quality summary for a work order
- `POST /quality-checks` - Create a new quality check
- `PUT /quality-checks/{id}` - Update a quality check
- `DELETE /quality-checks/{id}` - Delete a quality check

### Material Tracking

- `GET /material-transactions` - Get all material transactions
- `GET /material-transactions/{id}` - Get material transaction by ID
- `GET /work-orders/{id}/material-transactions` - Get material transactions for a work order
- `GET /materials/{id}/transactions` - Get transactions for a material
- `POST /material-transactions` - Create a new material transaction
- `PUT /material-transactions/{id}` - Update a material transaction
- `DELETE /material-transactions/{id}` - Delete a material transaction
- `POST /work-orders/{id}/allocate-materials` - Allocate materials for a work order
- `POST /work-orders/{id}/consume-materials` - Consume materials for a work order

### Production Counts

- `GET /production-counts` - Get all production counts
- `GET /production-counts/{id}` - Get production count by ID
- `GET /work-orders/{id}/production-counts` - Get production counts for a work order
- `GET /work-orders/{id}/production-summary` - Get production summary for a work order
- `POST /production-counts` - Create a new production count
- `PUT /production-counts/{id}` - Update a production count
- `DELETE /production-counts/{id}` - Delete a production count
- `POST /work-orders/{id}/increment-count` - Increment production count for a work order

### Downtime

- `GET /downtimes` - Get all downtimes
- `GET /downtimes/{id}` - Get downtime by ID
- `GET /machines/{id}/downtimes` - Get downtimes for a machine
- `GET /downtimes/active` - Get active downtimes
- `POST /downtimes` - Create a new downtime
- `PUT /downtimes/{id}` - Update a downtime
- `DELETE /downtimes/{id}` - Delete a downtime
- `PUT /downtimes/{id}/end` - End a downtime event

## PCS API

Base URL: `http://localhost:5003/api/v1`

### Machine Parameters

- `GET /parameters` - Get all machine parameters
- `GET /machines/{id}/parameters` - Get parameters for a machine
- `GET /machines/{id}/parameters/{name}` - Get specific parameter for a machine
- `PUT /machines/{id}/parameters/{name}` - Update a machine parameter

### Sensor Data

- `GET /machines/{id}/sensors` - Get latest sensor data for a machine
- `GET /machines/{id}/sensors/{name}/range` - Get sensor data within a time range
- `GET /machines/{id}/sensors/{name}/statistics` - Get statistics for sensor data

### Alarms

- `GET /alarms` - Get all alarms
- `GET /alarms/{id}` - Get alarm by ID
- `GET /machines/{id}/alarms` - Get alarms for a machine
- `POST /alarms` - Create a new alarm
- `PUT /alarms/{id}/acknowledge` - Acknowledge an alarm
- `PUT /alarms/{id}/resolve` - Resolve an alarm

### Machine States

- `GET /machines/{id}/state` - Get current state for a machine
- `GET /machines/{id}/states` - Get state history for a machine
- `GET /states/{id}` - Get state by ID
- `GET /machines/{id}/uptime` - Calculate machine uptime

### Cycle Data

- `GET /machines/{id}/cycles` - Get cycles for a machine
- `GET /work-orders/{id}/cycles` - Get cycles for a work order
- `GET /cycles/{id}` - Get cycle by ID
- `GET /machines/{id}/cycle-statistics` - Get cycle statistics for a machine

### Machine Commands

- `GET /machines/{id}/commands` - Get commands for a machine
- `GET /commands/{id}` - Get command by ID
- `POST /machines/{id}/commands` - Create a new command

### Machine Management

- `GET /machines/{id}/status` - Get current status of a machine
- `GET /machines/status` - Get status of all machines
- `POST /machines` - Create a new machine
- `POST /machines/{id}/start` - Start a machine
- `POST /machines/{id}/stop` - Stop a machine
- `POST /machines/{id}/set-parameter` - Set a machine parameter

## Interface API

Base URL: `http://localhost:5000/api`

### System Status

- `GET /status` - Get status of all systems

### Dashboard Data

- `GET /dashboard/summary` - Get summary data for dashboard
- `GET /dashboard/production` - Get production data for dashboard
- `GET /dashboard/inventory` - Get inventory data for dashboard
- `GET /dashboard/quality` - Get quality data for dashboard

### Data Synchronization

- `POST /sync/start` - Start data synchronization
- `POST /sync/stop` - Stop data synchronization
- `GET /sync/status` - Get data synchronization status

### System Control

- `POST /system/start` - Start all system components
- `POST /system/stop` - Stop all system components

### Proxy APIs

The interface also provides proxy endpoints to access the individual system APIs:

- `GET/POST/PUT/DELETE /api/erp/*` - Proxy to ERP API
- `GET/POST/PUT/DELETE /api/mes/*` - Proxy to MES API
- `GET/POST/PUT/DELETE /api/pcs/*` - Proxy to PCS API

## API Authentication

The emulator APIs do not require authentication as they are intended for testing purposes only. In a production environment, proper authentication and authorization mechanisms should be implemented.

## Error Handling

All APIs follow standard HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a JSON object with an error message:

```json
{
  "error": "Error message"
}
```

## Data Formats

All APIs accept and return JSON data. Dates are formatted as ISO 8601 strings (e.g., `2025-04-24T10:30:00Z`).

## Pagination

List endpoints support pagination through query parameters:

- `limit`: Maximum number of items to return (default: 100)
- `offset`: Number of items to skip (default: 0)

Example: `GET /api/v1/materials?limit=10&offset=20`

## Filtering

Many list endpoints support filtering through query parameters. Refer to the specific endpoint documentation for available filters.

Example: `GET /api/v1/work-orders?status=active`

## Sorting

List endpoints support sorting through the `sort` query parameter:

- `sort=field`: Sort by field in ascending order
- `sort=-field`: Sort by field in descending order

Example: `GET /api/v1/production-plans?sort=-due_date`

## Rate Limiting

The emulator APIs do not implement rate limiting. In a production environment, appropriate rate limiting should be configured.
" > docs/api_documentation.md

echo "# Developer Guide

This guide provides information for developers who want to extend or modify the Manufacturing Emulator System.

## Project Structure

The project is organized into the following directories:

- **erp/**: ERP emulator component
- **mes/**: MES emulator component
- **pcs/**: PCS emulator component
- **common/**: Shared code and interface
- **database/**: Database initialization and utilities
- **docs/**: Documentation
- **tests/**: Test scripts

Each component follows a similar structure:

- **models.py**: Data models using SQLAlchemy ORM
- **database.py**: Database connection and session management
- **services.py**: Business logic services
- **api.py**: REST API endpoints using Flask
- **main.py**: Entry point for the component

## Technology Stack

- **Backend**: Python with Flask for REST APIs
- **Database**: SQLite (can be replaced with other databases)
- **ORM**: SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript with Bootstrap
- **API**: RESTful JSON APIs

## Adding New Features

### Adding a New Machine Type

To add a new machine type to the PCS emulator:

1. Extend the machine simulator in **pcs/machine_simulator.py**:
   ```python
   class NewMachineType(InjectionMoldingMachine):
       # Override methods to implement different behavior
       def _run_cycle(self):
           # Implement cycle behavior for the new machine type
           pass
   ```

2. Update the machine manager to support the new machine type:
   ```python
   def create_machine(self, machine_id, machine_type='injection_molding'):
       if machine_type == 'injection_molding':
           machine = InjectionMoldingMachine(machine_id, self.config)
       elif machine_type == 'new_machine_type':
           machine = NewMachineType(machine_id, self.config)
       else:
           raise ValueError(f'Unknown machine type: {machine_type}')
       
       self.machines[machine_id] = machine
       return True
   ```

3. Update the API to support the new machine type:
   ```python
   @app.route('/api/v1/machines/new-type', methods=['POST'])
   def create_new_machine_type():
       data = request.get_json()
       machine_id = data.get('machine_id')
       result = MachineService.create_machine(machine_id, 'new_machine_type')
       return jsonify({'success': result})
   ```

### Adding New ERP Functionality

To add new ERP functionality:

1. Define new data models in **erp/models.py**:
   ```python
   class NewEntity(Base):
       __tablename__ = 'new_entities'
       
       id = Column(Integer, primary_key=True)
       name = Column(String, nullable=False)
       # Add more fields as needed
   ```

2. Implement business logic in **erp/services.py**:
   ```python
   class NewEntityService:
       @staticmethod
       def get_all_entities():
           # Implementation
           pass
       
       @staticmethod
       def create_entity(data):
           # Implementation
           pass
       
       # Add more methods as needed
   ```

3. Add API endpoints in **erp/api.py**:
   ```python
   class NewEntityListAPI(Resource):
       def get(self):
           # Implementation
           pass
       
       def post(self):
           # Implementation
           pass
   
   class NewEntityAPI(Resource):
       def get(self, entity_id):
           # Implementation
           pass
       
       def put(self, entity_id):
           # Implementation
           pass
       
       def delete(self, entity_id):
           # Implementation
           pass
   
   # Register resources
   api.add_resource(NewEntityListAPI, f'{API_PREFIX}/new-entities')
   api.add_resource(NewEntityAPI, f'{API_PREFIX}/new-entities/<int:entity_id>')
   ```

### Adding New MES Functionality

Follow a similar approach as for ERP to add new MES functionality:

1. Define new data models in **mes/models.py**
2. Implement business logic in **mes/services.py**
3. Add API endpoints in **mes/api.py**

### Adding New Data Synchronization Paths

To add new data synchronization paths:

1. Add new synchronization methods in **common/data_sync.py**:
   ```python
   def _sync_new_entity(self):
       """Synchronize new entity between systems"""
       try:
           # Implementation
           pass
       except Exception as e:
           logger.error(f'Error synchronizing new entity: {str(e)}')
           raise
   ```

2. Update the synchronization loop to call the new method:
   ```python
   def _sync_erp_to_mes(self):
       """Synchronize data from ERP to MES"""
       logger.info('Synchronizing data from ERP to MES...')
       
       try:
           # Existing synchronization
           self._sync_production_plans()
           self._sync_materials()
           
           # New synchronization
           self._sync_new_entity()
           
           logger.info('ERP to MES synchronization completed')
       
       except Exception as e:
           logger.error(f'Error synchronizing ERP to MES: {str(e)}')
           raise
   ```

### Creating Custom Dashboards

To create a custom dashboard:

1. Create a new HTML template in **common/templates/**:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>Custom Dashboard</title>
       <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css' rel='stylesheet'>
       <link rel='stylesheet' href='/static/css/styles.css'>
   </head>
   <body>
       <!-- Dashboard content -->
   </body>
   </html>
   ```

2. Add a route in **common/interface.py**:
   ```python
   @app.route('/custom-dashboard')
   def custom_dashboard():
       return render_template('custom_dashboard.html')
   ```

3. Add API endpoints to provide data for the dashboard:
   ```python
   @app.route('/api/custom-dashboard/data')
   def custom_dashboard_data():
       # Fetch and return data
       pass
   ```

4. Add JavaScript to fetch and display data:
   ```javascript
   fetch('/api/custom-dashboard/data')
       .then(response => response.json())
       .then(data => {
           // Update dashboard with data
       });
   ```

## Database Schema

The system uses SQLAlchemy ORM to define the database schema. Each component has its own set of tables:

### ERP Tables

- **materials**: Raw materials inventory
- **products**: Finished products
- **boms**: Bill of materials
- **bom_items**: Items in a bill of materials
- **production_plans**: Production plans
- **orders**: Customer orders
- **order_items**: Items in an order
- **material_transactions**: Material inventory transactions

### MES Tables

- **work_orders**: Manufacturing work orders
- **machines**: Production machines
- **schedule_entries**: Production schedule
- **quality_checks**: Quality control checks
- **material_transactions**: Material usage tracking
- **production_counts**: Production output counts
- **downtimes**: Machine downtime events

### PCS Tables

- **machine_parameters**: Machine control parameters
- **sensor_data**: Sensor measurements
- **alarms**: Machine alarms and warnings
- **machine_states**: Machine operational states
- **cycle_data**: Production cycle data
- **machine_commands**: Commands sent to machines

## Testing

The system includes integration tests in the **tests/** directory. To add new tests:

1. Add test functions to **tests/integration_test.py**:
   ```python
   def test_new_functionality():
       """Test new functionality"""
       try:
           # Test implementation
           return True
       except Exception as e:
           logger.error(f'Error testing new functionality: {str(e)}')
           return False
   ```

2. Add the test to the test runner:
   ```python
   def run_all_tests():
       """Run all tests"""
       # Existing tests
       run_test('System Availability', test_system_availability)
       
       # New test
       run_test('New Functionality', test_new_functionality)
   ```

## Performance Considerations

- The system is designed for testing and emulation, not for production use
- For large-scale testing, consider using a more robust database like PostgreSQL
- The data synchronization module uses separate threads for each synchronization path
- Sensor data and cycle data can grow quickly, consider implementing data retention policies

## Security Considerations

- The system does not implement authentication or authorization
- For production use, add proper authentication and authorization mechanisms
- Implement HTTPS for all API endpoints
- Add input validation and sanitization for all API endpoints

## Logging

The system uses Python's logging module. Each component has its own log file:

- **erp/erp.log**: ERP emulator logs
- **mes/mes.log**: MES emulator logs
- **pcs/pcs.log**: PCS emulator logs
- **interface.log**: Interface logs
- **sync.log**: Data synchronization logs
- **test_results.log**: Test logs

To modify logging configuration, update the logging setup in each component's main.py file.

## Configuration

System configuration is stored in **config.yaml**. The configuration includes:

- Database connections
- API ports and hosts
- Synchronization intervals
- Machine parameters

To add new configuration options:

1. Add the option to **config.yaml**
2. Update the code to use the new option

## Deployment

For production deployment:

1. Use a production-grade WSGI server like Gunicorn
2. Set up a reverse proxy with Nginx
3. Use a production database like PostgreSQL
4. Implement proper authentication and authorization
5. Set up HTTPS with Let's Encrypt
6. Configure proper logging and monitoring

Example Gunicorn configuration:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 common.interface:app
```

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name manufacturing-emulator.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Contributing

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass
6. Submit a pull request

Follow the existing code style and structure when making changes.

## Support

For support and questions, please open an issue in the repository or contact the maintainers.
" > docs/developer_guide.md

echo "# Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using the Manufacturing Emulator System.

## System Startup Issues

### Issue: One or more components fail to start

**Symptoms:**
- Error messages in the console when running start.sh
- Missing components in the system status dashboard

**Possible causes and solutions:**

1. **Port already in use**
   - Check if another process is using the required ports (5000, 5001, 5002, 5003)
   - Run `lsof -i :PORT` to see if a process is using the port
   - Kill the process or change the port in config.yaml

2. **Python environment issues**
   - Ensure the virtual environment is activated
   - Verify all dependencies are installed: `pip install -r requirements.txt`

3. **Permission issues**
   - Ensure start.sh and stop.sh are executable: `chmod +x start.sh stop.sh`
   - Check file permissions for the Python files

4. **Database initialization**
   - Ensure the database was initialized: `python database/init_db.py`
   - Check for database errors in the component logs

### Issue: System starts but components show as offline

**Symptoms:**
- All components start without errors
- System status dashboard shows components as offline

**Possible causes and solutions:**

1. **Network configuration**
   - Verify the host settings in config.yaml
   - Ensure localhost/127.0.0.1 is used for local testing

2. **Firewall issues**
   - Check if a firewall is blocking the ports
   - Allow the required ports in your firewall settings

3. **Slow startup**
   - Some components may take time to initialize
   - Wait a few moments and refresh the dashboard

## Data Synchronization Issues

### Issue: Data not synchronizing between systems

**Symptoms:**
- Changes in one system don't appear in other systems
- Synchronization status shows as online but data isn't updating

**Possible causes and solutions:**

1. **Synchronization not started**
   - Verify synchronization is running: check the sync status in the dashboard
   - Start synchronization if needed: click 'Start System' or use the API

2. **API errors**
   - Check the sync.log file for API error messages
   - Verify all components are running and accessible

3. **Data format issues**
   - Check for data format mismatches between systems
   - Verify the data being synchronized meets the expected format

4. **Synchronization intervals**
   - The default intervals may be too long for your testing
   - Adjust the intervals in config.yaml

## Database Issues

### Issue: Database errors

**Symptoms:**
- Error messages related to the database in component logs
- Components fail to start or operations fail

**Possible causes and solutions:**

1. **Database not initialized**
   - Run `python database/init_db.py` to initialize the database

2. **Database corruption**
   - Delete the database files and reinitialize:
     ```
     rm -f erp/erp.db mes/mes.db pcs/pcs.db
     python database/init_db.py
     ```

3. **SQLite limitations**
   - SQLite has limitations for concurrent access
   - For heavy testing, consider using PostgreSQL

## API Issues

### Issue: API requests failing

**Symptoms:**
- Error responses from API endpoints
- Frontend features not working

**Possible causes and solutions:**

1. **Incorrect API URLs**
   - Verify the API URLs being used
   - Check for typos in endpoint paths

2. **Missing or invalid parameters**
   - Check the API documentation for required parameters
   - Ensure parameters are in the correct format

3. **Component not running**
   - Verify the component handling the API is running
   - Check component logs for errors

4. **CORS issues**
   - If accessing APIs from a different domain, CORS may block requests
   - Configure CORS in the API components if needed

## Machine Simulation Issues

### Issue: Machines not running or cycling

**Symptoms:**
- Machines show as idle in the dashboard
- No cycle data being generated

**Possible causes and solutions:**

1. **No work orders assigned**
   - Create and schedule work orders for the machines
   - Verify work orders are properly assigned to machines

2. **Machine not started**
   - Use the API to start the machine
   - Check if the machine was started with the correct work order

3. **Simulation errors**
   - Check the PCS logs for simulation errors
   - Verify machine parameters are within valid ranges

4. **Threading issues**
   - The simulation runs in a separate thread
   - Check for thread-related errors in the PCS logs

## Interface Issues

### Issue: Dashboard not updating

**Symptoms:**
- Dashboard shows stale data
- Real-time updates not appearing

**Possible causes and solutions:**

1. **JavaScript errors**
   - Check the browser console for JavaScript errors
   - Verify the browser supports all features used

2. **API connectivity**
   - Ensure the browser can connect to all API endpoints
   - Check for network errors in the browser console

3. **Update intervals**
   - The dashboard updates at fixed intervals
   - Adjust the update intervals in the JavaScript code if needed

4. **Browser caching**
   - Clear the browser cache
   - Use incognito/private browsing mode for testing

## Performance Issues

### Issue: System running slowly

**Symptoms:**
- Operations take a long time to complete
- Dashboard updates are delayed

**Possible causes and solutions:**

1. **Resource limitations**
   - Check CPU and memory usage
   - Close unnecessary applications

2. **Database growth**
   - Large amounts of sensor and cycle data can slow the system
   - Implement data retention policies or periodically reset the database

3. **Logging overhead**
   - Excessive logging can impact performance
   - Adjust logging levels in the component configurations

4. **Synchronization frequency**
   - High synchronization frequency can cause performance issues
   - Adjust synchronization intervals in config.yaml

## Common Error Messages

### "No such file or directory"

This usually indicates a missing file or incorrect path. Check:
- File paths in your code
- Working directory when running commands
- File permissions

### "Address already in use"

This indicates a port conflict. Check:
- If another instance of the system is running
- Other applications using the same ports
- Use `lsof -i :PORT` to identify the process using the port

### "Database is locked"

This indicates concurrent access issues with SQLite. Check:
- If multiple processes are accessing the same database
- If a previous process didn't close the database properly
- Consider using a more robust database for heavy concurrent access

### "Connection refused"

This indicates a component is not running or not accessible. Check:
- If the component is started
- The host and port configuration
- Network/firewall settings

## Resetting the System

If you encounter persistent issues, you can reset the system:

1. Stop all components:
   ```
   ./stop.sh
   ```

2. Delete the database files:
   ```
   rm -f erp/erp.db mes/mes.db pcs/pcs.db
   ```

3. Reinitialize the database:
   ```
   python database/init_db.py
   ```

4. Restart the system:
   ```
   ./start.sh
   ```

## Getting Help

If you continue to experience issues:

1. Check the log files for detailed error messages
2. Review the documentation for the specific component
3. Search for similar issues in the project repository
4. Contact the maintainers with detailed information about the issue
" > docs/troubleshooting.md

mkdir -p docs/images
echo "Creating architecture diagram..."
