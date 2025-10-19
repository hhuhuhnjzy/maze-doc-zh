.. _malearn:

malearn：面向 Maze 框架的机器学习执行时间预测模块
==================================================

``malearn`` 模块为 Maze 调度框架（ASPLOS '26）提供了一套轻量级、可扩展且支持在线学习的任务执行时间预测系统。
该模块专为 LLM 智能体工作流中的异构任务（如文本推理、视觉语言处理、语音识别等）设计，通过机器学习模型对任务运行时长进行精准估计，
从而支撑 Maze 的 **DAPS 调度算法**（基于任务紧急度与关键度的动态优先级调度）。

设计目标
--------

在 Maze 框架中，准确的执行时间预测是高效 DAG 调度的基石。``malearn`` 的核心设计理念包括：

- **多模态特征建模**：不同任务类型（如 LLM、VLM、语音）使用各自定制的特征集合。
- **增量学习能力**：随着新任务执行数据的积累，模型可在后台自动更新，持续优化预测精度。
- **鲁棒性保障**：支持异常值过滤、缺失特征默认值填充，并在模型不可用时回退到启发式估计。
- **持久化支持**：模型与训练数据自动落盘，支持服务重启后快速恢复，便于离线分析与调试。

核心组件
--------

ExecTimePredictor：任务类型专属预测器
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: malearn.ExecTimePredictor
   :members:
   :undoc-members:
   :show-inheritance:

每个 ``ExecTimePredictor`` 实例专用于一种工具类型（tool type），独立维护其模型、归一化器和数据集。

当前支持的任务类型及特征如下：

- **``llm_process``**：大语言模型推理任务
  特征：``text_length``（文本长度）、``token_count``（词元数量）、``batch_size``（批大小）、``reason``（是否含推理链）

- **``vlm_process``**：视觉-语言模型任务（如图像问答、图文生成）
  特征：图像高/宽/面积/长宽比、图像熵、边缘密度、文本区域占比、亮度均值与方差、提示词长度及词元数等

- **``llm_fuse2In1``**：双文本融合任务（如对比、摘要）
  特征：两个输入文本的长度与词元数、提示词信息、reason 标志

- **``speech_process``**：语音处理任务（如语音识别）
  特征：``duration``（音频时长）、``audio_entropy``（音频熵）、``audio_energy``（音频能量）

默认使用 **XGBoost 回归模型**（与论文中“基于树的在线学习器”一致），同时也支持 MLP 回归器和线性回归，便于对比实验或轻量部署。

DAGTaskPredictor：调度器统一接口
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: malearn.DAGTaskPredictor
   :members:
   :undoc-members:
   :show-inheritance:

这是 Maze 调度器调用的主入口，负责：

1. **函数名映射**：将 DAG 节点中的函数名（如 ``"vlm_inference_v1"``）映射到标准工具类型（如 ``"vlm_process"``）
2. **特征聚合**：从 Redis 中读取所有前置任务（predecessors）的结果，提取为当前任务准备的特征（``succ_task_feat``）
3. **执行预测**：调用对应 ``ExecTimePredictor`` 进行时间估计
4. **安全兜底**：若模型未训练或预测失败，则使用启发式默认值（如 GPU 任务 15 秒，CPU 任务 3 秒，I/O 任务 1 秒）

该设计确保 Maze 在冷启动、数据稀疏或模型异常等场景下仍能做出合理调度决策。

与 Maze 框架的集成
------------------

在 Maze 工作流中，每个任务执行完毕后会将以下信息写入 Redis（键为 ``result:<task_id>``）：

- ``start_time`` / ``end_time``：任务起止时间戳
- ``curr_task_feat``：当前任务的输入特征
- ``succ_task_feat``：为每个后继任务预计算的特征映射

``DAGTaskPredictor.collect_data_for_task()`` 方法会消费这些日志：

- 计算实际执行时间（``end_time - start_time``）
- 将特征与执行时间追加到对应工具类型的 CSV 数据集中
- 当新样本数量达到阈值时，**在后台线程中触发增量训练**

预测结果直接输入 DAPS 调度器（论文 Algorithm 2），用于计算任务的 **关键度（Criticality）** 与 **紧急度（Urgency）**，最终决定任务在调度队列中的优先级。

扩展新任务类型
--------------

若需支持新的任务类型（例如 ``"video_process"``），只需三步：

1. 在 ``ExecTimePredictor.tool_types`` 中添加该类型及其特征列表
2. 在 ``DAGTaskPredictor.func_name_to_tool_type`` 中增加函数名到工具类型的映射
3. 确保任务执行逻辑在日志中输出对应的 ``curr_task_feat``

所有模型和数据按 ``<model_dir>/<tool_type>/`` 目录结构独立存储，互不干扰。

相关参考
--------

- **论文**：*Maze: Efficient Scheduling for LLM Agent Workflows*（ASPLOS '26）
- **附录 E.1**：任务执行时间预测的理论分析（基于二阶泰勒展开与 XGBoost 正则化）
- **图 2(c)**：不同任务类型的资源消耗特征（CPU/GPU/I/O 密集型）
- **DAPS 调度算法**（论文 Algorithm 2）：预测时间如何影响任务优先级