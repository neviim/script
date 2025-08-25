# Versão em python do script para retornar quantos dias faltão 
# para vencer o contrado do dominio consultado

## Versão em python
```python
sudo mkdir -p /scripts
sudo nano /scripts/check_domain_expiry.py

sudo chmod +x /scripts/check_domain_expiry.py
```

### Instalar dependencias, linux Debian/Ubuntu
```shell
# Debian/Ubuntu
sudo apt-get install -y whois
pip install tqdm

# CentOS/RHEL/AlmaLinux
sudo yum install -y whois
# ou
sudo dnf install -y whois
```

### Testes
```shell
/scripts/check_domain_expiry.py google.com
/scripts/check_domain_expiry.py comunidade.cn
/scripts/check_domain_expiry.py zabbix.com.br
```

- Saída esperada: 123 (ou -1 se erro)

### Integra ao Zabbix

```bash
# No arquivo do agente (/etc/zabbix/zabbix_agentd.d/userparameter_domain.conf):
UserParameter=domain.expiry.days[*],/scripts/check_domain_expiry.py "$1"
```

- Teste múltiplos domínios

```bash
python3 check_domain_expiry.py --domains google.com comunidade.cn zabbix.org
```
google.com: 123
comunidade.cn: 45
zabbix.org: 200

- Crie um arquivo com a lista de domínios:

```shell
sudo nano /etc/zabbix/domains.txt
```

```txt
# Lista de domínios para monitorar
google.com
comunidade.cn
vovojosefa.com.br
teste.com.uy
```

````shell
sudo chmod +x /scripts/check_domains_from_file.py
````

- Teste:

```shell
python3 check_domains_from_file.py /etc/zabbix/domains.txt
```

- Saida:

```
google.com: 123
comunidade.cn: 45
vovojosefa.com.br 219
teste.com.uy -1
```

## Integrar com Zabbix (opcional)

Se quiser monitorar um domínio específico do arquivo, use um UserParameter com argumento:

```ini
# Em /etc/zabbix/zabbix_agentd.d/userparameter_domain.conf

# Verifica um domínio específico do arquivo
UserParameter=domain.expiry.fromfile[*],grep -v '^#' /etc/zabbix/domains.txt | grep -i '$1' | head -n1 | xargs /scripts/check_domain_expiry.py

# Ou: executa o script completo e extrai o valor (mais pesado)
UserParameter=domain.expiry.batch,/scripts/check_domains_from_file.py /etc/zabbix/domains.txt
```
Recomendo usar o template por domínio individual (como antes) se quiser alertas específicos. 


### Dica: Automatize com cron (relatório diário)

```shell
sudo crontab -e
```

Adicione

```
0 6 * * * /scripts/check_domains_from_file.py /etc/zabbix/domains.txt > /var/log/domain_expiry_report.txt
```