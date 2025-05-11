import { sha512 } from 'https://esm.sh/@noble/hashes/sha512';
import { etc, sign } from "https://esm.sh/@noble/ed25519";
import { DFS3_USERS, toBytes, base64ToBuffer, bufferToBase64, unlockPrivateKey } from './common.js';

// Error: etc.sha512Sync not set
etc.sha512Sync = sha512;


// ---
// Utilidades: format size
// ---
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}


// ---
// Utilidades: format date
// ---
function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' });
}


async function loadFiles() {

  // Obtener archivos desde la API
  const accessToken = sessionStorage.getItem('access_token');
  const res = await fetch('/api/v1/files', { headers: { 'Authorization': 'Bearer ' + accessToken } });

  // Token inválido o expirado, redirigir al login
  if (res.status === 401) {
    sessionStorage.clear();
    window.location.href = 'login.html';
    return;
  }

  if (!res.ok) {
    $('#empty-msg').text('Error al cargar archivos.').removeClass('text-muted').addClass('text-danger');
    return;
  }

  const files = await res.json();
  if (files.length > 0) {
    $('#empty-msg').hide();
    files.forEach(file => {
      $('#file-list').append(`
        <tr>
          <td>${file.name}</td>
          <td>${formatSize(file.size)}</td>
          <td>${formatDate(file.creation_date)}</td>
          <td>
            <button class="btn btn-sm btn-outline-primary" data-id="${file.file_id}">Descargar</button>
            <button class="btn btn-sm btn-outline-secondary" data-id="${file.file_id}">Compartir</button>
          </td>
        </tr>
      `);
    });
  }

}


// ---
// main
// ---
$(function () {

  // Hay usuarios? 
  const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
  if (Object.keys(users).length === 0) {
    window.location.href = 'register.html';
    return;
  }

  // Cargamos info usuario
  const userId = sessionStorage.getItem('active_user_id') || '';
  if (!userId) {
    window.location.href = 'login.html';
    return;
  }

  const alias = users[userId].alias;
  $('#user-alias').text(alias);

  // Obtenemos archivos desde la API y mostramos
  loadFiles(); 

  // Botón cerrar sesión (limpia storage y redirige)
  $('#logout-btn').click(() => {
    sessionStorage.clear();
    window.location.href = 'login.html'; 
  });

  // Botón subir nuevo archivo
  $('#new-upload-btn').click(() => {
    window.location.href = 'upload.html';
  });

});

