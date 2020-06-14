from extra_metrics.main import serve_and_process

def install_prom_hook():
    print("I would install the prom hook")

def install_dashboards_into_grafana_provisioning():
    print("I would copy the dashboard data files into grafana provisioning")

def install_into_environment():
    install_prom_hook()
    install_dashboards_into_grafana_provisioning()
    
def run_test_server():
    serve_and_process()