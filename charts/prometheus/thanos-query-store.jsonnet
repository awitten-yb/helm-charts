local t = import 'kube-thanos/thanos.libsonnet';

// For an example with every option and component, please check all.jsonnet

local commonConfig = {
  config+:: {
    local cfg = self,
    namespace: std.extVar('namespace'),
    version: 'v0.19.0',
    image: 'quay.io/thanos/thanos:' + cfg.version,
    objectStorageConfig: {
      name: 'thanos-objectstorage',
      key: 'thanos.yaml',
    },
    volumeClaimTemplate: {
      spec: {
        accessModes: ['ReadWriteOnce'],
        resources: {
          requests: {
            storage: '10Gi',
          },
        },
      },
    },
  },
};


local storeSdFilePrefix = 'thanos-querier-file-sd-';

local shardCount = std.extVar('shards');

local releaseNamePrefix = std.extVar('release');

local s = t.store(commonConfig.config {
  replicas: 1,
  serviceMonitor: true,
});

local q = t.query(commonConfig.config {
  replicas: 1,
  replicaLabels: ['prometheus_replica', 'rule_replica'],
  serviceMonitor: true,
  stores+: [
    'dns+%s-shard-%s-prometheus-server.%s.svc.cluster.local:10901' % [releaseNamePrefix, x, std.extVar('namespace')] 
    for x in std.range(0, std.parseInt(shardCount) - 1)
  ],
});

{ ['thanos-store-' + name]: s[name] for name in std.objectFields(s) } +
{ ['thanos-query-' + name]: q[name] for name in std.objectFields(q) }
