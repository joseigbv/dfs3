import { DFS3_USERS, base64ToBuffer } from './common.js';
import { decryptFile } from './crypto.js';
import { authorizeUserForFile } from './crypto.js';
 

// ---
// Variables globales
// ---
const accessToken = sessionStorage.getItem('access_token') || '';
const privateKey = base64ToBuffer(sessionStorage.getItem('private_key') || '');
const userId = sessionStorage.getItem('active_user_id') || '';
const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
const currentUser = users[userId] ?? {};
const publicKey = base64ToBuffer(currentUser.public_key || '');


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

  $('#file-list').empty();

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
            <button class="btn btn-sm btn-outline-primary download-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-download me-1"></i>
              Descargar
            </button>
            <button class="btn btn-sm btn-outline-secondary share-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-share me-1"></i>
              Compartir
            </button>
            <button class="btn btn-sm btn-outline-secondary rename-btn" data-id="${file.file_id}" data-filename="${file.name}">
              <i class="bi bi-pencil me-1"></i>
              Renombrar
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
    $('#file-list').show();
  }
  else {
    $('#empty-msg').text('No hay archivos aún.').show();
  }
}


// ---
// Ultima fase de compartir
// ---
async function handleShareConfirmation(filename, metadata) {
  const selectedOption = $('#user-select option:selected');
  const destUserId = selectedOption.val();
  const destPublicKey = base64ToBuffer(selectedOption.data('pubkey'));

  if (!destUserId || !destPublicKey) {
    $('#share-error').removeClass('d-none').text('Selecciona un usuario válido.');
    return;
  }

  try {
    // Añadimos nuevo usuario a la lista de autorizados
    const authorizedUser = await authorizeUserForFile(
      userId,         // Owner del fichero (nosotros)
      metadata,       // Metadatos del fichero a autorizar
      privateKey,     // Clave privada del propietario
      publicKey,      // Clave publica del propietario
      destUserId,     // Id del destinatario
      destPublicKey   // Clave publica del destinatario
    );

    const res = await fetch(`/api/v1/files/share`, {
      headers: { 
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json'
      },
      method: 'POST',
      body: JSON.stringify({
        filename,
        authorized_users: [ authorizedUser ]
      })
    });

    if (!res.ok) {
      const e = await res.text();
      throw new Error(e);
    }
 
    // Ocultamos cuadro de dialogo
    bootstrap.Modal.getInstance(document.getElementById('shareModal')).hide();

    // Refrescamos tabla de ficheros
    setTimeout(() => loadFiles(), 2000);

  } catch (e) {
    //$('#share-error').removeClass('d-none').text('Error: ' + err.message);
    alert("Error al compartir fichero");
    console.log(e);
  }
}


// ---
// Abre dialogo modal para compartir
// ---
async function openShareModal(filename, metadata) {
  try {
    // Extraemos lista de usuarios
    const res = await fetch('/api/v1/users', {
      headers: { Authorization: 'Bearer ' + accessToken }
    });

    const users = await res.json();

    // Cargamos usuarios en cuadro de dialogo
    const select = $('#user-select');
    select.empty().append('<option selected disabled>Elige un alias...</option>');
    users.forEach(user => {
      select.append(`<option value="${user.user_id}" data-pubkey="${user.public_key}">${user.alias} (${user.public_key.slice(0, 18)}...)</option>`);
    });

    $('#share-error').addClass('d-none').text('');

    // Asociamos un solo handler temporal
    $('#confirm-share-btn').off('click').on('click', async function () {
      await handleShareConfirmation(filename, metadata);
    });

    // Mostramos cuadro de dialogo modal
    const modal = new bootstrap.Modal(document.getElementById('shareModal'));
    modal.show();

  } catch (e) {
    alert("Error al cargar usuarios");
    console.log(e);
  }
}


// ---
// Devuelve icono segun mimetype
// ---
function getIconForMimeType(mimetype) {
  // control de errores
  if (!mimetype) return 'bi-file-earmark';

  // TODO ir rellenando con opciones...
  if (mimetype.startsWith('image/')) return 'bi-file-earmark-image';
  if (mimetype === 'application/pdf') return 'bi-file-earmark-pdf';
  if (mimetype.startsWith('video/')) return 'bi-file-earmark-play';
  if (mimetype.startsWith('audio/')) return 'bi-file-earmark-music';
  if (mimetype === 'application/zip' || mimetype === 'application/x-tar') return 'bi-file-earmark-zip';
  if (mimetype === 'text/plain') return 'bi-file-earmark-text';
  if (mimetype.includes('word')) return 'bi-file-earmark-word';
  if (mimetype.includes('excel') || mimetype.includes('spreadsheet')) return 'bi-file-earmark-excel';
  if (mimetype.includes('presentation')) return 'bi-file-earmark-slides';

  // icono genérico por defecto
  return 'bi-file-earmark'; 
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

  // Mostramos mensaje de update
  $('#file-list').hide();
  $('#empty-msg')
    .text('Actualizando archivos...')
    .removeClass('text-danger')
    .addClass('text-mute')
    .show();

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


// ---
// Click en botones 'descargar'
// ---
$(document).on('click', '.download-lnk, .download-btn', async function (e) {
  // evita navegación cuando se usa el link
  e.preventDefault(); 

  const fileId = $(this).data('id');
  const fileName = $(this).data('filename');

  try {
    // Para medir rendimiento en descarga
    performance.mark('start-download');

    // Primero buscamos metadatos de fichero
    const resFile = await fetch(`/api/v1/files/${fileName}`, {
      headers: { 'Authorization': 'Bearer ' + accessToken },
      method: 'GET'
    });

    if (resFile.status === 401) {
      sessionStorage.clear();
      window.location.href = 'login.html';
      return;
    } 

    if (!resFile.ok) {
      const e = await resFile.text();
      throw new Error(e);
    }

    // Reconstruccion parcial de metadata a partir de cabeceras api
    const metadata = {
      'file_id': resFile.headers.get("X-DFS3-File-ID"),
      'owner': resFile.headers.get("X-DFS3-Owner"),
      'size': resFile.headers.get("X-DFS3-Size"), 
      'mimetype': resFile.headers.get("X-DFS3-Mimetype"),
      'sha256': resFile.headers.get("X-DFS3-SHA256"),
      'iv': resFile.headers.get("X-DFS3-IV"),
      'authorized_users': [{
        'user_id': userId,
        'encrypted_key': resFile.headers.get("X-DFS3-Encrypted-Key"),
        'iv': resFile.headers.get("X-DFS3-IV-Key")
      }],
      // ...
    };

    const blob = await resFile.blob();
    const fileDataEncrypted = new Uint8Array(await blob.arrayBuffer()); 

    // Clave publica del propietario (quien cifro el fichero y dio permisos)
    const ownerPublicKey = base64ToBuffer(resFile.headers.get("X-DFS3-Public-Key"));
    console.log(ownerPublicKey);

    // Desciframos para el propietario
    const fileData = await decryptFile(
      metadata, // OJO!!!
      fileDataEncrypted,  
      userId, 
      privateKey, 
      publicKey,
      ownerPublicKey
    );

    // Descargamos fichero descifrado con sus metadatos correspondientes
    // Ojo, usamos el nombre del fichero en la tabla, no de metadatos !!!
    downloadFile(fileData, fileName, metadata.mimetype);

    // Calculamos rendimiento y mostramos por consola
    performance.mark('end-download');
    performance.measure('download-time', 'start-download', 'end-download');
    console.log(performance.getEntriesByName('download-time'));

  } catch (e) {
    alert('Error al descargar');
    console.log(e);
  }
});


// Botón compartir archivo
$(document).on('click', '.share-btn', async function () {
  // Mostramos mensaje de update
  /*
  $('#file-list').hide();
  $('#empty-msg')
    .text('Actualizando archivos...')
    .removeClass('text-danger')
    .addClass('text-mute')
    .show();
  */

  // Qué deseamos compartir?
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

    // Solicitamos con que usuario queremos compartir
    openShareModal(fileName, metadata);

  } catch (e) {
    alert('Error al compartir');
    console.log(e);
  }
});


// Botón renombrar archivo
$(document).on('click', '.rename-btn', async function () {
  // Mostramos mensaje de update
  $('#file-list').hide();
  $('#empty-msg')
    .text('Actualizando archivos...')
    .removeClass('text-danger')
    .addClass('text-mute')
    .show();

  // Qué deseamos renombrar?
  const fileName = $(this).data('filename');
  const newName = prompt('Nuevo nombre:', fileName);

  try {
    const res = await fetch(`/api/v1/files/${fileName}`, {
      headers: { 
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json'
      },
      method: 'PATCH',
      body: JSON.stringify({ new_name: newName })
    });

    if (res.status === 401) {
      sessionStorage.clear();
      window.location.href = 'login.html';
      return;
    } 

    if (!res.ok) {
      const e = await res.text();
      throw new Error(e);
    }

    // Refrescamos tabla de ficheros
    setTimeout(() => loadFiles(), 2000);

  } catch (e) {
    alert('Error al renombrar');
    console.log(e);
  }
});


// Botón borrar archivo
$(document).on('click', '.delete-btn', async function () {
  // Mostramos mensaje de update
  $('#file-list').hide();
  $('#empty-msg')
    .text('Actualizando archivos...')
    .removeClass('text-danger')
    .addClass('text-mute')
    .show();

  // Qué deseamos borrar?
  const fileName = $(this).data('filename');

  try {
    const res = await fetch(`/api/v1/files/${fileName}`, {
      headers: { 'Authorization': 'Bearer ' + accessToken },
      method: 'DELETE'
    });

    if (res.status === 401) {
      sessionStorage.clear();
      window.location.href = 'login.html';
      return;
    } 

    if (!res.ok) {
      const e = await res.text();
      throw new Error(e);
    }

    // Refrescamos tabla de ficheros
    setTimeout(() => loadFiles(), 2000);

  } catch (e) {
    alert('Error al borrar');
    console.log(e);
  }
});

