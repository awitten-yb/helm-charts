

import yaml
import json
import copy
import os
import re
import subprocess

from collections import namedtuple

from kubernetes import client, config
from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api

# helm delete prom-test-shard-0 prom-test-shard-1 prom-test-shard-2 -n test-shard && kubectl delete deployment thanos-querier 
# -n test-shard && kubectl delete configmap thanos-querier-file-sd -n test-shard

CONFIG_MAP_PREFIX = 'thanos-querier-file-sd-'
THANOS_QUERIER_DEPLOYMENT_PREFIX = 'thanos-querier-'
S3_CONFIG_MAP_PREFIX = 's3-config-'

def install_parser(subparsers, subcommand_name):
    parser = subparsers.add_parser(subcommand_name, help='install prometheus helm charts, and start thanos')
    parser.add_argument('--chart', type=str, 
                    help='namespace for helm charts')

extra_scrape_configs = '''extraScrapeConfigs: |
  - job_name: avalanche-hash
    kubernetes_sd_configs:
      - role: pod
    scheme: http
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_avalanche_scrape]
      action: keep
      regex: true
    - source_labels: [__address__]
      modulus:       4    # 4 shards
      target_label:  __tmp_hash
      action:        hashmod
    - source_labels: [__tmp_hash]
      regex:         ^0$  # This is the 1st shard
      action:        keep
      '''


def config_map_file(name, file_name, config_file):
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
        },
        "data": {
            file_name: config_file
        }
    }

def handle_install(args):
    global extra_scrape_configs
    config.load_kube_config()
    shards, ns, chart, release_name_prefix = int(os.environ['PROMETHEUS_SHARDS']), \
         os.environ['PROMETHEUS_NAMESPACE'], args.chart, os.environ['PROMETHEUS_RELEASE_NAME_PREFIX']
    extra_scrape_configs = re.sub('modulus: \s+[0-9]', 'modulus:       ' + str(shards), extra_scrape_configs)
    thanos_query_targets = []
    thanos_sd_file = CONFIG_MAP_PREFIX + release_name_prefix

    for shard in range(shards):
        release_name = '{rn}-shard-{shard}'.format(rn=release_name_prefix, shard=shard)
        config_file_name = release_name + "-config.yaml"
        config_file = open(config_file_name, "w")
        config_values = re.sub('\^[0-9]+\$', '^{shard}$'.format(shard=shard), extra_scrape_configs)
        config_file.write(config_values)
        config_file.close()
        cmd = ['helm', 'install', release_name, '-f', config_file_name, chart, 
                    '-n', ns, '--set', 'server.global.external_labels.shard=' + str(shard)]
        #".format(
        #                        release_name=release_name, ns=ns))

        subprocess.call(cmd, stdout=subprocess.PIPE)
        os.remove(config_file_name)

    api_client_instance = api_client.ApiClient()
    api = core_v1_api.CoreV1Api(api_client_instance)
    api.create_namespaced_config_map(
            body=config_map_file(thanos_sd_file, "{tsd}.yaml".format(tsd=thanos_sd_file),
            json.dumps([{ "targets": thanos_query_targets }])), namespace=ns)
"""
    with open(os.path.join(os.path.dirname(__file__), "thanos_query.yaml")) as f:
        dep = yaml.safe_load(f)
        dep['spec']['template']['spec']['containers'][0]['args'].append(
                '--store.sd-files=/etc/config/{tsd}.yaml'.format(tsd=thanos_sd_file))
        dep['spec']['template']['spec']['volumes'][0]['configMap']['name'] = thanos_sd_file
        dep['metadata']['name'] = THANOS_QUERIER_DEPLOYMENT_PREFIX + release_name_prefix
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace=ns)
        print("Deployment created. status='%s'" % resp.metadata.name)
"""

def handle_upgrade(args):
    pass

def handle_delete(args):
    ns, release_name_prefix = os.environ['PROMETHEUS_NAMESPACE'], os.environ['PROMETHEUS_RELEASE_NAME_PREFIX']
    output = subprocess.run(['helm', 'ls', '-n', ns], capture_output=True)
    format_string = '\n{rn}-shard-[0-9]+'.format(rn=release_name_prefix)
    releases = re.findall(format_string, output.stdout.decode())
    for release in releases:
        subprocess.run(['helm', 'delete', release[1:], '-n', ns])
    subprocess.run(['kubectl', 'delete', 'configmap', 
            CONFIG_MAP_PREFIX + release_name_prefix, '-n', ns])

    

def upgrade_parser(subparsers, subcommand_name):
    parser = subparsers.add_parser(subcommand_name, help='upgrade prometheus helm charts, and start thanos')
    pass

def delete_parser(subparsers, subcommand_name):
    parser = subparsers.add_parser(subcommand_name, help='delete prometheus helm charts, and start thanos')

