.. _mapath:

mapath：Maze 的任务级动态自适应调度器（MaPath）
==============================================

``mapath`` 模块实现了 Maze 框架的核心调度引擎——**MaPath（Multi-agent Path Scheduler）**，
负责将用户提交的 LLM Agent 工作流（以 DAG 形式表达）分解为细粒度任务，并在异构计算集群上进行高效、鲁棒的动态调度。
MaPath 的设计目标是：**在保证低延迟的同时，最大化集群资源利用率与系统吞吐量**。

核心思想
--------

与传统将整个 Agent 视为调度单元的框架（如 AutoGen、AgentScope）不同，MaPath 采用 **任务级调度（task-level scheduling）** 架构：

- 每个工作流被建模为一个 **DAG（有向无环图）**，节点为任务，边为数据依赖。
- 调度器以 **单个任务** 为单位进行资源分配、执行与监控。
- 任务可跨节点调度，支持 CPU、GPU、I/O 等异构资源需求。

这种细粒度调度使得 Maze 能够：
- 更灵活地进行 **负载均衡**
- 避免因单个长任务阻塞整个 Agent
- 在高负载下显著降低 P95 响应时间（论文图 6b）

调度算法：DAPS（Dynamic Adaptive Priority Scheduling）
--------------------------------------------------

MaPath 采用 **DAPS 算法** 动态计算任务优先级。每个就绪任务的优先级得分由两部分加权组成：

.. math::
   \text{Score} = w_1 \cdot \text{Urgency} + w_2 \cdot \text{Criticality}

其中默认权重为：:math:`w_1 = 2.0`, :math:`w_2 = 1.0`。

- **紧急度（Urgency）**：反映工作流剩余推理任务数的紧迫性
  :math:`\text{Urgency} = 1 - \frac{\text{remaining\_inferences}}{\text{max\_known\_inferences}}`

- **关键度（Criticality）**：反映该任务在工作流总耗时中的占比
  :math:`\text{Criticality} = \frac{\text{pred\_exec\_time}}{\text{expected\_dag\_time}}`

> **注**：`pred_exec_time` 由 :ref:`malearn` 模块提供；`expected_dag_time` 基于历史同类工作流的平均执行时间。

优先级队列按 `(提交时间, -Score, 入队序号)` 排序，确保 **高分任务优先、先到先服务、无饥饿**。

系统架构
--------

MaPath 调度器由三个协同工作的线程组成（见 `daps.py`）：

1. **DAG Creator（DAG 构建器）**
   - 从内存队列接收用户提交的工作流（JSON 格式）
   - 使用 `networkx` 重建 DAG 图结构
   - 为每个任务调用 `TaskStatusManager.add_task()` 进行预注册
   - 将入度为 0 的任务加入调度队列

2. **Scheduler & Submitter（调度与提交器）**
   - 从优先级队列中取出最高优先级任务
   - 检查任务是否已被级联取消（如前置任务失败）
   - 调用 `TaskScheduler.submit()` 将任务分发至 Ray 集群执行

3. **Monitor（监控器）**
   - 监听任务完成通知（来自执行节点）
   - 更新任务状态与执行时间
   - 对失败任务触发 **级联取消（Cascade Cancel）**，避免无效计算
   - 当 DAG 中所有任务完成时，记录总耗时并清理内存

资源感知与上下文管理
--------------------

MaPath 通过 `DAGContextManager`（见 `dag_context.py`）实现资源感知调度：

- 为每个运行中的 DAG 创建一个 `DAGContext` Ray Actor
- 上下文存储：DAG ID、首选执行节点、配置参数（如模型缓存路径、API 密钥）
- 调度器通过 `get_least_loaded_node()` 选择当前负载最低的可用节点
- 支持将任务亲和性绑定到特定节点，减少数据传输开销

与 Maze 其他模块的协同
----------------------

- **与 `malearn` 协同**：获取任务执行时间预测，用于 DAPS 评分
- **与 `TaskScheduler` 协同**：实际任务分发与执行
- **与 `TaskStatusManager` 协同**：统一任务状态管理（PENDING / RUNNING / FINISHED / FAILED / CANCELLED）
- **与 `MaRegister` 协同**：使用预定义的工具模板快速构建 DAG

性能优势（来自论文）
--------------------

在动态负载实验中（图 6），MaPath 展现出显著优势：

- **P95 延迟**：在 125% 超载下，Maze-V（启用 MaPath）仅为 285 秒，而 AutoGen 超过 1400 秒
- **吞吐量**：Maze 完成 51 个 DAG（1.02 DAG/min），优于 AutoGen（0.88）、AgentScope（0.86）
- **GPU 利用率**：平均 GPU 显存利用率提升至 60%+，而 Agent 级框架仅 25%

这证明 MaPath 的任务级调度能有效缓解任务积压，提升资源效率。

配置参数
--------

- ``w1``：紧急度权重（默认 2.0）
- ``w2``：关键度权重（默认 1.0）
- ``max_known_inferences``：历史最大推理任务数（用于归一化 Urgency）
- ``task_type_avg_times``：各类任务默认执行时间（用于冷启动兜底）

这些参数可在启动调度器时通过 `args` 或配置文件调整。

相关参考
--------

- **论文**：*Maze: Efficient Scheduling for LLM Agent Workflows*（ASPLOS '26）
- **第 5 节**：Distributed Scheduler（MaPath 架构）
- **算法 2**：DAPS 调度算法伪代码
- **图 6**：动态负载下的响应时间与资源利用率对比
- **附录 E.4**：任务级调度开销分析（平均调度开销仅 0.0043 秒）