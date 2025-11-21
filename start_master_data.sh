
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
cd erp
python3 master_data_server.py
