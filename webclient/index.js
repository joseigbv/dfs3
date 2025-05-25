import { DFS3_USERS, base64ToBuffer } from './common.js';
import { decryptFile } from './crypto.js';


// ---
// Variables globales
// ---
const accessToken = sessionStorage.getItem('access_token') || '';
const privateKey = base64ToBuffer(sessionStorage.getItem('private_key') || '');
const userId = sessionStorage.getItem('active_user_id') || '';
const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
const currentUser = users[userId] ?? {};
const publicKey = base64ToBuffer(currentUser.publicKeyB64 || '');


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
  return d.toLocaleString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}


// ---
// Auxiliar para descarga de ficheros
// ---
function downloadFile(data, fileName, mimeType = 'application/octet-stream') {
  const blob = new Blob([data], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}


// ---
// Carga por API listado de ficheros para userId y muestra
// ---
async function loadFiles() {
  const res = await fetch('/api/v1/files', { 
    headers: { 'Authorization': 'Bearer ' + accessToken },
    method: 'GET'
  });

  // Token inválido o expirado, redirigir al login
  if (res.status === 401) {
    sessionStorage.clear();
    window.location.href = 'login.html';
    return;
  }

  if (!res.ok) {
    $('#empty-msg')
      .text('Error al cargar archivos.')
      .removeClass('text-muted')
      .addClass('text-danger');

    return;
  }

  const files = await res.json();
  if (files.length > 0) {
    files.forEach(file => {
      const iconClass = getIconForMimeType(file.mimetype);
      $('#file-list').append(`
        <tr>
          <td>
            <a href="#" class="download-lnk text-decoration-none" data-id="${file.file_id}" data-filename="${file.name}">
              ${file.name}
            </a>
          </td>
          <td>${formatSize(file.size)}</td>
          <td>${formatDate(file.creation_date)}</td>
          <td>
            <!--
            <button class="btn btn-sm btn-outline-primary download-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-download me-1"></i>
              Descargar
            </button>
            -->
            <button class="btn btn-sm btn-outline-primary share-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-share me-1"></i>
              Compartir
            </button>
            <button class="btn btn-sm btn-outline-secondary rename-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-pencil me-1"></i>
              Renombrar
            </button>
            <button class="btn btn-sm btn-outline-secondary copy-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-clipboard me-1"></i>
              Copiar
            </button>
            <button class="btn btn-sm btn-outline-secondary delete-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-trash me-1"></i>
              Borrar
            </button>
          </td>
          <td><i class="bi ${iconClass} me-2 fs-5 text-muted" title="${file.mimetype}"></i></td>
        </tr>
      `);
    });
    $('#empty-msg').hide();
  }
}


// ---
// main
// ---
$(function () {
  if (Object.keys(users).length === 0) {
    window.location.href = 'register.html';
    return;
  }

  if (!userId || !currentUser || !accessToken) {
    sessionStorage.clear();
    window.location.href = 'login.html';
    return;
  }

  // Mostramos usuario actual
  $('#user-alias').text(currentUser.name || currentUser.alias);

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


function getIconForMimeType(mimetype) {
  if (!mimetype) return 'bi-file-earmark';

  if (mimetype.startsWith('image/')) return 'bi-file-earmark-image';
  if (mimetype === 'application/pdf') return 'bi-file-earmark-pdf';
  if (mimetype.startsWith('video/')) return 'bi-file-earmark-play';
  if (mimetype.startsWith('audio/')) return 'bi-file-earmark-music';
  if (mimetype === 'application/zip' || mimetype === 'application/x-tar') return 'bi-file-earmark-zip';
  if (mimetype === 'text/plain') return 'bi-file-earmark-text';
  if (mimetype.includes('word')) return 'bi-file-earmark-word';
  if (mimetype.includes('excel') || mimetype.includes('spreadsheet')) return 'bi-file-earmark-excel';
  if (mimetype.includes('presentation')) return 'bi-file-earmark-slides';

  return 'bi-file-earmark'; // icono genérico por defecto
}


// ---
// Click en botones 'descargar'
// ---
$(document).on('click', '.download-lnk', async function (e) {
  // evita navegación
  e.preventDefault(); 

  const fileId = $(this).data('id');
  const fileName = $(this).data('filename');

  try {
    // Primero buscamos metadatos
    const resMeta = await fetch(`/api/v1/files/${fileId}/meta`, {
      headers: { 'Authorization': 'Bearer ' + accessToken },
      method: 'GET'
    });

    if (resMeta.status === 401) {
      sessionStorage.clear();
      window.location.href = 'login.html';
      return;
    } 

    if (!resMeta.ok) {
      const e = await resMeta.text();
      throw new Error(e);
    }

    const metadata = await resMeta.json();

    // Ahora descargamos datos
    const response = await fetch(`/api/v1/files/${fileId}`, {
      headers: { 'Authorization': 'Bearer ' + accessToken },
      method: 'GET'
    });

    if (response.status === 401) {
      sessionStorage.clear();
      window.location.href = 'login.html';
      return;
    } 

    if (!response.ok) {
      const e = await response.text();
      throw new Error(e);
    }

    const blob = await response.blob();
    const fileDataEncrypted = new Uint8Array(await blob.arrayBuffer()); 
    const publicKey = base64ToBuffer(currentUser.public_key);

    // Desciframos para el propietario
    const fileData = await decryptFile(
      metadata, 
      fileDataEncrypted,  
      userId, 
      privateKey, 
      publicKey
    ); 

    // Descargamos fichero descifrado con sus metadatos correspondientes
    // Ojo, usamos el nombre del fichero en la tabla, no de metadatos !!!
    downloadFile(fileData, fileName, metadata.mimetype);

  } catch (e) {
    alert('Error al descargar');
    console.log(e);
  }

});


// Botón compartir archivo
$(document).on('click', '.share-btn', async function () {
  const fileName = $(this).data('filename');
  alert(`No implementado: ${fileName}`);
});


// Botón renombrar archivo
$(document).on('click', '.rename-btn', async function () {
  const fileName = $(this).data('filename');
  alert(`No implementado: ${fileName}`);
});


// Botón copiar archivo
$(document).on('click', '.copy-btn', async function () {
  const fileName = $(this).data('filename');
  alert(`No implementado: ${fileName}`);
});


// Botón borrar archivo
$(document).on('click', '.delete-btn', async function () {
  const fileName = $(this).data('filename');
  alert(`No implementado: ${fileName}`);
});

