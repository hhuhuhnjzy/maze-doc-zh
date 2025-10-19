.. _installation:

安装指南
========

本指南将详细介绍如何在本地环境中安装 Maze 框架及其依赖项。为了确保安装过程顺利，我们建议您**分步安装**：首先手动安装一些对系统环境敏感的核心依赖（如 PyTorch），然后再通过 `pip` 批量安装其余依赖。

Maze 基于 Python 3.11 构建，建议使用虚拟环境以避免依赖冲突。

步骤 1：创建并激活虚拟环境（推荐）
------------------------------------

我们强烈建议使用 `venv` 或 `conda` 创建独立的 Python 虚拟环境：

.. code-block:: bash

   # 使用 venv 创建虚拟环境
   python -m venv maze-env
   source maze-env/bin/activate    # Linux/macOS
   # maze-env\Scripts\activate     # Windows

激活后，您的命令行提示符通常会显示 `(maze-env)`。

步骤 2：手动安装 PyTorch 及其相关库
----------------------------------

根据官方 `requirements.txt` 文件，以下包由于包含平台相关的二进制文件，**不建议直接通过 `requirements.txt` 安装**：

- ``torch==2.6.0``
- ``torchvision==0.21.0``

请根据您的操作系统和是否拥有 NVIDIA GPU（以及 CUDA 版本）选择合适的安装命令。

**如果您有 NVIDIA GPU 并希望启用 GPU 加速：**

前往 `https://pytorch.org/get-started/locally/ <https://pytorch.org/get-started/locally/>`_ 获取最新命令。例如，在撰写本文时，适用于 Linux + CUDA 11.8 的命令为：

.. code-block:: bash

   pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu118

**如果您使用 CPU-only 环境（无 GPU 或仅用 CPU）：**

.. code-block:: bash

   pip install torch==2.6.0+cpu torchvision==0.21.0+cpu --index-url https://download.pytorch.org/whl/cpu

> .. note::
>    请务必访问 PyTorch 官网获取与您系统匹配的安装命令。错误的版本可能导致性能下降或运行失败。

步骤 3：安装其他第三方依赖
----------------------------

现在，您可以安全地安装剩余的依赖项。这些包大多为纯 Python 包或已提供通用二进制分发（wheel），安装成功率高。

1. 确保您已在项目根目录下（即包含 `requirements.txt` 的目录）。
2. 执行以下命令：

.. code-block:: bash

   pip install -r requirements.txt

该命令将自动从清华源（`pypi.tuna.tsinghua.edu.cn`）安装所有必需的第三方库，包括 FastAPI、Flask、Ray、Transformers、EasyOCR 等。

> .. warning::
>    如果您跳过步骤 2 直接运行此命令，可能会安装到不兼容的 `torch` 版本（例如 CPU 版本覆盖了 GPU 版本），导致后续运行效率低下。

步骤 4：安装 Maze 项目本身
---------------------------

使用可编辑模式（`-e`）安装 Maze，以便开发和调试，并注册 `maze` 命令行工具：

.. code-block:: bash

   pip install -e .

安装完成后，您可以通过以下命令验证安装：

.. code-block:: bash

   maze --help

如果正确输出帮助信息，则表示 Maze 已成功安装。

步骤 5：配置项目路径（服务器模式必需）
---------------------------------------

如果您计划使用 **服务器模式**（分布式执行），请务必修改配置文件：

1. 打开 ``config/config.toml``。
2. 找到 ``[paths]`` 部分，将 ``project_root`` 修改为您的 Maze 项目在本地的**绝对路径**：

   .. code-block:: toml

      [paths]
      project_root = "/your/absolute/path/to/Maze"

> .. important::
>    此步骤至关重要。Ray 集群需要通过该路径将代码分发到所有工作节点（Worker Nodes）。路径错误将导致远程节点无法找到代码而执行失败。

可选步骤：下载示例模型
----------------------

如果您希望运行内置的、依赖本地模型的示例工作流（如 EasyOCR 或 Hugging Face 模型），可以运行以下脚本下载模型缓存：

.. code-block:: bash

   python maze/utils/download_model.py

这将把所需模型文件下载到 ``model_cache/`` 目录。

故障排除
--------

- **`torch` 安装失败？**
  请确认网络连接，或尝试更换 PyTorch 官方镜像源。避免使用国内镜像站安装 `torch`，因为它们可能不同步。

- **`pip install -r requirements.txt` 报错？**
  确保已成功安装 `torch` 和 `torchvision`。检查 Python 版本是否为 3.11。

- **`maze` 命令未找到？**
  确认已执行 `pip install -e .`，且虚拟环境已激活。

完成以上步骤后，您的 Maze 环境已准备就绪，可以进入 :ref:`quick_start` 开始第一个分布式 Agent 工作流。