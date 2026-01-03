# 项目结构总览（脱敏版）

> 说明：
> - 这是“让你熟悉项目”的结构索引，优先覆盖 **代码 / 配置 / 模板 / 工具 / 测试**。
> - 仓库里存在部分以真实样例命名的文档/结果文件目录（可能含个人信息）。为符合数据安全要求，这里**不展开列出具体文件名**，只描述用途与建议处理方式。

```text
肠癌358基因/
├── AGENTS.md # 仓库开发/测试/数据安全规范（重要）
├── README.md # 项目介绍与入口说明
├── pytest.ini # pytest 配置
├── requirements.txt # 运行依赖
├── requirements-dev.txt # 开发/测试依赖
├── setup.py # Python 包安装与命令行入口配置
├── data_get.md # 公共知识库下载来源整理（CIViC/CGI/等）
├── 肺癌甲基化检测 # 甲基化相关说明文档（UTF-8 文本）
│
├── config/ # YAML 配置（映射/项目识别/全局设置/过滤）
│   ├── settings.yaml # 全局设置（含 knowledge_bases 路径与筛选策略）
│   ├── mapping.yaml # Excel 字段 -> 模板变量映射（主版本）
│   ├── cnv_fusion_hla_mapping.yaml # CNV/Fusion/HLA 相关表映射补充
│   ├── drug_tables_config.yaml # 药物明细表（drug_*）配置
│   ├── filtering.yaml # Variations 等表格的数据过滤策略
│   ├── project_types.yaml # 项目类型识别与默认模板选择
│   ├── patient_info.yaml # 患者信息字段规范/默认值
│   ├── variant_table_baseline.yaml # variants_2_1 “未见突变”基线行配置
│   ├── mapping.yaml.backup # mapping.yaml 历史备份（对照用）
│   ├── mapping.yaml.bak # mapping.yaml 历史备份（对照用）
│   ├── mapping.yaml.phase1 # mapping.yaml 阶段版本（对照用）
│   ├── ._mapping.yaml # macOS 资源叉文件（可删除）
│   ├── ._settings.yaml # macOS 资源叉文件（可删除）
│   ├── ._filtering.yaml # macOS 资源叉文件（可删除）
│   ├── ._project_types.yaml # macOS 资源叉文件（可删除）
│   └── ._variant_table_baseline.yaml # macOS 资源叉文件（可删除）
│
├── reportgen/ # 主 Python 包（Excel -> ReportData -> docxtpl 渲染）
│   ├── __init__.py # 包入口
│   ├── __version__.py # 版本号
│   ├── cli.py # CLI：reportgen generate / reportgen validate
│   │
│   ├── config/
│   │   ├── __init__.py # config 子包入口
│   │   ├── loader.py # ConfigLoader：读取 mapping/settings/filtering/project_types
│   │   └── ._loader.py # macOS 资源叉文件（可删除）
│   │
│   ├── models/
│   │   ├── __init__.py # models 子包入口
│   │   ├── excel_data.py # ExcelDataSource：sheet/表数据容器
│   │   ├── mapping.py # FieldMapping/TableMapping：映射与格式化模型
│   │   └── report_data.py # ReportData：模板渲染上下文（fields/tables）
│   │
│   ├── utils/
│   │   ├── __init__.py # utils 子包入口
│   │   ├── file_utils.py # 文件/路径工具
│   │   ├── hgvs_utils.py # HGVS 工具：位点拼接/变异类型中文推断
│   │   ├── logger.py # 统一日志封装（结构化输出）
│   │   └── validators.py # 输入校验（Excel/Docx/路径等）
│   │
│   ├── knowledge/
│   │   ├── __init__.py # knowledge 子包入口
│   │   ├── gene_knowledge.py # 基因知识库加载与“诊疗知识”段落生成
│   │   └── mutation_description.py # c./p.HGVS -> 中文位点说明生成器
│   │
│   └── core/
│       ├── __init__.py # core 子包入口
│       ├── report_generator.py # 报告生成主流程（读->清洗->映射->渲染）
│       ├── excel_reader.py # Excel 读取与标准化（sheet 解析）
│       ├── data_cleaner.py # 数据清洗（文本/数值/空值等）
│       ├── field_mapper.py # 映射与聚合逻辑（含 variants_2_1 / targeted_drug_tips / KB筛选）
│       ├── template_renderer.py # docxtpl 渲染 + 渲染后清理（空行等）
│       ├── project_detector.py # 项目类型识别（读取 project_types.yaml）
│       ├── template_bridge_358.py # 358 面板桥接逻辑（MSI/TMB/未检出基因等）
│       ├── ._excel_reader.py # macOS 资源叉文件（可删除）
│       ├── ._field_mapper.py # macOS 资源叉文件（可删除）
│       ├── ._project_detector.py # macOS 资源叉文件（可删除）
│       ├── ._template_bridge_358.py # macOS 资源叉文件（可删除）
│       └── ._report_generator.py # macOS 资源叉文件（可删除）
│
├── templates/ # docxtpl Word 模板（包含 jinja2 变量/循环）
│   ├── aligned_template_with_cnv_fusion_hla_FIXED.docx # 推荐生产模板（批注已清理，CNV/Fusion/HLA齐全）
│   ├── aligned_template_with_cnv_fusion_hla_FIXED.docx.bak # FIXED 模板备份
│   ├── aligned_template_with_cnv_fusion_hla.docx # FIXED 前版本（对照用）
│   ├── aligned_template_with_drugs.docx # 含药物表版本（对照用）
│   ├── aligned_template.docx # 早期对齐模板（对照用）
│   ├── aligned_template_final.docx # 对齐模板阶段产物（对照用）
│   ├── aligned_template_from_tempe_test.docx # tempe_test 对照导出的模板（对照用）
│   ├── jinja2_template_358.docx # 358 jinja2 模板早期版本
│   ├── jinja2_template_358_v2.docx # 358 jinja2 模板（保留批注，用于核对需求）
│   ├── jinja2_template_358_v3.docx # 358 模板迭代版本（对照用）
│   ├── jinja2_template_358_v4.docx # 358 模板迭代版本（对照用）
│   ├── jinja2_template_358_v5.docx # 358 模板迭代版本（对照用）
│   ├── jinja2_template_358_v5_highlighted.docx # v5 高亮变量版（排查模板变量用）
│   ├── jinja2_template_358_v6.docx # 358 模板迭代版本（对照用）
│   ├── jinja2_template_358_v7.docx # 358 模板迭代版本（对照用）
│   ├── jinja2_template_358_v7_highlighted.docx # v7 高亮变量版
│   ├── jinja2_template_358_v8.docx # 358 模板迭代版本（对照用）
│   ├── jinja2_template_358_v8_highlighted.docx # v8 高亮变量版
│   ├── jinja2_template_358_v9.docx # 358 模板迭代版本（对照用）
│   ├── table_template.docx # 表格实验模板（对照用）
│   ├── test_bridge_output.docx # 模板桥接输出测试文件（本地调试产物）
│   ├── test_output_excel.docx # Excel 输出测试文件（本地调试产物）
│   ├── test_output_v3.docx # 输出测试文件（本地调试产物）
│   ├── test_output_v4.docx # 输出测试文件（本地调试产物）
│   └── test_template.docx # 模板测试文件（本地调试产物）
│
├── data/
│   ├── knowledge_bases/
│   │   ├── README.md # 离线知识库说明（如何下载/构建/引用）
│   │   ├── raw/ # 原始下载文件目录（默认被 .gitignore 忽略）
│   │   │   └── .gitkeep # 占位文件
│   │   └── processed/
│   │       ├── targeted_drug_db_public.xlsx # 由 CIViC/CGI + 内部库构建的靶向药物提示库
│   │       └── immune_gene_list_public.xlsx # 由 CGI 免疫相关条目 + 内部清单构建的免疫基因列表
│   ├── input/ # 本地输入样例目录（默认被 .gitignore 忽略，避免纳入敏感数据）
│   ├── output/ # 本地输出目录（默认被 .gitignore 忽略）
│   └── logs/ # 本地日志目录（默认被 .gitignore 忽略）
│
├── tools/ # 辅助工具（分析/模板修复/对齐/知识库构建）
│   ├── knowledge_bases/
│   │   └── build_public_kb.py # 构建 public KB（生成 data/knowledge_bases/processed/*.xlsx）
│   ├── analysis/ # Excel/Docx结构分析与对齐检查脚本
│   ├── template/ # 模板修复/变量补齐/药物表相关脚本
│   ├── debug/ # 调试脚本（配置/表结构/融合等）
│   ├── experiments/ # 试验脚本（过滤/HLA/skip rows等）
│   ├── sanitize_docx.py # docx 脱敏工具（用于把样例模板/报告去标识化）
│   ├── compare_docx.py # docx 对比工具
│   ├── build_aligned_template.py # 构建对齐模板工具（历史产物）
│   ├── make_template_from_baseline.py # 从 baseline 生成模板的工具
│   ├── highlight_jinja2_vars.py # 高亮模板变量（排查漏字段）
│   ├── update_template_variables.py # 更新模板变量引用（对齐 mapping）
│   ├── fix_table_loops.py # 修复模板循环（for/if 控制行）
│   ├── complete_template_update.py # 批量模板修复/更新脚本
│   └── tools/_work/ # 临时解包/中间文件（建议本地使用，勿纳入版本管理）
│
├── scripts/ # 运行/实验脚本（多为一次性模板改造或调试）
│   ├── generate_report.py # 单份报告生成脚本
│   ├── batch_generate_reports.py # 批量生成报告脚本
│   ├── create_jinja2_template.py # 创建/改造 jinja2 模板脚本
│   ├── pack_docx.py # 解包/回包 docx 工具脚本
│   ├── add_variant_loops.py # 给模板注入变异表循环
│   ├── add_summary_table_loop.py # 给汇总表注入循环（旧版）
│   ├── add_summary_table_loop_v2.py # 给汇总表注入循环（新版）
│   ├── add_undetected_genes_loop.py # 未检出基因表循环注入
│   ├── add_cnv_fusion_variables.py # CNV/Fusion/HLA 变量注入
│   ├── implement_cnv_fusion_vars.py # CNV/Fusion/HLA 变量落地实现
│   ├── test_template_v3.py # 模板渲染测试脚本（v3）
│   ├── test_template_v4.py # 模板渲染测试脚本（v4）
│   ├── test_template_with_excel.py # 用真实/样例 Excel 跑模板渲染
│   ├── test_template_bridge.py # template_bridge_358 逻辑测试脚本
│   ├── test_reportgen_pipeline.py # 报告生成管线测试脚本
│   ├── test_full_pipeline.py # 全流程测试脚本
│   └── scripts/._*.py # macOS 资源叉文件（可删除）
│
├── tests/
│   ├── unit/ # 单元测试（纯逻辑/小范围）
│   ├── integration/ # 集成测试（端到端：Excel -> docx）
│   ├── fixtures/ # 测试夹具（sample_excel/sample_template 等）
│   └── output/ # 测试输出（运行时生成）
│
├── docs/
│   ├── manuals/ # 使用手册（推荐先看）
│   ├── reports/ # 对齐/差异/修复过程报告
│   ├── analysis/ # 分析文档
│   ├── samples/ # 样例 docx（含 sanitized 版本）
│   ├── contracts/ # 合同/交付相关文档
│   └── presentations/ # 汇报材料（PPT）
│
├── 2025.12.10/ # 对照样例目录（可能含终版报告docx与个人信息；建议只本地保存/脱敏后再纳入版本管理）
│   ├── 示例：+++自建肠癌基因数据库.xlsx # 内部靶向用药/解析库示例（批注里有提到）
│   ├── 对应关系：*.result.xlsx # Excel 与终版报告的对应关系样例（本地）
│   └── *.docx # （敏感）终版报告样例（含批注/个人信息），用于对齐需求与模板
│
└── 2025.12.12/
    ├── 1-免疫治疗相关基因.xlsx # 免疫正/负相关/超进展相关基因清单（批注里有提到）
    ├── 2-各癌种重要基因整理（...）.xlsx # 各癌种重要基因参考表（用于“未见突变”基线/扩展）
    └── 3-基因-转录本号-染色体信息.xls # Gene-Transcript-Chr 对照表（用于补全/未检出基因列表）
```
