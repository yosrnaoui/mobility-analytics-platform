/**
 * Mobility Analytics Platform — app.js
 * Gère : upload, démo, carte Leaflet, liste des trajectoires, toasts
 */

'use strict';

// ── État global ──────────────────────────────────────────────────────────────
let map = null;
let currentLayers = { path: null, markers: [] };
let selectedFile = null;
let activeCardId = null;

// ── Initialisation ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initUpload();
  loadTrajectoryList();

  document.getElementById('loadDemoBtn').addEventListener('click', loadDemo);
  document.getElementById('refreshList').addEventListener('click', loadTrajectoryList);
  document.getElementById('cancelUpload').addEventListener('click', resetUploadForm);
  document.getElementById('submitUpload').addEventListener('click', submitUpload);
});

// ── Carte Leaflet ────────────────────────────────────────────────────────────
function initMap() {
  map = L.map('leafletMap', { zoomControl: true }).setView([36.8, 10.18], 11);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap contributors © CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);
}

function renderTrajectoryOnMap(points) {
  // Nettoyer les couches précédentes
  if (currentLayers.path) map.removeLayer(currentLayers.path);
  currentLayers.markers.forEach(m => map.removeLayer(m));
  currentLayers.markers = [];

  if (!points || points.length === 0) return;

  const latlngs = points.map(p => [p.latitude, p.longitude]);

  // Tracé principal
  currentLayers.path = L.polyline(latlngs, {
    color: '#3b82f6',
    weight: 3,
    opacity: 0.85,
  }).addTo(map);

  // Marqueurs
  points.forEach((p, i) => {
    const isAnomaly = p.is_anomaly;
    const color = isAnomaly ? '#ef4444' : '#3b82f6';
    const size = isAnomaly ? 10 : 6;

    const icon = L.divIcon({
      html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,.6);"></div>`,
      className: '',
      iconSize: [size, size],
    });

    const marker = L.marker([p.latitude, p.longitude], { icon });

    const speedTxt = p.speed_kmh != null ? `${p.speed_kmh.toFixed(1)} km/h` : '—';
    const popupContent = `
      <div style="font-family:sans-serif;font-size:13px;line-height:1.6;">
        <strong>Point #${i + 1}</strong><br/>
        📍 ${p.latitude.toFixed(5)}, ${p.longitude.toFixed(5)}<br/>
        🚀 Vitesse : ${speedTxt}<br/>
        🕐 ${new Date(p.timestamp).toLocaleString('fr-FR')}
        ${isAnomaly ? `<br/>⚠️ <span style="color:#ef4444;font-weight:600;">${p.anomaly_reason}</span>` : ''}
      </div>
    `;
    marker.bindPopup(popupContent);

    if (isAnomaly || i === 0 || i === points.length - 1) {
      marker.addTo(map);
      currentLayers.markers.push(marker);
    } else {
      marker.addTo(map);
      currentLayers.markers.push(marker);
    }
  });

  map.fitBounds(currentLayers.path.getBounds(), { padding: [30, 30] });

  // Scroll vers la carte
  document.getElementById('map').scrollIntoView({ behavior: 'smooth' });
}

// ── Upload ───────────────────────────────────────────────────────────────────
function initUpload() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  dropZone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFileSelected(fileInput.files[0]);
  });

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelected(file);
  });
}

function handleFileSelected(file) {
  selectedFile = file;
  document.getElementById('trajName').value = file.name.replace(/\.[^.]+$/, '');
  document.getElementById('uploadForm').style.display = 'flex';
  document.getElementById('dropZone').style.display = 'none';
}

function resetUploadForm() {
  selectedFile = null;
  document.getElementById('uploadForm').style.display = 'none';
  document.getElementById('dropZone').style.display = 'flex';
  document.getElementById('trajName').value = '';
  document.getElementById('trajDesc').value = '';
  document.getElementById('fileInput').value = '';
}

async function submitUpload() {
  if (!selectedFile) return;

  const name = document.getElementById('trajName').value.trim() || selectedFile.name;
  const desc = document.getElementById('trajDesc').value.trim();

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('name', name);
  formData.append('description', desc);

  setUploadLoading(true);

  try {
    const res = await fetch('/api/trajectories/upload/', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Erreur inconnue');

    showStats(data.metrics);
    renderTrajectoryOnMap(data.points);
    showToast(`✅ "${name}" analysée avec succès !`, 'success');
    resetUploadForm();
    loadTrajectoryList();
  } catch (err) {
    showToast(`❌ ${err.message}`, 'error');
  } finally {
    setUploadLoading(false);
  }
}

function setUploadLoading(loading) {
  document.getElementById('uploadBtnText').textContent = loading ? 'Analyse...' : 'Analyser';
  document.getElementById('uploadSpinner').style.display = loading ? 'inline-block' : 'none';
  document.getElementById('submitUpload').disabled = loading;
}

// ── Démo ─────────────────────────────────────────────────────────────────────
async function loadDemo() {
  document.getElementById('loadDemoBtn').textContent = 'Chargement...';
  document.getElementById('loadDemoBtn').disabled = true;

  try {
    const res = await fetch('/api/trajectories/demo/');
    const data = await res.json();
    showStats(data.metrics);
    renderTrajectoryOnMap(data.points);
    showToast('🗺️ Trajectoire démo chargée !', 'success');
  } catch (err) {
    showToast('❌ Impossible de charger la démo', 'error');
  } finally {
    document.getElementById('loadDemoBtn').innerHTML = `
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><polygon points="4,2 14,8 4,14" fill="currentColor"/></svg>
      Charger la démo
    `;
    document.getElementById('loadDemoBtn').disabled = false;
  }
}

// ── Statistiques hero ────────────────────────────────────────────────────────
function showStats(metrics) {
  document.getElementById('heroStats').style.display = 'grid';
  document.getElementById('statDist').textContent = metrics.total_distance_km?.toFixed(1) ?? '—';
  document.getElementById('statSpd').textContent = metrics.avg_speed_kmh?.toFixed(1) ?? '—';
  document.getElementById('statAnom').textContent = metrics.anomaly_count ?? '0';
  document.getElementById('statPts').textContent = metrics.point_count ?? '—';
}

// ── Liste des trajectoires ───────────────────────────────────────────────────
async function loadTrajectoryList() {
  const container = document.getElementById('trajectoriesList');

  try {
    const res = await fetch('/api/trajectories/');
    const data = await res.json();
    const list = data.trajectories;

    if (!list || list.length === 0) {
      container.innerHTML = '<p class="empty-state">Aucune trajectoire sauvegardée pour l\'instant.</p>';
      return;
    }

    container.innerHTML = `<div class="traj-grid">${list.map(renderCard).join('')}</div>`;

    list.forEach(t => {
      const card = document.getElementById(`card-${t.id}`);
      card.addEventListener('click', (e) => {
        if (e.target.closest('.btn-delete')) return;
        loadTrajectoryDetail(t.id);
        document.querySelectorAll('.traj-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
      });

      card.querySelector('.btn-delete').addEventListener('click', () => deleteTrajectory(t.id));
    });
  } catch (err) {
    container.innerHTML = '<p class="empty-state">Erreur de chargement.</p>';
  }
}

function renderCard(t) {
  const date = new Date(t.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  const hasAnomalies = (t.anomaly_count || 0) > 0;

  return `
    <div class="traj-card" id="card-${t.id}">
      <div class="traj-card-header">
        <span class="traj-card-name">${escHtml(t.name)}</span>
        <span class="traj-card-date">${date}</span>
      </div>
      <div class="traj-card-metrics">
        <div class="metric-mini">
          <div class="val">${(t.total_distance_km || 0).toFixed(1)}</div>
          <div class="lbl">km</div>
        </div>
        <div class="metric-mini">
          <div class="val">${(t.avg_speed_kmh || 0).toFixed(0)}</div>
          <div class="lbl">km/h moy.</div>
        </div>
        <div class="metric-mini">
          <div class="val">${t.point_count || 0}</div>
          <div class="lbl">points</div>
        </div>
      </div>
      <div class="traj-card-footer">
        <span class="badge ${hasAnomalies ? 'badge-danger' : 'badge-success'}">
          ${hasAnomalies ? `⚠ ${t.anomaly_count} anomalie(s)` : '✓ Aucune anomalie'}
        </span>
        <button class="btn-delete">Supprimer</button>
      </div>
    </div>
  `;
}

async function loadTrajectoryDetail(id) {
  try {
    const res = await fetch(`/api/trajectories/${id}/`);
    const data = await res.json();
    showStats(data.metrics);
    renderTrajectoryOnMap(data.points);
    document.getElementById('map').scrollIntoView({ behavior: 'smooth' });
  } catch {
    showToast('❌ Erreur lors du chargement', 'error');
  }
}

async function deleteTrajectory(id) {
  if (!confirm('Supprimer cette trajectoire ?')) return;
  try {
    await fetch(`/api/trajectories/${id}/delete/`, { method: 'DELETE' });
    showToast('🗑️ Supprimée.', 'success');
    loadTrajectoryList();
  } catch {
    showToast('❌ Erreur de suppression', 'error');
  }
}

// ── Toast ────────────────────────────────────────────────────────────────────
let toastTimer = null;

function showToast(message, type = '') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast show${type ? ` toast-${type}` : ''}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}

// ── Utilitaires ──────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
