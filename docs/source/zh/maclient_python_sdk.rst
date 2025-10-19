.. _maclient_python_sdk:

maclient_python_sdk：Maze Python 客户端 SDK
==========================================

``maclient_python_sdk`` 是 Maze 框架的 **官方 Python 客户端库**，用于与 ``maserver_api`` 服务交互。它封装了底层 HTTP 通信、序列化、文件打包等细节，让用户能以 **简洁、声明式** 的方式：

- 构建有向无环图（DAG）工作流
- 提交工作流到远程服务端
- 实时查询任务状态与结果
- 下载运行产物
- 管理自定义工具

该 SDK 与服务端的 DAG 定义（如 ``_graph_builder.py`` 中的 ``DAG`` 类）**语义对齐**，但运行在用户本地，不依赖 Ray。

安装
----

.. code-block:: bash

    pip install maclient

快速入门
--------

以下是一个完整示例：构建一个“图像描述 → 文本摘要”两阶段工作流，并提交执行。

.. code-block:: python

    from maclient import MazeClient, task

    # 1. 连接服务端
    client = MazeClient(server_url="http://localhost:8000")

    # 2. 定义任务函数（必须用 @task 装饰）
    @task
    def image_caption(image_path: str) -> dict:
        """生成图像描述"""
        # 实际逻辑由服务端执行
        pass

    @task
    def summarize(text: str) -> dict:
        """对文本进行摘要"""
        pass

    # 3. 构建工作流
    dag = client.new_dag(name="image_analysis")

    # 添加第一个任务（无依赖）
    task1_id = dag.add_task(
        func=image_caption,
        inputs={"image_path": "/input/cat.jpg"}  # 静态输入
    )

    # 添加第二个任务（依赖 task1 的输出）
    task2_id = dag.add_task(
        func=summarize,
        inputs={"text": f"{task1_id}.output.caption"}  # 动态依赖
    )

    # 4. 提交并等待结果
    run_id = client.submit_dag(dag)
    print(f"Workflow submitted with run_id: {run_id}")

    # 5. 轮询直到完成
    while not client.is_run_finished(run_id):
        time.sleep(2)

    # 6. 获取最终结果
    result = client.get_task_result(run_id, task2_id)
    print("Summary:", result["data"]["summary"])

核心概念
--------

任务（Task）
~~~~~~~~~~

- 任务是工作流的基本执行单元。
- 必须使用 ``@task`` 装饰器定义，该装饰器会注入元数据（名称、输入/输出 schema、资源需求等）。
- 任务函数**仅定义接口**，实际执行在服务端 Worker 上进行。
- 输入参数来源有三种：
  1. **静态值**：如 ``inputs={"param": "hello"}``
  2. **上游任务输出**：如 ``inputs={"param": "task_abc.output.key"}`
  3. **自动注入**：如模型路径、API 密钥（由服务端配置决定）

工作流（DAG）
~~~~~~~~~~~

- 由多个任务及其依赖关系构成的有向无环图。
- SDK 中的 ``DAG`` 对象负责构建图结构，但**不执行**。
- 提交时，整个 DAG 会被序列化（含函数字节码）并发送至服务端。

运行（Run）
~~~~~~~~~

- 每次提交 DAG 会生成一个唯一的 ``run_id``。
- 一个 Run 包含：DAG 实例、运行沙箱目录、任务状态记录、产出文件。
- Run 是生命周期管理的基本单位（可查询、下载、销毁）。

API 参考
--------

MazeClient
~~~~~~~~~~

.. autoclass:: maclient.MazeClient
    :members:
    :undoc-members:

    .. automethod:: __init__(self, server_url: str)

        初始化客户端。

        :param server_url: 服务端基础 URL，如 ``"http://localhost:8000"``

    .. automethod:: new_dag(self, name: str = "") -> DAG

        创建一个新的空工作流对象。

        :param name: 工作流名称（可选）
        :return: ``DAG`` 实例

    .. automethod:: submit_dag(self, dag: DAG, project_files: Optional[List[str]] = None) -> str

        将 DAG 提交到服务端执行。

        :param dag: 已构建好的 ``DAG`` 对象
        :param project_files: 需要一并上传的本地文件路径列表（如自定义模块）
        :return: 生成的 ``run_id``

    .. automethod:: get_task_result(self, run_id: str, task_id: str) -> dict

        获取指定任务的执行结果。

        返回字典包含：
        - ``status``: ``"success"``
        - ``task_status``: ``"pending" | "running" | "finished" | "failed" | "CANCELLED"``
        - ``data``: （仅当 finished）任务返回值
        - ``error``: （仅当 failed）错误信息

    .. automethod:: is_run_finished(self, run_id: str) -> bool

        检查指定运行是否已结束（所有任务处于终态）。

    .. automethod:: download_run(self, run_id: str, output_dir: str)

        下载整个运行目录到本地。

        :param run_id: 运行 ID
        :param output_dir: 本地保存路径

    .. automethod:: destroy_run(self, run_id: str)

        请求服务端清理该运行的所有产物（仅当运行已结束）。

    .. automethod:: list_tools(self) -> List[dict]

        获取服务端所有已注册工具的元数据列表。

    .. automethod:: upload_tool(self, name: str, archive_path: str, **metadata)

        上传新工具到服务端。

        :param name: 工具名称
        :param archive_path: ZIP 格式的工具包路径
        :param metadata: 工具元数据（description, type, version, author, usage_notes）

DAG
~~~

.. autoclass:: maclient.DAG
    :members:
    :undoc-members:

    .. automethod:: add_task(self, func: Callable, task_name: Optional[str] = None, inputs: Optional[Dict] = None, resources: Optional[Dict] = None) -> str

        向工作流中添加一个任务节点。

        :param func: 用 ``@task`` 装饰的函数
        :param task_name: 任务别名（可选）
        :param inputs: 输入参数映射字典
        :param resources: 资源需求（如 GPU 数量）
        :return: 生成的唯一 ``task_id``

    .. automethod:: visualize(self)

        在本地可视化当前工作流结构（需安装 matplotlib）。

    .. automethod:: show_structure(self)

        在终端打印工作流的文本结构。

@task 装饰器
~~~~~~~~~~~

.. autofunction:: maclient.task

    用于装饰任务函数，使其能被 Maze 框架识别。

    支持通过参数指定元数据：

    .. code-block:: python

        @task(
            name="my_image_processor",
            description="Processes input image and returns features",
            resources={"gpu": 1},
            version="1.0"
        )
        def process_image(image_path: str) -> dict:
            pass

    装饰器会自动解析函数签名，生成输入/输出 schema，并注入到函数对象的 ``_task_meta`` 属性中。

异常处理
--------

SDK 在遇到服务端错误时会抛出标准异常：

- ``maclient.exceptions.MazeAPIError``：通用 API 错误（如 500）
- ``maclient.exceptions.MazeNotFoundError``：资源未找到（404）
- ``maclient.exceptions.MazeConflictError``：资源冲突（409）

建议在关键操作中使用 try-except 捕获：

.. code-block:: python

    from maclient.exceptions import MazeNotFoundError

    try:
        client.get_task_result("invalid_run", "t1")
    except MazeNotFoundError as e:
        print("Run or task not found:", e)

设计原则
--------

1. **本地构建，远程执行**：用户在本地构建 DAG，但所有计算在服务端完成。
2. **函数即任务**：任务逻辑以 Python 函数形式定义，清晰直观。
3. **依赖显式声明**：通过字符串引用（如 ``"task_id.output.key"``）表达数据依赖。
4. **与服务端强一致**：SDK 的 DAG 模型与服务端 ``ExecuteDAG`` 完全兼容。
5. **零 Ray 依赖**：客户端无需安装或连接 Ray。

参见
----

- :ref:`maserver_api`：服务端 API 详细规范
- :ref:`maworker`：Worker 如何执行这些任务
- ``@task`` 装饰器的完整 schema 定义（位于 ``maze.core.register``）