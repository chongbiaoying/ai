// ============================================================
// 配置
// ============================================================
const API = "http://localhost:8000";
const USER_ID_KEY = 'movie_user_id';
const DEFAULT_USER_ID = 'user_001';

function getUserId() {
  return localStorage.getItem(USER_ID_KEY) || DEFAULT_USER_ID;
}
function setUserId(id) {
  const v = String(id || '').trim() || DEFAULT_USER_ID;
  localStorage.setItem(USER_ID_KEY, v);
}

const SESSION_ID = "session_" + Date.now();

// ============================================================
// 主题管理
// ============================================================
const THEME_KEY = 'movie_theme';
const themeToggle = document.getElementById('themeToggle');
const themeIcons = { auto: '🌓', light: '☀️', dark: '🌙' };
const themeLabels = { auto: '跟随系统', light: '浅色', dark: '深色' };

function getThemeMode() {
  return localStorage.getItem(THEME_KEY) || 'auto';
}

function applyTheme(mode) {
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const effective = mode === 'auto' ? (systemDark ? 'dark' : 'light') : mode;
  document.documentElement.setAttribute('data-theme', effective);
  document.documentElement.setAttribute('data-theme-mode', mode);
  themeToggle.textContent = themeIcons[mode];
  themeToggle.title = `当前：${themeLabels[mode]}（点击切换）`;
}

themeToggle.addEventListener('click', () => {
  const order = ['auto', 'light', 'dark'];
  const current = getThemeMode();
  const next = order[(order.indexOf(current) + 1) % order.length];
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
});

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
mediaQuery.addEventListener('change', () => {
  if (getThemeMode() === 'auto') applyTheme('auto');
});

applyTheme(getThemeMode());

// ============================================================
// 排序管理
// ============================================================
const SORT_KEY = 'movie_sort';
let sortField = 'default';
let sortOrder = 'desc';

const sortFieldEl = document.getElementById('sortField');
const sortOrderBtn = document.getElementById('sortOrderBtn');

function loadSortSetting() {
  try {
    const saved = JSON.parse(localStorage.getItem(SORT_KEY) || '{}');
    if (['default', 'score', 'year', 'name'].includes(saved.field)) sortField = saved.field;
    if (['asc', 'desc'].includes(saved.order)) sortOrder = saved.order;
  } catch (_) { /* 忽略损坏数据 */ }
  sortFieldEl.value = sortField;
  updateSortOrderBtn();
}

function saveSortSetting() {
  localStorage.setItem(SORT_KEY, JSON.stringify({ field: sortField, order: sortOrder }));
}

function updateSortOrderBtn() {
  sortOrderBtn.textContent = sortOrder === 'asc' ? '↑' : '↓';
  sortOrderBtn.title = sortOrder === 'asc'
    ? '当前：升序（点击切换为降序）'
    : '当前：降序（点击切换为升序）';
}

function applySort(items) {
  if (sortField === 'default' || !Array.isArray(items) || items.length < 2) {
    return items;
  }
  const dir = sortOrder === 'asc' ? 1 : -1;
  const copy = [...items];
  copy.sort((a, b) => {
    if (sortField === 'name') {
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN') * dir;
    }
    const va = Number(a[sortField]) || 0;
    const vb = Number(b[sortField]) || 0;
    return (va - vb) * dir;
  });
  return copy;
}

sortFieldEl.addEventListener('change', () => {
  sortField = sortFieldEl.value;
  saveSortSetting();
  rerenderCurrentData();
});

sortOrderBtn.addEventListener('click', () => {
  sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
  updateSortOrderBtn();
  saveSortSetting();
  rerenderCurrentData();
});

function rerenderCurrentData() {
  if (!lastData.items || lastData.items.length === 0) {
    loadMovies();
    return;
  }
  renderMovies(lastData.items, lastData.paged, lastData.total);
}

// ============================================================
// 搜索历史
// ============================================================
const SEARCH_HISTORY_KEY = 'movie_search_history';
const SEARCH_HISTORY_MAX = 10;

const searchWrapper = document.querySelector('.search-wrapper');
const searchInputEl = document.getElementById('searchInput');
const searchHistoryEl = document.getElementById('searchHistory');
const searchHistoryList = document.getElementById('searchHistoryList');
const searchHistoryClear = document.getElementById('searchHistoryClear');

let historyActiveIndex = -1;

function getSearchHistory() {
  try {
    const arr = JSON.parse(localStorage.getItem(SEARCH_HISTORY_KEY) || '[]');
    return Array.isArray(arr) ? arr.filter(x => typeof x === 'string' && x.trim()) : [];
  } catch (_) {
    return [];
  }
}

function setSearchHistory(arr) {
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(arr.slice(0, SEARCH_HISTORY_MAX)));
}

function addSearchHistory(keyword) {
  const kw = String(keyword || '').trim();
  if (!kw) return;
  const arr = getSearchHistory().filter(x => x !== kw);
  arr.unshift(kw);
  setSearchHistory(arr);
}

function removeSearchHistory(keyword) {
  const arr = getSearchHistory().filter(x => x !== keyword);
  setSearchHistory(arr);
  if (arr.length === 0) hideSearchHistory();
  else renderSearchHistory();
}

function clearSearchHistory() {
  localStorage.removeItem(SEARCH_HISTORY_KEY);
  hideSearchHistory();
}

function showSearchHistory() {
  const arr = getSearchHistory();
  if (arr.length === 0) {
    hideSearchHistory();
    return;
  }
  renderSearchHistory();
  searchHistoryEl.hidden = false;
  historyActiveIndex = -1;
}

function hideSearchHistory() {
  searchHistoryEl.hidden = true;
  historyActiveIndex = -1;
}

function renderSearchHistory() {
  const arr = getSearchHistory();
  if (arr.length === 0) {
    hideSearchHistory();
    return;
  }
  searchHistoryList.innerHTML = '';
  arr.forEach((kw, idx) => {
    const li = document.createElement('li');
    li.className = 'search-history-item';
    li.dataset.index = idx;
    li.dataset.keyword = kw;

    const text = document.createElement('span');
    text.className = 'history-text';
    text.textContent = kw;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'history-remove';
    removeBtn.title = '删除该记录';
    removeBtn.textContent = '×';

    li.addEventListener('click', (e) => {
      if (e.target === removeBtn) return;
      searchInputEl.value = kw;
      hideSearchHistory();
      doSearch();
    });

    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      removeSearchHistory(kw);
    });

    li.appendChild(text);
    li.appendChild(removeBtn);
    searchHistoryList.appendChild(li);
  });
}

function updateActiveHistoryItem() {
  const items = searchHistoryList.querySelectorAll('.search-history-item');
  items.forEach((it, idx) => {
    it.classList.toggle('active', idx === historyActiveIndex);
  });
  if (historyActiveIndex >= 0 && items[historyActiveIndex]) {
    items[historyActiveIndex].scrollIntoView({ block: 'nearest' });
  }
}

searchInputEl.addEventListener('focus', () => {
  setTimeout(showSearchHistory, 0);
});

searchInputEl.addEventListener('keydown', (e) => {
  const panelVisible = !searchHistoryEl.hidden;
  const items = panelVisible
    ? searchHistoryList.querySelectorAll('.search-history-item')
    : [];

  if (panelVisible && items.length > 0) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      historyActiveIndex = (historyActiveIndex + 1) % items.length;
      updateActiveHistoryItem();
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      historyActiveIndex = historyActiveIndex <= 0 ? items.length - 1 : historyActiveIndex - 1;
      updateActiveHistoryItem();
      return;
    }
    if (e.key === 'Enter' && historyActiveIndex >= 0) {
      e.preventDefault();
      const kw = items[historyActiveIndex].dataset.keyword;
      searchInputEl.value = kw;
      hideSearchHistory();
      doSearch();
      return;
    }
  }

  if (e.key === 'Enter') {
    hideSearchHistory();
    doSearch();
  } else if (e.key === 'Escape') {
    hideSearchHistory();
  }
});

document.addEventListener('click', (e) => {
  if (!searchWrapper.contains(e.target)) hideSearchHistory();
});

searchHistoryClear.addEventListener('click', (e) => {
  e.stopPropagation();
  clearSearchHistory();
  toast('已清空搜索历史', 'success');
});

// ============================================================
// 偏好设置
// ============================================================
const prefBtn = document.getElementById('prefBtn');
const prefModal = document.getElementById('prefModal');
const prefUserIdEl = document.getElementById('prefUserId');
const prefFavoriteTypeEl = document.getElementById('prefFavoriteType');
const prefMinScoreEl = document.getElementById('prefMinScore');
const prefMinScoreValueEl = document.getElementById('prefMinScoreValue');
const prefSaveBtn = document.getElementById('prefSaveBtn');

function openPref() {
  prefModal.classList.add('active');
  prefUserIdEl.value = getUserId();
  prefFavoriteTypeEl.value = '';
  prefMinScoreEl.value = '7';
  prefMinScoreValueEl.textContent = '7.0';
  prefSaveBtn.disabled = false;
  prefSaveBtn.textContent = '保存';
  loadMemoryForUser(getUserId());
}

function closePref() {
  prefModal.classList.remove('active');
}

async function loadMemoryForUser(userId) {
  prefSaveBtn.disabled = true;
  prefSaveBtn.textContent = '加载中…';
  try {
    const res = await fetch(`${API}/ai/memory/${encodeURIComponent(userId)}`);
    if (res.status === 404) {
      prefSaveBtn.disabled = false;
      prefSaveBtn.textContent = '保存';
      return;
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `加载失败 (${res.status})`);
    }
    const data = await res.json();
    if (data.favorite_type != null) {
      prefFavoriteTypeEl.value = data.favorite_type;
    }
    if (data.preferred_min_score != null) {
      const v = Number(data.preferred_min_score);
      prefMinScoreEl.value = String(v);
      prefMinScoreValueEl.textContent = v.toFixed(1);
    }
  } catch (err) {
    toast(err.message || '加载偏好失败', 'error');
  } finally {
    prefSaveBtn.disabled = false;
    prefSaveBtn.textContent = '保存';
  }
}

prefMinScoreEl.addEventListener('input', () => {
  const v = parseFloat(prefMinScoreEl.value) || 0;
  prefMinScoreValueEl.textContent = v.toFixed(1);
});

prefUserIdEl.addEventListener('blur', () => {
  const uid = prefUserIdEl.value.trim();
  if (uid) loadMemoryForUser(uid);
});

prefBtn.addEventListener('click', openPref);

prefSaveBtn.addEventListener('click', async () => {
  const uid = prefUserIdEl.value.trim() || DEFAULT_USER_ID;
  const favorite_type = prefFavoriteTypeEl.value.trim();
  const preferred_min_score = parseFloat(prefMinScoreEl.value);

  if (isNaN(preferred_min_score) || preferred_min_score < 0 || preferred_min_score > 10) {
    toast('评分需在 0-10 之间', 'warning');
    return;
  }

  prefSaveBtn.disabled = true;
  prefSaveBtn.textContent = '保存中…';

  try {
    const res = await fetch(`${API}/ai/memory/${encodeURIComponent(uid)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        favorite_type: favorite_type || null,
        preferred_min_score,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || '保存失败');
    }
    setUserId(uid);
    toast('偏好已保存', 'success');
    closePref();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    prefSaveBtn.disabled = false;
    prefSaveBtn.textContent = '保存';
  }
});

// ============================================================
// 状态
// ============================================================
let currentPage = 1;
let pageSize = 6;
let searchMode = null;
let editingId = null;
let detailMovie = null;
let isLoading = false;
let currentSearchKeyword = '';   // 当前搜索关键词，用于高亮

const lastData = { items: [], paged: false, total: 0 };

// ============================================================
// Toast
// ============================================================
function toast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const icons = { success: '✓', error: '✕', warning: '!', info: 'i' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || '✓'}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 350);
  }, 2800);
}

// ============================================================
// 确认弹窗
// ============================================================
function confirmDialog({ title = '确认操作', message = '', confirmText = '确定', icon = '⚠️' } = {}) {
  return new Promise(resolve => {
    const overlay = document.getElementById('confirmModal');
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMsg').textContent = message;
    document.getElementById('confirmIcon').textContent = icon;
    const okBtn = document.getElementById('confirmOk');
    const cancelBtn = document.getElementById('confirmCancel');
    okBtn.textContent = confirmText;
    overlay.classList.add('active');

    function cleanup(result) {
      overlay.classList.remove('active');
      okBtn.onclick = null;
      cancelBtn.onclick = null;
      overlay.onclick = null;
      resolve(result);
    }
    okBtn.onclick = () => cleanup(true);
    cancelBtn.onclick = () => cleanup(false);
    overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };
  });
}

// ============================================================
// 骨架屏
// ============================================================
function showSkeleton() {
  const grid = document.getElementById('movieGrid');
  grid.innerHTML = '';
  document.getElementById('emptyHint').style.display = 'none';
  for (let i = 0; i < pageSize; i++) {
    const s = document.createElement('div');
    s.className = 'skeleton-card';
    s.innerHTML = `
      <div class="skeleton-line w-70"></div>
      <div class="skeleton-line w-40"></div>
      <div class="skeleton-line w-90"></div>
      <div class="skeleton-line w-40"></div>
    `;
    grid.appendChild(s);
  }
}

// ============================================================
// 加载电影列表
// ============================================================
async function loadMovies() {
  if (isLoading) return;
  isLoading = true;
  showSkeleton();

  try {
    let items, paged, total;

    if (searchMode === 'search') {
      const kw = document.getElementById('searchInput').value.trim();
      items = await fetchJSON(`${API}/movies/search?keyword=${encodeURIComponent(kw)}`);
      paged = false;
      total = items.length;
    } else if (searchMode === 'filter') {
      const kw = document.getElementById('searchInput').value.trim();
      const score = document.getElementById('filterScore').value;
      const year = document.getElementById('filterYear').value;
      const params = new URLSearchParams();
      if (kw) params.append('keyword', kw);
      if (score) params.append('min_score', score);
      if (year) params.append('year', year);
      items = await fetchJSON(`${API}/movies/filter?${params.toString()}`);
      paged = false;
      total = items.length;
    } else {
      const data = await fetchJSON(`${API}/movies?page=${currentPage}&page_size=${pageSize}`);
      items = data.items;
      paged = true;
      total = data.total;
    }

    lastData.items = items;
    lastData.paged = paged;
    lastData.total = total;

    renderMovies(items, paged, total);
  } catch (err) {
    toast(err.message || '加载失败', 'error');
    document.getElementById('movieGrid').innerHTML = '';
    document.getElementById('emptyHint').style.display = 'block';
  } finally {
    isLoading = false;
  }
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败 (${res.status})`);
  }
  return res.json();
}

// ============================================================
// 关键词高亮
// 先定位原文匹配位置，再对每段分别 escape，避免 XSS
// ============================================================
function highlightKeyword(text, keyword) {
  const raw = String(text == null ? '' : text);
  const kw = String(keyword == null ? '' : keyword).trim();
  if (!kw) return escapeHtml(raw);

  const lowerRaw = raw.toLowerCase();
  const lowerKw = kw.toLowerCase();
  const kwLen = kw.length;

  let result = '';
  let cursor = 0;

  while (cursor <= raw.length) {
    const idx = lowerRaw.indexOf(lowerKw, cursor);
    if (idx === -1) {
      result += escapeHtml(raw.slice(cursor));
      break;
    }
    // 匹配前的普通文本
    result += escapeHtml(raw.slice(cursor, idx));
    // 匹配的部分
    result += `<mark class="hl">${escapeHtml(raw.slice(idx, idx + kwLen))}</mark>`;
    cursor = idx + kwLen;
  }

  return result;
}

// ============================================================
// 渲染电影卡片
// ============================================================
function renderMovies(rawItems, paged, total) {
  const grid = document.getElementById('movieGrid');
  const hint = document.getElementById('emptyHint');
  const countEl = document.getElementById('totalCount');

  const items = applySort(rawItems);
  grid.innerHTML = '';

  if (!items || items.length === 0) {
    hint.style.display = 'flex';
    document.getElementById('pageInfo').innerText = '';
    countEl.textContent = '共 0 部';
    document.getElementById('prevBtn').disabled = true;
    document.getElementById('nextBtn').disabled = true;
    return;
  }
  hint.style.display = 'none';

  // 只有搜索模式下才高亮
  const highlightKw = (searchMode === 'search') ? currentSearchKeyword : '';

  items.forEach(m => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h3>${highlightKeyword(m.name, highlightKw)}</h3>
      <div class="score">⭐ ${m.score}</div>
      <div class="meta">
        <span>📅 ${m.year}</span>
        ${m.type ? `<span class="tag">${escapeHtml(m.type)}</span>` : ''}
      </div>
      <div class="actions">
        <button class="btn-edit">编辑</button>
        <button class="btn-del">删除</button>
      </div>
    `;
    card.onclick = () => openDetail(m);
    card.querySelector('.btn-edit').onclick = (e) => { e.stopPropagation(); openEdit(m); };
    card.querySelector('.btn-del').onclick = (e) => { e.stopPropagation(); deleteMovie(m.id, m.name); };
    grid.appendChild(card);
  });

  if (paged) {
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    document.getElementById('pageInfo').innerText = `第 ${currentPage} / ${totalPages} 页`;
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    countEl.textContent = `共 ${total} 部`;
  } else {
    document.getElementById('pageInfo').innerText = `共 ${items.length} 条结果`;
    document.getElementById('prevBtn').disabled = true;
    document.getElementById('nextBtn').disabled = true;
    countEl.textContent = `筛选结果 ${items.length} 部`;
  }
}

// ============================================================
// 分页
// ============================================================
function changePage(delta) {
  currentPage = Math.max(1, currentPage + delta);
  loadMovies();
}

// ============================================================
// 搜索 / 过滤
// ============================================================
function doSearch() {
  const kw = document.getElementById('searchInput').value.trim();
  const score = document.getElementById('filterScore').value;
  const year = document.getElementById('filterYear').value;

  if (score || year) {
    searchMode = 'filter';
    currentSearchKeyword = '';   // 过滤模式不高亮
  } else if (kw) {
    searchMode = 'search';
    currentSearchKeyword = kw;   // 搜索模式记录关键词用于高亮
  } else {
    searchMode = null;
    currentSearchKeyword = '';
  }

  if (kw) addSearchHistory(kw);

  hideSearchHistory();
  currentPage = 1;
  loadMovies();
}

function resetSearch() {
  document.getElementById('searchInput').value = '';
  document.getElementById('filterScore').value = '';
  document.getElementById('filterYear').value = '';
  searchMode = null;
  currentSearchKeyword = '';
  currentPage = 1;
  loadMovies();
}

document.getElementById('filterScore').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});
document.getElementById('filterYear').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

// ============================================================
// 电影详情弹窗
// ============================================================
function openDetail(movie) {
  detailMovie = movie;
  document.getElementById('detailName').textContent = movie.name || '—';
  document.getElementById('detailScore').textContent = movie.score != null ? `${movie.score} / 10` : '—';
  document.getElementById('detailYear').textContent = movie.year || '—';
  document.getElementById('detailType').textContent = movie.type || '未分类';

  const poster = document.getElementById('detailPoster');
  poster.textContent = pickPosterEmoji(movie.type);

  document.getElementById('detailModal').classList.add('active');
}

function closeDetail() {
  document.getElementById('detailModal').classList.remove('active');
  detailMovie = null;
}

document.getElementById('detailEditBtn').onclick = () => {
  if (!detailMovie) return;
  const movie = detailMovie;
  closeDetail();
  openEdit(movie);
};

function pickPosterEmoji(type) {
  if (!type) return '🎬';
  const t = String(type);
  if (t.includes('科幻')) return '🚀';
  if (t.includes('爱情')) return '💕';
  if (t.includes('恐怖') || t.includes('惊悚')) return '👻';
  if (t.includes('喜剧')) return '😂';
  if (t.includes('动作')) return '💥';
  if (t.includes('动画')) return '🐭';
  if (t.includes('纪录')) return '📽️';
  if (t.includes('战争')) return '⚔️';
  if (t.includes('悬疑') || t.includes('犯罪')) return '🔍';
  if (t.includes('奇幻')) return '🧙';
  if (t.includes('剧情')) return '🎭';
  return '🎬';
}

// ============================================================
// 新增 / 编辑
// ============================================================
function openCreate() {
  editingId = null;
  document.getElementById('modalTitle').innerText = '新增电影';
  document.getElementById('mName').value = '';
  document.getElementById('mScore').value = '';
  document.getElementById('mYear').value = '';
  document.getElementById('mType').value = '';
  document.getElementById('modal').classList.add('active');
  setTimeout(() => document.getElementById('mName').focus(), 100);
}

function openEdit(movie) {
  editingId = movie.id;
  document.getElementById('modalTitle').innerText = '编辑电影';
  document.getElementById('mName').value = movie.name;
  document.getElementById('mScore').value = movie.score;
  document.getElementById('mYear').value = movie.year;
  document.getElementById('mType').value = movie.type || '';
  document.getElementById('modal').classList.add('active');
  setTimeout(() => document.getElementById('mName').focus(), 100);
}

function closeModal() {
  document.getElementById('modal').classList.remove('active');
}

async function submitModal() {
  const payload = {
    name: document.getElementById('mName').value.trim(),
    score: parseFloat(document.getElementById('mScore').value),
    year: parseInt(document.getElementById('mYear').value),
    type: document.getElementById('mType').value.trim() || '未分类',
  };

  if (!payload.name) { toast('请填写电影名', 'warning'); return; }
  if (isNaN(payload.score) || payload.score < 0 || payload.score > 10) {
    toast('评分必须是 0-10 之间的数字', 'warning'); return;
  }
  if (isNaN(payload.year) || payload.year < 1888) {
    toast('年份无效', 'warning'); return;
  }

  try {
    const url = editingId === null ? `${API}/movies` : `${API}/movies/${editingId}`;
    const method = editingId === null ? 'POST' : 'PUT';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || '保存失败');
    }
    closeModal();
    toast(editingId === null ? '新增成功' : '更新成功', 'success');
    loadMovies();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ============================================================
// 删除
// ============================================================
async function deleteMovie(id, name) {
  const ok = await confirmDialog({
    icon: '🗑️',
    title: '删除电影',
    message: `确定要删除《${name}》吗？此操作不可撤销。`,
    confirmText: '删除',
  });
  if (!ok) return;

  try {
    const res = await fetch(`${API}/movies/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || '删除失败');
    }
    toast('已删除', 'success');
    loadMovies();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ============================================================
// Markdown 渲染
// ============================================================
function renderMarkdown(text) {
  if (!text) return '';

  let html = escapeHtml(text);

  const codeBlocks = [];
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre class="md-pre"><code>${code.replace(/^\n+|\n+$/g, '')}</code></pre>`);
    return `\x00CB${idx}\x00`;
  });

  const inlineCodes = [];
  html = html.replace(/`([^`\n]+)`/g, (_, code) => {
    const idx = inlineCodes.length;
    inlineCodes.push(`<code class="md-code">${code}</code>`);
    return `\x00IC${idx}\x00`;
  });

  function inline(s) {
    s = s.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?=[^*\w]|$)/g, '$1<em>$2</em>');
    return s;
  }

  const lines = html.split('\n');
  const out = [];
  let listType = null;

  const closeList = () => {
    if (listType) {
      out.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line === '') {
      closeList();
      continue;
    }

    let m;

    if ((m = line.match(/^###\s+(.+)$/))) {
      closeList();
      out.push(`<h4>${inline(m[1])}</h4>`);
      continue;
    }
    if ((m = line.match(/^##\s+(.+)$/))) {
      closeList();
      out.push(`<h3>${inline(m[1])}</h3>`);
      continue;
    }
    if ((m = line.match(/^#\s+(.+)$/))) {
      closeList();
      out.push(`<h2>${inline(m[1])}</h2>`);
      continue;
    }

    if ((m = line.match(/^\d+\.\s+(.+)$/))) {
      if (listType !== 'ol') {
        closeList();
        out.push('<ol>');
        listType = 'ol';
      }
      out.push(`<li>${inline(m[1])}</li>`);
      continue;
    }

    if ((m = line.match(/^[-*]\s+(.+)$/))) {
      if (listType !== 'ul') {
        closeList();
        out.push('<ul>');
        listType = 'ul';
      }
      out.push(`<li>${inline(m[1])}</li>`);
      continue;
    }

    if ((m = line.match(/^>\s*(.+)$/))) {
      closeList();
      out.push(`<blockquote>${inline(m[1])}</blockquote>`);
      continue;
    }

    closeList();
    out.push(`<p>${inline(line)}</p>`);
  }
  closeList();

  let result = out.join('');
  result = result.replace(/\x00CB(\d+)\x00/g, (_, i) => codeBlocks[Number(i)]);
  result = result.replace(/\x00IC(\d+)\x00/g, (_, i) => inlineCodes[Number(i)]);

  return result;
}

// ============================================================
// AI 聊天
// ============================================================
let isChatting = false;

async function sendChat() {
  if (isChatting) return;
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  appendMsg(text, 'user');
  appendTyping();
  isChatting = true;

  try {
    const res = await fetch(`${API}/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: SESSION_ID,
        user_id: getUserId(),
        message: text,
      }),
    });
    removeTyping();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      appendMsg('（AI 服务暂时不可用：' + (err.detail || res.status) + '）', 'ai');
      return;
    }
    const data = await res.json();
    appendMsg(data.answer, 'ai');
  } catch (err) {
    removeTyping();
    appendMsg('（网络错误，请稍后再试）', 'ai');
  } finally {
    isChatting = false;
  }
}

function appendMsg(text, role) {
  const box = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  if (role === 'ai') {
    div.innerHTML = renderMarkdown(text);
  } else {
    div.textContent = text;
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function appendTyping() {
  const box = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg ai typing';
  div.id = 'typingIndicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// ============================================================
// 快捷提问
// ============================================================
document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (isChatting) return;
    const prompt = btn.dataset.prompt;
    if (!prompt) return;
    document.getElementById('chatInput').value = prompt;
    sendChat();
  });
});

// ============================================================
// 工具
// ============================================================
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeModal();
    closeDetail();
    closePref();
    hideSearchHistory();
    const confirmOverlay = document.getElementById('confirmModal');
    if (confirmOverlay.classList.contains('active')) {
      confirmOverlay.classList.remove('active');
      document.getElementById('confirmCancel').onclick?.();
    }
  }
});

// ============================================================
// 启动
// ============================================================
loadSortSetting();
loadMovies();