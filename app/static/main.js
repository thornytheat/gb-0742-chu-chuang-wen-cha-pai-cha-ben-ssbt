import {choose, q, put, stamp} from './paper.js';
import {stages} from './stages.js';

const stage = document.body.dataset.stage;
const sample = q('#sample');
const cabinet = q('#cabinet');
const runButton = q('#run');
const replayButton = q('#rerun');
const printButton = q('#print');
const download = q('#export');
const content = q('#stage-content');
const page = {run:null, cabinet:null, abort:null, loading:false};

async function request(path, settings) {
  const response = await fetch(path,settings);
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.message || (response.status === 422 ? '参数格式有误。' : `无法读取 HTTP ${response.status}`));
  return data;
}

function message(note, bad=false) {
  const box = q('#feedback');
  box.classList.toggle('error',bad);
  box.hidden = !note;
  box.textContent = note ?? '';
}

function enable() {
  sample.disabled = page.loading || !sample.options.length;
  runButton.disabled = sample.disabled;
  replayButton.disabled = page.loading || !page.run;
  cabinet.disabled = page.loading || !page.run;
  printButton.disabled = page.loading || !page.run;
}

function viewKey(run, cabinetId, params) {
  params.set('run',run.id);
  params.set('cabinet',cabinetId);
  history.replaceState(null,'',`${location.pathname}?${params}`);
  for (const link of document.querySelectorAll('[data-section]')) {
    const to = new URL(link.href);
    to.search = new URLSearchParams({run:run.id,cabinet:cabinetId});
    link.href = to;
  }
}

async function render(run, requested, records, params = new URLSearchParams()) {
  page.abort?.abort();
  page.abort = new AbortController();
  const {signal} = page.abort;
  const cabinetId = run.cabinets.some((item) => item.id === requested) ? requested : run.cabinets[0].id;
  const get = (path) => request(path,{signal});
  const base = `/api/runs/${run.id}`;
  content.setAttribute('aria-busy','true');
  content.hidden = true;
  put('#statusbar','正在核取归卷');
  const audit = await get(`${base}/audit`);
  await stages[stage]({get,base,run,cabinet:cabinetId,history:records,audit,signal,params});
  page.run = run;
  page.cabinet = cabinetId;
  choose(cabinet,run.cabinets.map((item) => [item.id,item.id]),cabinetId);
  viewKey(run,cabinetId,params);
  put('#shift-caption',`${run.shift} / ${run.label}`);
  put('#policy',run.policy);
  put('#shift-window',`${stamp(run.window[0])} — ${stamp(run.window[1])}`);
  put('#generated',`归卷 ${stamp(run.created)}`);
  q('#generated').dateTime = run.created;
  for (const key of ['expected','stable','abnormal','missing']) put(`#${key}`,audit.hours[key]);
  put('#isolated',audit.row_audit.isolated);
  put('#tolerance',`${run.tolerance_seconds} s`);
  download.href = `${base}/export`;
  download.hidden = false;
  put('#statusbar',`${run.id.slice(0,12)} · ${audit.hours.balanced ? '柜时账一致' : '柜时账有差异'}`);
  content.hidden = false;
  content.setAttribute('aria-busy','false');
}

async function go(action) {
  page.loading = true;
  enable();
  try {
    await action();
  } catch (error) {
    message(error.message,true);
    if (content.getAttribute('aria-busy') === 'true') {
      content.setAttribute('aria-busy','false');
      put('#statusbar','载入失败');
    }
  } finally {
    page.loading = false;
    enable();
  }
}

runButton.addEventListener('click', () => go(async () => {
  message('正在排查…');
  const outcome = await request('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sample:sample.value})});
  await render(outcome.manifest,page.cabinet,await request('/api/runs'));
  message(outcome.reused ? '相同输入已归卷。' : '新班次已归卷。');
}));
replayButton.addEventListener('click', () => go(async () => {
  message('正在按原档复算…');
  const outcome = await request(`/api/runs/${page.run.id}/rerun`,{method:'POST'});
  message(`复算一致 · ${outcome.manifest.result_sha256.slice(0,12)}`);
}));
printButton.addEventListener('click', () => window.print());
cabinet.addEventListener('change', () => go(async () => {
  message('');
  await render(page.run,cabinet.value,await request('/api/runs'));
}));

go(async () => {
  const params = new URLSearchParams(location.search);
  const [records, catalog] = await Promise.all([request('/api/runs'),request('/api/samples')]);
  const run = params.has('run') ? records.find((item) => item.id === params.get('run')) : records[0];
  choose(sample,catalog.map((item) => [item.id,item.label]),run?.sample ?? 'shift');
  if (run) await render(run,params.get('cabinet'),records,params);
  else {
    put('#statusbar','待运行');
    content.setAttribute('aria-busy','false');
    message(params.has('run') ? '归卷未找到，请选择样例。' : '选择样例后运行。');
  }
});
