import requests
import subprocess
from datetime import datetime

class SecurityAuditor:
    def __init__(self):
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'vulnerabilities': []
        }

    def check_exposed_endpoints(self, base_url):
        """Verifica endpoints comuns que não deveriam estar expostos"""
        sensitive_endpoints = ['/admin', '/console', '/backup']
        for endpoint in sensitive_endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code < 400:
                    self.report['vulnerabilities'].append({
                        'type': 'exposed_endpoint',
                        'endpoint': endpoint,
                        'severity': 'high'
                    })
            except requests.RequestException:
                continue

    def check_dependencies(self):
        """Verifica dependências vulneráveis usando pip-audit"""
        try:
            result = subprocess.run(['pip-audit'], capture_output=True, text=True)
            if result.returncode != 0:
                self.report['vulnerabilities'].append({
                    'type': 'vulnerable_dependencies',
                    'details': result.stdout,
                    'severity': 'critical'
                })
        except FileNotFoundError:
            self.report['vulnerabilities'].append({
                'type': 'missing_tool',
                'tool': 'pip-audit',
                'severity': 'medium'
            })

    def generate_report(self):
        """Gera relatório completo de segurança"""
        return self.report

# Exemplo de uso:
# auditor = SecurityAuditor()
# auditor.check_exposed_endpoints('http://localhost:8000')
# auditor.check_dependencies()
# print(auditor.generate_report())