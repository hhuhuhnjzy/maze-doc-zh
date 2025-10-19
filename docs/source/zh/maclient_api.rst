MazeClient Web API 接口文档
============================

MazeClient 提供了一套基于 FastAPI 的 RESTful Web API，用于远程管理会话、工作流、任务和运行实例。该 API 支持创建客户端会话、定义工作流、动态注册任务函数、提交执行、查询结果等完整生命周期操作。

所有接口均以 ``/api`` 为前缀，部分接口路径中包含动态参数（如 ``{session_id}``、``{workflow_id}`` 等）。

健康检查与资源概览
--------------------

.. http:get:: /api/health

   健康检查接口，返回服务状态和资源统计信息。

   :statuscode 200: 服务正常
   :statuscode 503: 服务不可用

   **响应示例**:

   .. code-block:: json

      {
        "status": "healthy",
        "timestamp": 1712345678.123,
        "sessions_count": 2,
        "workflows_count": 5,
        "runs_count": 3,
        "builtin_tasks_count": 4,
        "total_registered_tasks": 10
      }

.. http:get:: /api/sessions

   列出当前所有活跃会话及其资源概览。

   :statuscode 200: 成功返回会话列表

   **响应字段**:

   - ``session_id``: 会话唯一标识
   - ``server_address``: 关联的 Maze 服务端地址
   - ``workflows_count``: 该会话中创建工作流数量
   - ``runs_count``: 当前运行实例数量
   - ``tasks_count``: 已注册任务函数数量

会话管理
--------

.. http:post:: /api/client/create

   创建一个新的 MazeClient 会话。

   :statuscode 201: 会话创建成功
   :statuscode 400: 请求参数错误

   **请求体（JSON）**:

   .. code-block:: json

      {
        "server_address": "127.0.0.1:6380"
      }

   **响应**:

   返回 ``session_id``，后续所有操作需通过该 ID 标识会话。

.. http:delete:: /api/{session_id}/cleanup

   清理指定会话的所有资源（包括工作流、运行实例、任务函数等）。

   :param string session_id: 会话唯一标识
   :statuscode 200: 清理成功
   :statuscode 404: 会话不存在

工作流管理
----------

.. http:post:: /api/{session_id}/workflows/create

   在指定会话中创建工作流。

   :param string session_id: 会话唯一标识
   :statuscode 201: 工作流创建成功

   **请求体（JSON）**:

   .. code-block:: json

      {
        "name": "my_workflow"
      }

   **响应**:

   返回 ``workflow_id``，用于后续任务添加和提交。

.. http:get:: /api/{session_id}/workflows/{workflow_id}/structure

   获取工作流的结构图（任务依赖关系）。

   :param string session_id: 会话唯一标识
   :param string workflow_id: 工作流 ID

.. http:delete:: /api/{session_id}/workflows/{workflow_id}/tasks/{task_id}

   从工作流中删除指定任务（强制删除，无视依赖）。

   :param string session_id: 会话唯一标识
   :param string workflow_id: 工作流 ID
   :param string task_id: 任务 ID

任务管理
--------

.. http:post:: /api/{session_id}/workflows/{workflow_id}/tasks/add

   向工作流添加一个任务。

   :param string session_id: 会话唯一标识
   :param string workflow_id: 工作流 ID

   **请求体（JSON）**:

   .. code-block:: json

      {
        "function_name": "my_task_func",
        "task_name": "Step 1",
        "inputs": {"param1": "value1"},
        "file_paths": ["/data/file.txt"],
        "resources": {"cpu": "2", "memory": "4G"}
      }

   **说明**:

   - ``function_name`` 必须是已注册的任务函数（内置或动态注册）。
   - ``file_paths`` 和 ``resources`` 为可选字段。

.. http:put:: /api/{session_id}/workflows/{workflow_id}/tasks/{task_id}

   更新已有任务的配置（函数、输入、资源等）。

.. http:get:: /api/{session_id}/workflows/{workflow_id}/task/{task_id}/info

   获取指定任务的详细信息。

.. http:get:: /api/{session_id}/tasks/available

   列出当前会话中所有可用的任务函数（含元数据，如描述、输入/输出参数等）。

动态任务注册
------------

.. http:post:: /api/{session_id}/tasks/register

   通过上传 Python 代码字符串动态注册任务函数。

   :param string session_id: 会话唯一标识

   **表单参数**:

   - ``task_code``: 包含任务函数定义的 Python 代码（字符串）
   - ``function_name``: 要注册的函数名

   **要求**:

   函数必须使用 ``@task`` 装饰器标记，否则无法被识别为有效任务。

任务包上传
----------

.. http:post:: /api/{session_id}/tasks/upload

   上传 ZIP 格式的任务包（包含任务代码、依赖、配置等）。

   :param string session_id: 会话唯一标识

   **表单参数**:

   - ``task_archive``: ZIP 文件（File）
   - ``description``: 任务描述
   - ``task_type``: 任务类型（如 "llm", "data_processing"）
   - ``version``: 版本号（默认 "1.0.0"）
   - ``author``: 作者（默认 "unknown"）

工作流执行与结果查询
----------------------

.. http:post:: /api/{session_id}/workflows/{workflow_id}/submit

   提交工作流执行。

   :param string session_id: 会话唯一标识
   :param string workflow_id: 工作流 ID

   **请求体（JSON）**:

   .. code-block:: json

      {
        "mode": "server"  // 可选值："server" 或 "local"
      }

   **响应**:

   返回 ``run_id``，用于后续查询或控制。

.. http:post:: /api/{session_id}/tasks/result

   获取指定任务的执行结果（支持同步等待）。

   :param string session_id: 会话唯一标识

   **请求体（JSON）**:

   .. code-block:: json

      {
        "run_id": "run-123",
        "task_id": "task-456",
        "wait": true,
        "timeout": 300,
        "poll_interval": 2.0
      }

.. http:post:: /api/{session_id}/tasks/result/async

   异步获取任务结果（基于 asyncio 轮询）。

.. http:post:: /api/{session_id}/tasks/cancel

   取消指定任务的执行。

.. http:get:: /api/{session_id}/runs/{run_id}/summary

   获取整个运行实例的摘要信息（各任务状态、耗时等）。

.. http:post:: /api/{session_id}/runs/{run_id}/destroy

   销毁运行实例，释放资源。

前端与跨域支持
--------------

.. http:get:: /

   返回内置的 Web 前端页面（位于 ``frontend/index.html``），可用于可视化操作。

**CORS 支持**：API 已启用 CORS，允许任意来源跨域访问，便于 Web 前端集成。

错误处理
--------

所有接口在出错时返回标准 HTTP 错误码（如 404、500）及 JSON 格式的错误详情：

.. code-block:: json

   {
     "detail": "Failed to create client: Connection refused"
   }

日志记录
--------

服务启动时自动加载内置任务函数（来自同目录下的 ``task.py``），并在日志中输出加载信息。