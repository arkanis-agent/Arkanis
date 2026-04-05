import requests
import subprocess
import logging
import time
from datetime import datetime
from urllib.parse import urlparse

class SecurityAuditor:
    def __init__(self):
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'vulnerabilities': []
        }
        logging.basicConfig(filename='security_audit.log', level=logging.INFO)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'ArkanisV3-SecurityScanner/1.0'})

    def _validate_url(self, url):
        """Valida e sanitiza URLs"""
        if not isinstance(url, str):
            return False
            
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False
                
            # Sanitização básica
            if '\n' in url or '\r' in url or ' ' in url:
                return False
                
            return True
        except ValueError:
            return False

    def _make_request(self, url, max_retries=3):
        """Faz requisições com retry e backoff"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=5,
                    verify=True,
                    allow_redirects=False
                )
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = (2 ** attempt) * 0.5
                time.sleep(wait_time)
        return None

    def check_security_headers(self, base_url):
        """Verifica headers de segurança importantes"""
        if not self._validate_url(base_url):
            logging.error('URL inválida fornecida: %s', base_url)
            return

        try:
            response = self._make_request(base_url)
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'Content-Security-Policy': None,
                'Strict-Transport-Security': None
            }

            missing_headers = []
            for header, expected_value in security_headers.items():
                if header not in response.headers:
                    missing_headers.append(header)
                elif expected_value and response.headers[header] != expected_value:
                    self.report['vulnerabilities'].append({
                        'type': 'insecure_header',
                        'header': header,
                        'value': response.headers[header],
                        'expected': expected_value,
                        'severity': 'medium'
                    })

            if missing_headers:
                self.report['vulnerabilities'].append({
                    'type': 'missing_security_headers',
                    'headers': missing_headers,
                    'severity': 'medium'
                })

        except requests.RequestException as e:
            logging.warning('Erro ao verificar headers de segurança: %s', str(e))

    def check_exposed_endpoints(self, base_url):
        """Verifica endpoints comuns que não deveriam estar expostos"""
        if not self._validate_url(base_url):
            logging.error('URL inválida fornecida: %s', base_url)
            return

        sensitive_endpoints = ['/admin', '/console', '/backup']
        for endpoint in sensitive_endpoints:
            try:
                response = self._make_request(f"{base_url}{endpoint}")
                if response.status_code < 400:
                    self.report['vulnerabilities'].append({
                        'type': 'exposed_endpoint',
                        'endpoint': endpoint,
                        'severity': 'high',
                        'ssl_verified': response.url.startswith('https://'),
                        'status_code': response.status_code
                    })
            except requests.exceptions.SSLError:
                self.report['vulnerabilities'].append({
                    'type': 'ssl_error',
                    'endpoint': endpoint,
                    'severity': 'critical'
                })
            except requests.RequestException as e:
                logging.warning('Erro ao verificar endpoint %s: %s', endpoint, str(e))
                continue

    def check_dependencies(self):
        """Verifica dependências vulneráveis usando pip-audit"""
        try:
            result = subprocess.run(
                ['pip-audit', '--format', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Processa saída JSON diretamente
            try:
                audit_data = json.loads(result.stdout)
                if audit_data.get('vulnerabilities', []):
                    self.report['vulnerabilities'].append({
                        'type': 'vulnerable_dependencies',
                        'count': len(audit_data['vulnerabilities']),
                        'severity': 'critical',
                        'details': audit_data
                    })
            except json.JSONDecodeError:
                logging.error('Formato inválido do pip-audit')
                
        except subprocess.CalledProcessError as e:
            logging.error('Erro ao executar pip-audit: %s', str(e))
            self.report['vulnerabilities'].append({
                'type': 'pip_audit_error',
                'details': str(e),
                'severity': 'high'
            })
        except FileNotFoundError:
            logging.warning('pip-audit não encontrado')
            self.report['vulnerabilities'].append({
                'type': 'missing_tool',
                'tool': 'pip-audit',
                'severity': 'medium'
            })

    def generate_report(self):
        """Gera relatório completo de segurança"""
        logging.info('Relatório de segurança gerado')
        # Ordena vulnerabilidades por severidade
        self.report['vulnerabilities'].sort(
            key=lambda x: ['low', 'medium', 'high', 'critical'].index(x['severity']),
            reverse=True
        )
        return self.report