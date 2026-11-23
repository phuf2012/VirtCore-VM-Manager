const $ = (s) => document.querySelector(s);
const list = $('#vm-list');
let toastTimer;

async function api(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function esc(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function toast(message) { const el = $('#toast'); el.textContent = message; el.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3000); }

function renderVMs(vms) {
  const running = vms.filter(vm => vm.state === 'running').length;
  $('#stat-total').textContent = vms.length;
  $('#stat-running').textContent = running;
  $('#nav-count').textContent = vms.length;
  $('#section-count').textContent = vms.length;
  if (!vms.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-icon">▣</div><strong>Your virtual machines will show up here</strong><p>Create your first VM to get started with VirtCore.</p></div>';
    return;
  }
  list.innerHTML = vms.map(vm => {
    const state = vm.state || 'unknown';
    const action = state === 'running' ? '<button class="vm-action" data-action="shutdown">Shut down</button><button class="vm-action" data-action="pause">Pause</button>' : state === 'paused' ? '<button class="vm-action" data-action="resume">Resume</button>' : '<button class="vm-action" data-action="start">Start</button>';
    return `<article class="vm-row" data-name="${esc(vm.name)}"><div class="vm-icon">▣</div><div class="vm-info"><strong>${esc(vm.name)}</strong><small>${esc(vm.cpus)} vCPU · ${esc(vm.memory)} memory</small></div><span class="vm-state ${state === 'running' ? 'running' : ''}">${esc(state.toUpperCase())}</span><div class="vm-actions">${action}<button class="vm-action danger" data-action="delete">Delete</button></div></article>`;
  }).join('');
}

async function refresh() {
  const button = $('#refresh'); button.classList.add('spinning');
  try {
    const status = await api('/api/status');
    $('#host-state').textContent = status.connected ? 'Connected to KVM' : 'Connection unavailable';
    $('#host-status').textContent = status.connected ? 'Connected' : 'Unavailable';
    $('#host-uri').textContent = status.uri || 'Local hypervisor';
    $('#host-indicator').classList.toggle('online', status.connected);
    $('#connection-notice').hidden = status.connected;
    if (!status.connected) $('#connection-error').textContent = status.error || 'Check that libvirt is installed and your user can access the system connection.';
    const result = await api('/api/vms');
    renderVMs(result.vms || []);
  } catch (error) {
    $('#host-state').textContent = 'Connection unavailable';
    $('#host-status').textContent = 'Unavailable';
    $('#host-indicator').classList.remove('online');
    $('#connection-notice').hidden = false;
    $('#connection-error').textContent = error.message;
    renderVMs([]);
  } finally { button.classList.remove('spinning'); }
}

function openModal() { $('#modal').hidden = false; $('#form-error').hidden = true; $('#create-form').elements.name.focus(); }
function closeModal() { $('#modal').hidden = true; }
$('#create-open').addEventListener('click', openModal);
$('#create-open-2').addEventListener('click', openModal);
document.querySelectorAll('.close-modal').forEach(button => button.addEventListener('click', closeModal));
$('#modal').addEventListener('click', event => { if (event.target === $('#modal')) closeModal(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeModal(); });
$('#refresh').addEventListener('click', refresh);
$('#notice-refresh').addEventListener('click', refresh);

$('#create-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = $('#create-submit'); const errorBox = $('#form-error');
  button.disabled = true; button.textContent = 'Creating…'; errorBox.hidden = true;
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    await api('/api/vms', { method: 'POST', body: JSON.stringify(data) });
    closeModal(); event.currentTarget.reset(); event.currentTarget.elements.memory.value = 4096; event.currentTarget.elements.cpus.value = 2; event.currentTarget.elements.disk.value = 32;
    toast(`Created ${data.name}`); await refresh();
  } catch (error) { errorBox.textContent = error.message; errorBox.hidden = false; }
  finally { button.disabled = false; button.innerHTML = 'Create VM <span class="arrow">→</span>'; }
});

list.addEventListener('click', async event => {
  const button = event.target.closest('[data-action]'); if (!button) return;
  const row = button.closest('.vm-row'); const name = row.dataset.name; const action = button.dataset.action;
  if (action === 'delete' && !window.confirm(`Delete ${name} and its virtual disk? This cannot be undone.`)) return;
  button.disabled = true;
  try { await api(`/api/vms/${encodeURIComponent(name)}/${action}`, { method: 'POST', body: '{}' }); toast(`${name}: ${action} complete`); await refresh(); }
  catch (error) { toast(error.message); button.disabled = false; }
});

refresh();
setInterval(refresh, 10000);
