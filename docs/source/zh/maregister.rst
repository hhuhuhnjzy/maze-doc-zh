.. _maregister:

maregister：Maze 任务注册与元数据管理中心（MaRegister）
=====================================================

``maregister`` 模块实现了 Maze 框架的 **任务注册中心（Task Registry）**，即 **MaRegister**。
它不仅负责统一注册所有可调度的原子任务（“工具函数”），还集中管理每个任务的**完整元数据**，
包括功能描述、输入/输出规范、资源需求等，为 DAG 构建、调度决策、执行验证和可观测性提供基础支撑。

任务元数据模型
--------------

每个任务通过 ``@task`` 装饰器声明其完整元信息，这些信息被统一存储在函数对象的 ``_task_meta`` 属性中，结构如下：

.. code-block:: python

    func._task_meta = {
        'name': str,                      # 任务唯一标识（必须）
        'description': str,               # 功能描述
        'input_parameters': dict,         # 输入参数 Schema（JSON Schema 格式）
        'output_parameters': dict,        # 输出参数 Schema
        'resources': {
            'type': str,                  # 任务类型: 'cpu' | 'gpu' | 'io'
            'cpu_num': int,               # 所需 CPU 核心数
            'mem': int,                   # 所需内存（MB）
            'gpu_mem': int,               # 所需 GPU 显存（MB）
            'model_name': Optional[str],  # 依赖的模型名称（如 "llama-3-8b"）
            'backend': Optional[str]      # 执行后端（如 "vllm", "huggingface"）
        }
    }

特殊类型支持：在 ``input_parameters`` 中可使用预定义类型常量：

- ``TYPE_FILEPATH = "filepath"``
- ``TYPE_FOLDERPATH = "folderpath"``

用于标识文件/目录路径参数，便于后续 I/O 优化或沙箱安全检查。

任务注册机制
------------

1. **手动注册（开发/测试）**
   通过 ``task_registry.register_task(func)`` 显式注册已装饰的函数：

   .. code-block:: python

       @task(
           name="image_caption",
           description="为输入图像生成描述性文本",
           input_parameters={"image": {"type": "filepath"}},
           output_parameters={"caption": {"type": "string"}},
           task_type="gpu",
           gpu_mem=4096,
           model_name="llava-v1.6"
       )
       def image_caption(image: str) -> dict:
           ...

       task_registry.register_task(image_caption)

2. **自动发现（生产部署）**
   调用 ``discover_tasks(tasks_root_path, package_root_path)`` 扫描指定目录：

   - 遍历 ``tasks_root_path`` 下所有 ``.py`` 文件（跳过 ``__init__.py`` 等）
   - 动态导入模块，并检查每个函数是否包含 ``_task_meta``
   - 自动注册所有合法任务

   该机制使得新增工具只需：
   - 将函数放入 ``tools/`` 目录
   - 添加 ``@task(...)`` 装饰器
     即可被 Maze 系统自动识别，无需修改注册代码。

任务调用与验证
--------------

注册后的任务可通过名称获取并执行：

.. code-block:: python

    func = task_registry.get_task("image_caption")
    result = func(image="/data/img.jpg")

MaRegister **不负责参数校验或资源分配**（由调度器和执行器处理），但提供完整的元数据供下游使用：

- **DAG 构建器**：验证节点参数是否符合 ``input_parameters`` Schema
- **MaPath 调度器**：根据 ``resources`` 信息选择合适节点（如 GPU 显存 ≥ 4096MB）
- **malearn 预测器**：根据 ``name`` 映射到工具类型（如 ``"vlm_process"``）以提取特征

与 Maze 框架的协同
------------------

+------------------+-------------------------------------------------------------------------------------+
| 模块             | 如何使用 MaRegister                                                                 |
+==================+=====================================================================================+
| **DAG 解析器**   | 从 JSON 节点的 ``func`` 字段查注册表，获取函数对象与输入 Schema，验证参数合法性       |
+------------------+-------------------------------------------------------------------------------------+
| **MaPath 调度器**| 根据 ``resources`` 中的 ``type``、``gpu_mem`` 等信息进行资源感知调度                  |
+------------------+-------------------------------------------------------------------------------------+
| **malearn**      | 通过任务 ``name`` 映射到预测模型类型（如 ``"llm_process"``），无需重复定义特征逻辑    |
+------------------+-------------------------------------------------------------------------------------+
| **监控系统**     | 利用 ``description`` 和 ``model_name`` 生成可读性高的任务追踪日志                     |
+------------------+-------------------------------------------------------------------------------------+

典型工作流示例
--------------

1. 用户定义工具函数并装饰：

   .. code-block:: python

       @task(name="speech_to_text", task_type="gpu", gpu_mem=2048)
       def stt(audio_path: str) -> dict:
           ...

2. 系统启动时自动注册：

   .. code-block:: python

       task_registry.discover_tasks("src/tools", "src")
       # 日志: Successfully registered task: speech_to_text

3. 用户提交 DAG：

   .. code-block:: json

       {"nodes": [{"id": "t1", "func": "speech_to_text", "args": {"audio_path": "a.wav"}}]}

4. DAG 构建器查注册表 → 调度器查资源需求 → 执行器加载模型 → 完成任务

设计优势
--------

- **声明式**：任务能力与需求显式声明，提升系统可理解性
- **强类型**：输入/输出 Schema 支持静态/动态校验，减少运行时错误
- **资源感知**：调度器可基于精确资源需求做放置决策
- **零侵入**：业务逻辑与框架元数据完全解耦
- **可扩展**：新增任务无需修改核心调度逻辑

异常与日志
----------

- **重复注册**：同名任务会覆盖，并记录 WARNING 日志（便于开发期热更新）
- **无效任务**：未装饰或缺少 ``name`` 的函数会被跳过，并记录 ERROR
- **导入失败**：单个模块错误不影响其他任务注册（fail-safe）

相关常量
--------

- ``TYPE_FILEPATH = "filepath"``
- ``TYPE_FOLDERPATH = "folderpath"``

这些类型可用于后续的 I/O 优化、沙箱路径映射或分布式文件系统挂载。

参见
----

- :ref:`mapath`：调度器如何利用 ``resources`` 信息进行节点选择
- :ref:`malearn`：如何基于任务 ``name`` 映射预测模型