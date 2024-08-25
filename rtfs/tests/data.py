CHUNK_GRAPH = """ClusterNode: 0:2
  ClusterNode: 1:8
  ClusterNode: 1:12
  ClusterNode: 1:10
  ClusterNode: 1:9
  ClusterNode: 1:11
ClusterNode: 1:8
  ChunkNode: runner/shared.py#2.37
  ChunkNode: cowboy_lib/coverage.py#28.31
  ChunkNode: queue/core.py#136.41
  ChunkNode: queue/models.py#138.9
  ChunkNode: queue/service.py#140.31
  ChunkNode: runner/models.py#157.28
  ChunkNode: runner/service.py#159.40
  ChunkNode: tasks/get_baseline.py#181.77
  ChunkNode: test_modules/views.py#237.27
ClusterNode: 0:6
  ChunkNode: runner/shared.py#3.39
  ChunkNode: repo/runner.py#58.41
ClusterNode: 0:1
  ClusterNode: 1:7
  ClusterNode: 1:5
  ClusterNode: 1:4
  ClusterNode: 1:3
  ClusterNode: 1:1
  ClusterNode: 1:2
  ClusterNode: 1:6
ClusterNode: 1:7
  ChunkNode: ast/code.py#6.86
  ChunkNode: ast/service.py#88.43
ClusterNode: 0:7
  ChunkNode: python/ast.py#9.68
  ChunkNode: repo/source_file.py#59.91
ClusterNode: 1:5
  ChunkNode: cowboy_lib/coverage.py#15.39
  ChunkNode: coverage/models.py#113.33
  ChunkNode: coverage/stats.py#116.27
  ChunkNode: target_code/service.py#172.49
ClusterNode: 1:4
  ChunkNode: cowboy_lib/coverage.py#22.50
  ChunkNode: experiments/augment_test.py#124.32
  ChunkNode: repo/models.py#143.87
  ChunkNode: stats/service.py#165.22
ClusterNode: 0:8
  ChunkNode: llm/invoke_llm.py#31.37
  ChunkNode: llm/models.py#34.33
ClusterNode: 0:9
  ChunkNode: llm/models.py#36.67
  ChunkNode: augment_test/composer.py#189.48
ClusterNode: 0:4
  ChunkNode: repo/repository.py#49.98
  ChunkNode: repo/repository.py#57.43
  ChunkNode: tests/conftest.py#77.15
  ChunkNode: tests/test_gitrepo.py#78.29
ClusterNode: 1:3
  ChunkNode: repo/source_file.py#65.28
  ChunkNode: test_modules/test_module.py#72.90
  ChunkNode: cowboy_lib/utils.py#79.28
  ChunkNode: scripts/neuter_repo.py#161.23
ClusterNode: 1:1
  ChunkNode: repo/source_repo.py#66.33
  ChunkNode: test_modules/target_code.py#71.42
  ChunkNode: ast/models.py#87.56
  ChunkNode: scripts/neuter_repo.py#162.46
  ChunkNode: target_code/models.py#171.90
  ChunkNode: test_modules/iter_tms.py#228.41
  ChunkNode: test_modules/models.py#229.67
  ChunkNode: test_modules/service.py#231.17
  ChunkNode: cowboy-server/test.py#240.27
ClusterNode: 0:10
  ChunkNode: cowboy-server/main.py#82.104
  ChunkNode: extensions/sentry.py#132.14
ClusterNode: 1:12
  ChunkNode: cowboy-server/main.py#86.49
  ChunkNode: queue/core.py#137.94
  ChunkNode: runner/service.py#158.22
ClusterNode: 0:5
  ChunkNode: auth/models.py#91.23
  ChunkNode: repo/service.py#145.27
  ChunkNode: repo/service.py#150.47
ClusterNode: 1:10
  ChunkNode: auth/permissions.py#93.50
  ChunkNode: auth/service.py#99.54
  ChunkNode: queue/permissions.py#139.21
  ChunkNode: queue/views.py#141.23
  ChunkNode: queue/views.py#142.53
ClusterNode: 0:3
  ChunkNode: auth/views.py#106.16
  ChunkNode: health/views.py#133.12
  ChunkNode: src/models.py#135.46
  ChunkNode: repo/views.py#153.18
  ChunkNode: repo/views.py#154.12
ClusterNode: 1:9
  ChunkNode: database/core.py#119.52
  ChunkNode: experiments/augment_test.py#127.82
  ChunkNode: experiments/views.py#130.34
  ChunkNode: repo/service.py#146.15
  ChunkNode: repo/service.py#148.36
  ChunkNode: target_code/views.py#173.36
  ChunkNode: test_modules/service.py#233.27
ClusterNode: 0:11
  ChunkNode: tasks/create_tgt_coverage.py#177.46
  ChunkNode: src/utils.py#239.45
ClusterNode: 1:2
  ChunkNode: augment_test/base_strat.py#187.37
  ChunkNode: strats/augment_base.py#202.41
  ChunkNode: strats/augment_with_ctxt_file.py#205.50
  ChunkNode: strats/augment_with_missing.py#206.42
  ChunkNode: strats/prompt.py#208.28
  ChunkNode: strats/prompt.py#209.36
  ChunkNode: augment_test/types.py#211.39
ClusterNode: 1:11
  ChunkNode: evaluators/augment_additive.py#193.48
  ChunkNode: evaluators/augment_parallel.py#195.46
  ChunkNode: evaluators/eval_base.py#198.38
ClusterNode: 1:6
  ChunkNode: strats/augment_strat.py#204.45
  ChunkNode: strats/prompt.py#207.31
  ChunkNode: augment_test/types.py#212.29
"""