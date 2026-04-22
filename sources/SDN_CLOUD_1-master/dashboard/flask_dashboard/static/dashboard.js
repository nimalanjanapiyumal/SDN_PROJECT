
function palette(i) {
  const colors = ['#5b8cff', '#7cf0ff', '#2ed9a6', '#f7c75c', '#ff6b81', '#b18cff'];
  return colors[i % colors.length];
}

function clearCanvas(ctx, canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  return {w: rect.width, h: rect.height};
}

function drawAxes(ctx, w, h, maxValue, xLabels) {
  const pad = {l: 46, r: 18, t: 18, b: 42};
  ctx.strokeStyle = 'rgba(255,255,255,0.14)';
  ctx.fillStyle = '#9db0da';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + ((h - pad.t - pad.b) * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    const v = Math.round(maxValue * (1 - i / 4));
    ctx.fillText(String(v), 10, y + 4);
  }
  const innerW = w - pad.l - pad.r;
  xLabels.forEach((lab, idx) => {
    const x = pad.l + innerW * (idx + 0.5) / Math.max(1, xLabels.length);
    ctx.fillText(lab, x - 8, h - 16);
  });
  return pad;
}

function drawGroupedBars(canvas, payload, seriesKeys, seriesNames) {
  const ctx = canvas.getContext('2d');
  const {w, h} = clearCanvas(ctx, canvas);
  const labels = payload.backend_labels || [];
  const datasets = seriesKeys.map(k => payload[k] || []);
  const maxValue = Math.max(100, ...datasets.flat(), 1);
  const pad = drawAxes(ctx, w, h, maxValue, labels);
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const groupWidth = innerW / Math.max(labels.length, 1);
  const barWidth = Math.min(24, (groupWidth - 18) / Math.max(1, datasets.length));
  datasets.forEach((data, sIdx) => {
    ctx.fillStyle = palette(sIdx);
    data.forEach((value, idx) => {
      const x = pad.l + idx * groupWidth + 10 + sIdx * barWidth;
      const barH = (value / maxValue) * innerH;
      ctx.fillRect(x, h - pad.b - barH, barWidth - 4, barH);
    });
  });
  seriesNames.forEach((name, i) => {
    ctx.fillStyle = palette(i);
    ctx.fillRect(w - 160, 20 + i * 18, 12, 12);
    ctx.fillStyle = '#dfe8ff';
    ctx.fillText(name, w - 140, 30 + i * 18);
  });
}

function drawSingleBars(canvas, labels, values, title) {
  const ctx = canvas.getContext('2d');
  const {w, h} = clearCanvas(ctx, canvas);
  const maxValue = Math.max(...values, 10);
  const pad = drawAxes(ctx, w, h, maxValue, labels);
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const barWidth = Math.min(42, innerW / Math.max(1, labels.length) - 18);
  values.forEach((value, idx) => {
    const groupX = pad.l + innerW * (idx + 0.5) / Math.max(1, labels.length);
    const x = groupX - barWidth / 2;
    const barH = (value / maxValue) * innerH;
    ctx.fillStyle = palette(idx);
    ctx.fillRect(x, h - pad.b - barH, barWidth, barH);
  });
}

function initCharts() {
  document.querySelectorAll('.chart-canvas').forEach((canvas) => {
    const chartType = canvas.dataset.chart;
    let payload = {};
    try { payload = JSON.parse(canvas.dataset.payload || '{}'); } catch (e) {}
    if (chartType === 'grouped-bars') {
      drawGroupedBars(canvas, payload, ['cpu','mem','bw'], ['CPU %','Memory %','Bandwidth %']);
    } else if (chartType === 'dual-bars') {
      const ctxPayload = {backend_labels: payload.backend_labels || [], throughput: payload.throughput || [], active_conn: payload.active_conn || []};
      drawGroupedBars(canvas, ctxPayload, ['throughput','active_conn'], ['Throughput Mbps','Active connections']);
    } else if (chartType === 'weights') {
      drawSingleBars(canvas, payload.backend_labels || [], payload.weights || [], 'Weights');
    } else if (chartType === 'testing-throughput') {
      drawSingleBars(canvas, payload.http_labels || [], payload.http_throughput || [], 'HTTP req/s');
    } else if (chartType === 'testing-p95') {
      drawSingleBars(canvas, payload.http_labels || [], payload.http_p95 || [], 'HTTP p95 ms');
    } else if (chartType === 'testing-sla') {
      drawSingleBars(canvas, payload.http_labels || [], payload.http_sla || [], 'SLA %');
    } else if (chartType === 'testing-iperf') {
      drawSingleBars(canvas, payload.iperf_labels || [], payload.iperf_throughput || [], 'iperf Mbps');
    }
  });
}

window.addEventListener('load', initCharts);
window.addEventListener('resize', initCharts);
