.. _maserver_api:

maserver_api：Maze 统一服务端 API 接口
===================================

``maserver_api`` 是 Maze 框架的 **中心化服务端入口**，基于 FastAPI 构建，提供完整的 RESTful API 接口，用于：
- 提交与管理 AI 工作流（DAG）
- 查询任务状态与结果
- 同步运行时文件
- 管理可复用工具（Tool）
- 清理运行产物

所有接口均以 JSON 格式通信，支持文件上传/下载，并与 Ray 集群、DAGContext、任务调度器深度集成。

启动与配置
----------

服务通过以下命令启动：

.. code-block:: bash

    python maserver_api.py

启动时自动：
- 连接本地或远程 Ray 集群（``ray.init(address='auto')``）
- 初始化核心服务（调度器、状态管理器、上下文管理器等）
- 扫描 ``maze/library/tools/`` 目录，自动注册工具函数
- 启动后台调度线程（``dag_manager_daps``）

配置来源于项目根目录下的 ``config.toml``，关键字段包括：

- ``[server] host, port``：服务监听地址
- ``[paths] project_root``：项目根路径（必须）
- ``[paths] model_folder``：模型目录路径

核心服务组件
------------

服务启动时初始化以下全局组件（通过 ``core_services`` 字典共享）：

- ``dag_submission_queue``：工作流提交队列（``queue.Queue``）
- ``task_completion_queue``：任务完成回调队列
- ``status_mgr``：``TaskStatusManager``，记录所有任务状态
- ``dag_ctx_mgr``：``DAGContextManager``，管理运行时上下文（基于 Ray Actor）
- ``resource_mgr``：``ComputeNodeResourceManager``，管理计算资源
- ``scheduler``：``TaskScheduler``，负责任务分发与执行

API 接口概览
------------

.. list-table::
   :header-rows: 1

   * - 路径
     - 方法
     - 功能
   * - ``/submit_workflow/``
     - POST
     - 提交新工作流（含 DAG 定义与项目代码）
   * - ``/runs/{run_id}/summary``
     - GET
     - 获取指定运行的摘要信息
   * - ``/runs/destroy``
     - POST
     - 清理已完成运行的所有产物
   * - ``/runs/{run_id}/download``
     - GET
     - 下载整个运行目录的 ZIP 包
   * - ``/get/``
     - POST
     - 获取单个任务的执行结果或错误信息
   * - ``/runs/{run_id}/tasks/{task_id}/cancel``
     - POST
     - 请求取消指定任务（支持运行中任务的尽力取消）
   * - ``/files/hashes/{run_id}``
     - GET
     - 获取运行目录中所有文件的 SHA256 哈希清单
   * - ``/files/download/{run_id}``
     - POST
     - 下载指定文件列表（用于 Worker 拉取依赖）
   * - ``/files/upload/{run_id}``
     - POST
     - 上传新生成的文件（用于 Worker 推送结果）
   * - ``/tools``
     - GET
     - 列出所有已注册的工具
   * - ``/tools/upload``
     - POST
     - 上传新工具（含元数据与代码包）
   * - ``/tools/{tool_name}``
     - DELETE
     - 删除指定工具

详细接口说明
------------

提交工作流：``POST /submit_workflow/``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**请求体（multipart/form-data）**：

- ``workflow_payload``: JSON 文件，包含 DAG 定义，格式如下：

  .. code-block:: json

    {
      "tasks": {
        "t1": {
          "func_name": "image_caption",
          "serialized_func": "<base64-encoded cloudpickle>",
          "dependencies": [],
          "inputs": {"image_path": "/input/cat.jpg"}
        },
        "t2": {
          "func_name": "summarize",
          "serialized_func": "...",
          "dependencies": ["t1"],
          "inputs": {"text": "t1.output.caption"}
        }
      }
    }

- ``project_archive``: ZIP 文件，包含用户项目代码（将被解压至运行沙箱）

**响应**：

.. code-block:: json

    {
      "status": "success",
      "msg": "Workflow submitted successfully.",
      "run_id": "a1b2c3d4-..."
    }

获取任务结果：``POST /get/``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**请求体（JSON）**：

.. code-block:: json

    { "run_id": "a1b2c3d4-...", "task_id": "t1" }

**响应（成功）**：

.. code-block:: json

    {
      "status": "success",
      "task_status": "finished",
      "data": { "caption": "A cute cat on the sofa." }
    }

**响应（失败）**：

.. code-block:: json

    {
      "status": "success",
      "task_status": "failed",
      "error": "ValueError: Invalid image format"
    }

文件同步接口
~~~~~~~~~~~~

- **获取哈希清单**：``GET /files/hashes/{run_id}``

  返回运行目录中所有文件的相对路径与 SHA256 哈希，用于 Worker 判断需拉取哪些文件。

- **拉取文件**：``POST /files/download/{run_id}``

  请求体为 JSON：``{"files": ["a.py", "data/input.jpg"]}``，返回 ZIP 流。

- **推送文件**：``POST /files/upload/{run_id}``

  使用 ``multipart/form-data`` 上传，字段名为文件相对路径（如 ``output/result.png``）。

工具管理接口
~~~~~~~~~~~~

- **列出工具**：``GET /tools``

  返回所有已安装工具的元数据列表，每个条目包含 ``name, description, type, version, author`` 等字段。

- **上传工具**：``POST /tools/upload``

  表单字段：
  - ``tool_name``（必填）
  - ``description``, ``tool_type``, ``version``, ``author``, ``usage_notes``
  - ``tool_archive``：ZIP 格式的工具包

  工具将被解压至 ``{project_root}/maze/model_cache/{tool_name}/``，并写入 ``metadata.json``。

- **删除工具**：``DELETE /tools/{tool_name}``

  安全删除指定工具目录（路径校验防止目录遍历）。

运行管理接口
~~~~~~~~~~~~

- **获取运行摘要**：``GET /runs/{run_id}/summary``

  返回该运行中所有任务的状态、名称、耗时等信息。

- **下载运行产物**：``GET /runs/{run_id}/download``

  返回整个运行目录的 ZIP 压缩包，便于用户归档或调试。

- **销毁运行**：``POST /runs/destroy``

  请求体：``{"run_id": "..."}``。仅允许销毁**所有任务均已终止**的运行，否则返回 400。

- **取消任务**：``POST /runs/{run_id}/tasks/{task_id}/cancel``

  将任务状态设为 ``CANCELLED``。若任务正在运行，尝试通过 Ray 进行“尽力取消”（best-effort）。

错误处理
--------

- **400 Bad Request**：请求参数错误（如尝试销毁活跃运行）
- **404 Not Found**：run_id 或 task_id 不存在
- **409 Conflict**：资源冲突（如重复上传同名工具）
- **500 Internal Server Error**：服务内部异常（含完整 traceback 日志）

日志与可观测性
--------------

- 使用 ``maze.utils.log_config.setup_logging(mode='server')`` 初始化结构化日志
- 关键操作（提交、取消、上传、销毁）均有 INFO 级别日志
- 异常路径记录完整堆栈（``exc_info=True``）
- 日志输出至控制台及文件（取决于配置）

参见
----

- :ref:`maworker`：Worker 如何调用这些 API 进行文件同步
- :ref:`mapath`：``TaskScheduler`` 与 ``dag_manager_daps`` 的调度逻辑
- :ref:`maregister`：工具如何通过 ``task_registry`` 注册
- ``DAGContextManager``：任务结果存储与查询的底层机制