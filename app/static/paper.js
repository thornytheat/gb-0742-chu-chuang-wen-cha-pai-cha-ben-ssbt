export const q = (selector, root = document) => root.querySelector(selector);
export const put = (selector, value) => { q(selector).textContent = value ?? '—'; };
export const words = {
  STABLE:'稳定', ABNORMAL:'异常', MISSING:'缺证', UNCERTAIN:'跨阈值', SUSTAINED:'持续异常', TRANSIENT:'瞬时异常',
  MATCHED:'已核销', DUPLICATE_ALARM:'重复报警', MISSING_EVIDENCE:'证据不足', OUTSIDE_SHIFT:'班次外报警',
  STABLE_AT_ALARM:'稳定时报警', TRANSIENT_ONLY:'仅瞬时异常', UNKNOWN_CABINET:'柜号未知', NO_DEPLOYMENT:'无部署',
  DEPLOYMENT_CONFLICT:'部署重叠', MISSING_UPPER:'缺上层读数', NO_COMPATIBLE_LOWER:'无可用下层读数',
  LOWER_CONTENTION:'下层读数占用', CI_OVERLAP:'区间跨阈值', MISSING_RH:'湿度缺证',
  UNUSED_LOWER:'未用下层', EXTRA_UPPER:'额外上层', LATE_RECEIPT:'迟报', temperature:'温度', humidity:'湿度',
  upper:'上层', lower:'下层', accepted:'采信', isolated:'隔离', header:'栏头', duplicate:'重复', blank:'空行',
};
const timeZone = 'Asia/Shanghai';
const clock = new Intl.DateTimeFormat('zh-CN', {timeZone, hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
const date = new Intl.DateTimeFormat('zh-CN', {timeZone,month:'2-digit',day:'2-digit'});
export const hour = (value) => value ? clock.format(new Date(value)) : '—';
export const stamp = (value) => value ? `${date.format(new Date(value))} ${hour(value)}` : '—';

export function el(tag, content, css) {
  const box = document.createElement(tag);
  if (content != null) box.textContent = content;
  if (css) box.className = css;
  return box;
}

export function state(code) {
  return el('span', words[code] ?? code ?? '—', `state ${String(code).toLowerCase()}`);
}

export function choose(select, values, active) {
  select.replaceChildren(...values.map(([key, title]) => new Option(title, key)));
  if (values.some(([key]) => key === active)) select.value = active;
}

export function entries(values) {
  const list = el('dl', null, 'rule-list');
  for (const [term, value] of values) {
    const field = el('dd', null, 'mono');
    field.append(value instanceof Node ? value : String(value ?? '—'));
    list.append(el('dt',term), field);
  }
  return list;
}

export function table(target, rows, columns, empty = '暂无记录。') {
  if (!rows.length) {
    target.replaceChildren(el('p',empty,'empty'));
    return;
  }
  const root = el('table',null,'ledger');
  const head = root.createTHead().insertRow();
  for (const [name, , css] of columns) {
    const cell = el('th', name, css);
    cell.scope = 'col';
    head.append(cell);
  }
  const body = root.createTBody();
  for (const item of rows) {
    const row = body.insertRow();
    for (const [, value, css] of columns) {
      const field = typeof value === 'function' ? value(item) : item[value];
      const cell = row.insertCell();
      if (css) cell.className = css;
      if (field instanceof Node) cell.append(field);
      else {
        cell.textContent = field ?? '—';
        cell.title = cell.textContent;
      }
    }
  }
  target.replaceChildren(root);
}

export function pick(label, action, title = '') {
  const button = el('button',label,'table-action');
  button.type = 'button';
  button.title = title;
  button.setAttribute('aria-pressed','false');
  button.addEventListener('click', () => {
    for (const sibling of button.closest('tbody').querySelectorAll('[aria-pressed]')) sibling.setAttribute('aria-pressed','false');
    button.setAttribute('aria-pressed','true');
    action();
  });
  return button;
}

export function jump(label, route, params) {
  const link = el('a',label,'table-action');
  link.href = `${route}?${new URLSearchParams(params)}`;
  return link;
}

export function fault(target, error) {
  target.replaceChildren(el('p',error.message || '读取失败，请重试。','fault'));
}

export function drill(target, signal) {
  let queued = 0;
  return async (request, draw) => {
    const serial = ++queued;
    target.replaceChildren(el('p','正在查阅原行…','empty'));
    try {
      const data = await request();
      if (!signal.aborted && serial === queued) draw(data);
    } catch (error) {
      if (!signal.aborted && serial === queued) fault(target,error);
    }
  };
}

export const line = (row) => row.line === row.end_line ? row.line : `${row.line}–${row.end_line}`;
