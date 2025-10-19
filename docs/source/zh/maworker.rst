.. _maworker:

maworker：Maze 分布式任务执行单元（Worker）
=========================================

``maworker`` 并非一个独立模块文件，而是指 Maze 框架中运行在 Ray 集群各节点上的 **任务执行单元（Worker）**。
其核心逻辑由 ``remote_task_runner`` 函数实现（通常位于 ``maze.utils.executor`` 中），
负责在隔离环境中安全、可靠地执行由调度器分发的单个任务，并完成输入解析、结果返回与文件同步。

设计目标
--------

- **强隔离性**：每个任务在独立的 ``taskspace`` 目录中执行，避免文件污染
- **依赖自包含**：通过与 Master 节点同步代码与数据，确保执行环境一致性
- **上下文感知**：能正确解析来自上游任务或全局配置的输入参数
- **结果标准化**：统一包装用户函数返回值，便于 DAG 状态管理
- **容错与可观测**：捕获异常、记录日志，并支持级联失败处理

执行流程
--------

每个 Worker 任务的生命周期分为四个阶段：

1. **文件同步拉取（Pull）**
   - 从 Master 节点获取当前运行（run）所需的官方文件哈希清单
   - 对比本地 ``taskspace/`` 目录，仅下载缺失或内容变更的文件
   - 使用 ZIP 流高效传输，确保执行环境与提交时一致

2. **参数解析（Resolve）**
   - 反序列化用户函数（通过 ``cloudpickle``）
   - 设置 ``CUDA_VISIBLE_DEVICES``（若为 GPU 任务）
   - 解析函数参数，支持三种来源（按优先级）：
     a. **显式输入**：DAG 节点中指定的 ``task_inputs``（如 ``"input": "t1.output.text"``）
     b. **上下文继承**：从 ``DAGContext`` Actor 中按参数名获取（如模型路径、API 密钥）
     c. **函数默认值**：使用函数签名中的默认参数
   - 支持嵌套字典访问（如 ``"t1.output.result[0].caption"``）

3. **用户函数执行（Execute）**
   - 切换工作目录至 ``taskspace/``，确保所有文件读写在此隔离空间进行
   - 调用用户函数，捕获返回值
   - 无论成功或失败，均切回原始目录，防止环境泄漏

4. **结果处理与文件推送（Push）**
   - **结果包装**：将用户返回值包装为 ``{output_key: value}`` 字典（与 ``@task`` 中 ``output_parameters`` 一致）
   - **写入上下文**：将结果存入 ``DAGContext``，供下游任务消费
   - **文件推送**：扫描 ``taskspace/`` 中新增或修改的**非代码文件**（如图像、音频、中间结果），上传至 Master 节点

关键机制详解
------------

任务隔离：``taskspace`` 目录
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

每个运行（run）在 Worker 节点上拥有独立的 ``./taskspace/`` 目录，作为任务的**执行沙箱**：

- 所有用户函数的当前工作目录（cwd）被临时切换至此
- 输入文件（如图像、音频）和输出文件（如生成的图片）均存放于此
- 代码文件（.py）和缓存（__pycache__）被排除在上传范围之外，仅同步数据文件

该机制确保：
- 多个 DAG 或同一 DAG 的多个实例互不干扰
- 任务失败不会污染全局环境
- 中间产物可被精确追踪与回收

输入解析：动态依赖解析
~~~~~~~~~~~~~~~~~~~~~~

Worker 能解析形如 ``"task_id.output.key"`` 的动态输入引用：

- 通过 ``DAGContext`` Actor 获取上游任务的完整输出字典
- 按 ``key`` 路径提取具体字段（支持嵌套字典）
- 支持列表索引（如 ``"t2.output.items[0]"``）

例如：
.. code-block:: python

    # 上游任务 t1 返回: {"image_path": "/tmp/a.jpg", "objects": ["cat", "dog"]}
    # 当前任务参数: image="t1.output.image_path", first_obj="t1.output.objects[0]"

    # 解析后:
    # image = "/tmp/a.jpg"
    # first_obj = "cat"

结果标准化：单输出约束
~~~~~~~~~~~~~~~~~~~~~~

为简化 DAG 状态管理，Maze 强制要求每个任务**有且仅有一个输出字段**：

- 该字段名必须在 ``@task(output_parameters=...)`` 中显式声明
- 用户函数返回值会被自动包装为 ``{output_key: return_value}``
- 若用户返回 ``None``，则存储 ``None``，表示无有效输出

例如：
.. code-block:: python

    @task(name="summarize", output_parameters={"summary": {"type": "string"}})
    def summarize(text: str) -> str:
        return llm(f"Summarize: {text}")

    # 实际存入 DAGContext 的是: {"summary": "The quick brown fox..."}

容错与日志
----------

- **异常捕获**：所有异常被捕获并返回 ``{"status": "failed", "err_msg": ...}``
- **日志记录**：使用标准 ``logging`` 模块，按阶段（Sync/Resolve/Execute/Push）输出 DEBUG 级别日志
- **状态上报**：执行结果（成功/失败）通过 Ray 返回给调度器，用于触发后续任务或级联取消

与 Master 节点的通信
--------------------

Worker 通过 HTTP 与 Master 节点交互：

- **拉取文件**：``GET /files/hashes/<run_id>`` 获取哈希清单；``POST /files/download/<run_id>`` 下载文件
- **推送文件**：``POST /files/upload/<run_id>`` 上传新生成的数据文件

该设计避免了对 Redis 或共享文件系统的强依赖，提升了部署灵活性。

性能与安全考量
--------------

- **GPU 隔离**：通过设置 ``CUDA_VISIBLE_DEVICES``，确保多任务共享 GPU 时互不可见
- **内存安全**：使用 ``cloudpickle`` 反序列化，但仅限于受信任的内部函数（由注册中心控制）
- **I/O 优化**：仅同步必要文件，且排除 .py/.pyc，减少网络开销

参见
----

- :ref:`maregister`：任务如何通过 ``@task`` 声明输出规范
- :ref:`mapath`：调度器如何分发任务至 Worker
- :ref:`malearn`：执行时间预测如何用于调度
- ``DAGContext``：任务间数据传递的中心存储