REASONS = {
    "EMPTY_LINE": "空记录", "HEADER_REPEAT": "重复栏头", "WRONG_WIDTH": "栏数不符",
    "BAD_PROBE": "探头号格式无效", "BAD_TIME": "时间缺偏移或无效", "RECEIPT_BEFORE_MEASURE": "收报早于测量",
    "NO_TEMPERATURE": "温度空测", "BAD_UNIT": "单位无效", "BAD_READING": "量值或标准不确定度无效",
    "DUPLICATE_READING": "同探头同刻等值回传", "READING_CONFLICT": "同探头同刻报告矛盾",
    "NO_DEPLOYMENT": "测量时刻无有效部署", "DEPLOYMENT_CONFLICT": "部署时间窗重叠", "OFF_SHIFT": "测量在值班时窗外",
    "LATE_RECEIPT": "收报延迟", "EXTRA_UPPER": "同柜同小时有额外上层记录", "UNUSED_LOWER": "下层记录未被配准",
    "LOWER_CONTENTION": "下层记录已分配给相邻小时",

    "MISSING_UPPER": "缺上层测量", "NO_COMPATIBLE_LOWER": "无可用下层证据", "MISSING_RH": "湿度证据不足",
    "CI_OVERLAP": "置信区间跨阈值",

    "CANCELLED": "工单已撤销，处置未发生", "LATE_ARRIVAL": "到场晚于段首，前段柜时仍缺处置",
    "ARRIVED_AFTER_EPISODE": "到场晚于段末，未证明任何柜时", "NO_TICKET": "段内无报警工单",
    "ALL_TICKETS_CANCELLED": "相关工单均已撤销，处置未发生", "TRANSIENT_ONLY": "仅瞬时异常，未构成持续段",
}


def mark(row, disposition, reason):
    row.update(disposition=disposition, code=reason, note=REASONS[reason])
