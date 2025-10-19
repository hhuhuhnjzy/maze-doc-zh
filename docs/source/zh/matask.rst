Maze 内置任务库（Built-in Tasks）
================================

Maze 框架提供了一套丰富的**预定义任务（Built-in Tasks）**，覆盖文件 I/O、PDF 处理、OCR 识别、文本分析、工作流控制等多个场景。这些任务均以 ``@task`` 装饰器注册，可直接在 :doc:`maclient_api` 或 :doc:`maplayground` 中调用，无需额外开发。

所有内置任务均位于 ``maze.library.tasks`` 模块下，按功能划分为多个子模块，包括：

- ``io_tasks``：文件与数据加载
- ``pdf_tasks``：PDF 文档处理
- ``image_tasks``：图像与 OCR 处理
- ``llm_tasks``：大语言模型交互
- ``control_tasks``：流程控制与聚合

以下按功能分类详细介绍常用任务。

文件与数据加载任务
------------------

.. _task-load_pdf:

``load_pdf``
~~~~~~~~~~~~
- **描述**：从本地路径加载 PDF 文件，返回其二进制内容。
- **输入**：
  - ``pdf_path`` (str)：PDF 文件的完整路径。
- **输出**：
  - ``pdf_content`` (bytes)：PDF 的二进制内容。
- **用途**：作为 PDF 处理流水线的起点，将文件读入内存供后续任务使用。

.. _task-count_lines:

``count_lines``
~~~~~~~~~~~~~~~
- **描述**：计算上传的第一个文本文件的行数。
- **输入**：
  - ``supplementary_files`` (dict)：由框架自动注入的文件字典。
- **输出**：
  - ``line_count`` (int)：文件总行数。
- **用途**：快速验证文件内容规模，常用于数据预检。

PDF 文本与结构提取任务
-----------------------

.. _task-extract_text_and_tables_from_native_pdf:

``extract_text_and_tables_from_native_pdf``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：从**原生（非扫描）PDF**中快速提取文本和结构化表格。
- **输入**：
  - ``pdf_content`` (bytes)：PDF 二进制内容。
- **输出**：
  - ``extracted_text`` (str)：格式化后的文本与表格内容，按页分隔。
- **限制**：**不适用于扫描件或图片型 PDF**。
- **依赖**：``pdfplumber``
- **用途**：高效解析可选中文本的 PDF，如电子书、报告、论文等。

PDF 图像化与 OCR 任务
---------------------

.. _task-extract_text_from_pdf_range:

``extract_text_from_pdf_range``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：对 PDF 指定页码范围进行**图像渲染 + OCR 识别**，适用于扫描件。
- **输入**：
  - ``pdf_content`` (bytes)：PDF 二进制内容。
  - ``page_range`` (list[int])：起止页码（如 ``[3, 5]``，页码从 1 开始）。
- **输出**：
  - ``extracted_text`` (str)：OCR 识别出的文本，按页标注。
- **依赖**：``PyMuPDF (fitz)`` + ``EasyOCR``（支持中英文）
- **资源需求**：需 GPU（``gpu_mem=4096``）
- **用途**：处理扫描版 PDF、图片型文档、无法复制文本的 PDF。

.. _task-ocr_memory_chunk:

``ocr_memory_chunk``
~~~~~~~~~~~~~~~~~~~~
- **描述**：对内存中的一个小 PDF 块（如 5 页）执行 OCR，返回每页文本列表。
- **输入**：
  - ``pdf_chunk_content`` (bytes)：小 PDF 块的二进制内容。
- **输出**：
  - ``all_text_parts`` (List[str])：每页 OCR 结果组成的列表。
- **用途**：作为并行 OCR 流水线的原子单元，支持大规模文档分块处理。

文档结构与工作流控制任务
-------------------------

.. _task-calculate_page_offset:

``calculate_page_offset``
~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：根据目录逻辑页码与第一章实际物理页码，计算**页码偏移量**。
- **输入**：
  - ``logical_toc_with_ranges`` (dict)：LLM 解析出的带页码范围的目录。
  - ``physical_page_of_chapter_1`` (int)：第一章实际起始页码。
- **输出**：
  - ``page_offset`` (int)：偏移量（物理页 = 逻辑页 + offset）。
- **用途**：解决 PDF 目录页码与实际内容页码不一致的问题，为章节切分提供依据。

.. _task-split_pdf_by_chapters:

``split_pdf_by_chapters``
~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：根据结构化目录和页码偏移，将 PDF **按章节切分为多个独立 PDF 文件**。
- **输入**：
  - ``pdf_content`` (bytes)
  - ``logical_toc_with_ranges`` (dict)
  - ``page_offset`` (int)
  - ``physical_page_of_chapter_1`` (int)
  - ``output_directory`` (str)
- **输出**：
  - ``pdf_chunk_paths`` (List[str])：各章节 PDF 文件的保存路径。
- **用途**：实现书籍、报告的自动化章节拆分，便于后续分章节处理。

.. _task-scatter_chapter_in_memory:

``scatter_chapter_in_memory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：将单个章节 PDF 在内存中按页数切分为多个小块（二进制流）。
- **输入**：
  - ``chapter_pdf_content`` (bytes)
  - ``pages_per_chunk`` (int, 默认 5)
- **输出**：
  - ``page_chunk_contents`` (List[bytes])：小 PDF 块的二进制列表。
- **用途**：为并行 OCR 或摘要生成提供分块输入。

文本聚合与摘要准备任务
-----------------------

.. _task-gather_ocr_results:

``gather_ocr_results``
~~~~~~~~~~~~~~~~~~~~~~
- **描述**：将多个并行 OCR 任务返回的嵌套文本列表**扁平化**为单一页文本列表。
- **输入**：
  - ``ocr_texts`` (List[List[str]])
- **输出**：
  - ``flat_page_texts_list`` (List[str])
- **用途**：聚合分布式 OCR 结果，恢复原始页面顺序。

.. _task-split_text_for_summary:

``split_text_for_summary``
~~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：将页文本列表按指定页数重新组合为**摘要块**，供 LLM 并行摘要。
- **输入**：
  - ``flat_page_texts_list`` (List[str])
  - ``pages_per_summary_chunk`` (int, 默认 10)
- **输出**：
  - ``summary_text_chunks`` (List[str])
- **用途**：解决 LLM 上下文长度限制，实现长文档分段摘要。

结果持久化任务
--------------

.. _task-save_summary_to_md:

``save_summary_to_md``
~~~~~~~~~~~~~~~~~~~~~~
- **描述**：将章节摘要保存为 Markdown 文件。
- **输入**：
  - ``summary_text`` (str)
  - ``output_directory`` (str)
  - ``chapter_title`` (str)
- **输出**：
  - ``summary_file_path`` (str)
- **用途**：结构化保存处理结果，便于阅读与集成。

.. _task-assemble_final_report:

``assemble_final_report``
~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：将多个章节摘要 Markdown 文件**按顺序合并**为完整报告。
- **输入**：
  - ``summary_md_paths`` (List[str])
  - ``book_title`` (str)
  - ``output_directory`` (str)
- **输出**：
  - ``final_report_path`` (str)
- **用途**：生成最终交付物，如书籍摘要、会议纪要合集等。

辅助工具任务
------------

.. _task-scan_chapters_directory:

``scan_chapters_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：扫描目录，获取所有 PDF 章节文件的路径、标题和页数信息。
- **输入**：
  - ``directory_path`` (str)
- **输出**：
  - ``chapters_info`` (List[dict])
- **用途**：批量发现章节文件，用于自动化处理流水线。

.. _task-load_markdown_files:

``load_markdown_files``
~~~~~~~~~~~~~~~~~~~~~~~
- **描述**：加载指定目录下所有 `.md` 摘要文件，返回结构化列表。
- **输入**：
  - ``directory_path`` (str)
- **输出**：
  - ``chapter_summaries`` (List[dict])：含 ``title`` 和 ``content`` 字段。
- **用途**：为报告重组、内容筛选等后处理提供数据源。

使用建议
--------

- **优先使用原生文本提取**：若 PDF 可复制文本，使用 ``extract_text_and_tables_from_native_pdf``，速度更快、精度更高。
- **扫描件走 OCR 流程**：对图像型 PDF，务必使用 ``extract_text_from_pdf_range`` 或分块 OCR 方案。
- **大文档务必分块**：超过 20 页的章节建议通过 ``scatter_chapter_in_memory`` + 并行 OCR 提升效率。
- **结果及时持久化**：关键中间结果（如 OCR 文本、章节 PDF）建议保存到磁盘，避免内存溢出或重复计算。

扩展与定制
----------

所有内置任务均为标准 Python 函数，用户可：
- 直接调用其逻辑进行二次开发；
- 参考其实现编写自定义任务；
- 通过 ``upload_task`` 接口上传增强版任务覆盖默认行为。

> 💡 提示：完整任务列表可通过调用 Maze 服务端的 ``/api/tasks`` 接口动态获取。