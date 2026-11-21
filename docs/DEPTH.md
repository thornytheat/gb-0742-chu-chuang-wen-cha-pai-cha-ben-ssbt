# 深度登记 橱窗温差排查本

中型项目。保管员先核查探头位置与配对，再结合温湿梯度和报警原单复核展柜。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 点位采信 | 核对单位换算、迟报、冲突原档 | `GET /api/runs/{run_id}/intake` | `app/modules/intake/readings.py` `app/modules/intake/values.py` | `tests/test_intake.py` |
| M2 探头迁移 | 按测量时刻查有效部署与例外 | `GET /api/runs/{run_id}/assignment/lookup` | `app/modules/assignment/windows.py` | `tests/test_assignment.py` |
| M3 时窗配准 | 查一对一配对、时差、未用读数 | `GET /api/runs/{run_id}/pairing/{cabinet}` | `app/modules/pairing/matching.py` `app/modules/pairing/schedule.py` | `tests/test_pairing.py` |
| M4 垂直梯度 | 选择柜时，对照剖面、区间、原行 | `GET /api/runs/{run_id}/gradient/{cabinet}/evidence` | `app/modules/gradient/interval.py` `app/modules/gradient/grade.py` | `tests/test_gradient.py` |
| M5 异常持续 | 定位连续与瞬时异常段及其原行 | `GET /api/runs/{run_id}/episodes/{cabinet}` | `app/modules/episodes/segment.py` | `tests/test_episodes.py` |
| M6 值班单勾稽 | 核对柜时与图档行，查报警误报漏报 | `GET /api/runs/{run_id}/audit` | `app/modules/audit/reconcile.py` | `tests/test_audit.py` |
| M7 证据归卷 | 运行、复算或下载带摘要的归卷 | `POST /api/runs` `POST /api/runs/{run_id}/rerun` `GET /api/runs/{run_id}/export` | `app/modules/archive/pipeline.py` `app/modules/archive/service.py` `app/modules/archive/proof.py` `app/store.py` | `tests/test_archive.py` |

## 陷阱登记

| TRAP | 现象与样例 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | `clean-points.csv` 为 GB18030 | 中文值无法解码 | 回退编码 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_real_encodings_and_bom` |
| TRAP-02 | `night-points.csv` 的首栏含 BOM | 第一段缺探头栏 | 去 BOM 后验列 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_real_encodings_and_bom` |
| TRAP-03 | `night-points.csv` 读数备注跨行 | 错计数据量与行号 | 保留逻辑行和物理范围 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_multiline_note_keeps_source_span_and_text` |
| TRAP-04 | `night-points.csv` 分段档头重复 | 档头混入读数 | 第二个档头进独立账类 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_header_switch_changes_field_positions` |
| TRAP-05 | `night-points.csv` 多尾栏 | 原值遗失 | 错栏数整行保留并隔离 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_wrong_width_retains_last_extra_field` |
| TRAP-06 | `70.7°F` 使用全角数字 | 误隔离等值重传 | 规范化数值字符 | `app/modules/intake/values.py` | `tests/test_intake.py::test_fahrenheit_uncertainty_and_humidity_ratios_normalize_before_dedup` |
| TRAP-07 | 上报 `N/A` 温度 | 把空测代入梯度 | 单独以空温度隔离 | `app/modules/intake/values.py` | `tests/test_intake.py::test_no_temperature_is_distinct_from_other_bad_measurements` |
| TRAP-08 | 探头 `0001` | 失去前导零导致查不到部署 | 字符串保形 | `app/modules/intake/values.py` | `tests/test_intake.py::test_probe_id_keeps_leading_zeros` |
| TRAP-11 | 同一时刻有 Z、+08:00 | 重复读数计两次 | 统一到 UTC 秒键 | `app/timebase.py` `app/modules/intake/readings.py` | `tests/test_intake.py::test_fahrenheit_uncertainty_and_humidity_ratios_normalize_before_dedup` |
| TRAP-13 | 0008 在迁移后才报旧柜读数 | 错投至新柜 | 按测量归位，标迟报 | `app/modules/assignment/windows.py` `app/modules/intake/values.py` | `tests/test_assignment.py::test_late_reading_keeps_old_position_after_receipt_moves` |
| TRAP-14 | 同探头同秒报告不同 | 后到值覆盖 | 双方隔离，该柜时缺证 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_conflicting_same_probe_same_second_is_quarantined_jointly` |
| TRAP-15 | C/F/K 与湿度比例混输 | 偏置和不确定度混算 | 统一温标和湿度尺度 | `app/modules/intake/values.py` | `tests/test_intake.py::test_fahrenheit_uncertainty_and_humidity_ratios_normalize_before_dedup` |
| TRAP-16 | `truncated-points.csv` 缺完整记录 | 生成少证据的可疑归卷 | 与声明数量核对失败后拒绝归卷 | `app/modules/intake/readings.py` `app/modules/archive/service.py` | `tests/test_archive.py::test_truncation_aborts_archive_without_touching_existing_run` |
| TRAP-17 | `night-points.csv` 第二段改中文并换序 | 收报和测量栏对调 | 每段独立映射字段 | `app/modules/intake/readings.py` | `tests/test_intake.py::test_header_switch_changes_field_positions` |
| TRAP-23 | 探头在 13:00 馆内时间换柜 | 同一时刻两柜采信 | 左闭右开选择新柜 | `app/modules/assignment/windows.py` | `tests/test_assignment.py::test_adjacent_windows_are_half_open_at_exact_move` |
| TRAP-25 | 在混合部署契约上叠加同柜同层窗 | 任选一个探头 | 标重叠并拒用重叠段 | `app/modules/assignment/windows.py` | `tests/test_assignment.py::test_second_probe_at_same_position_marks_overlap_only` |

真实反例还有迁移前一分钟的下层读数不能与迁移后的上层配对，近中点无证读数不能挤掉同小时有效候选，区间端点的展示舍入不能改变判级，缺证切断连续异常，工单不能重复清销同一段。

## 对账规则

- 应监测柜时按键集合核对，柜时数分到稳定、异常、缺证。
- 工单与持续异常按柜时定位，列出重复报警和未报持续段。
- 原始 CSV、契约、规则版次确定归卷键。复算和证据导出会验证结果 SHA-256。
