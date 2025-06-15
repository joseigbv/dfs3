import { DFS3_USERS, base64ToBuffer } from './common.js';
import { encryptFile, authorizeUserForFile } from './crypto.js';


// ---
// Globales
// ---
const accessToken = sessionStorage.getItem('access_token') || '';
const privateKey = base64ToBuffer(sessionStorage.getItem('private_key') || '');
const userId = sessionStorage.getItem('active_user_id') || '';
const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
const currentUser = users[userId] ?? {};
const publicKey = base64ToBuffer(currentUser.public_key || '');


// ---
// Subida de fichero a la API
// ---
async function uploadFile(metadata, fileDataEncrypted) {
  const fileBlob = new Blob(
    [fileDataEncrypted], 
    { type: metadata.mimetype || "application/octet-stream" }
  );

  const formData = new FormData();
  formData.append('data', fileBlob, metadata.filename);
  formData.append('metadata', JSON.stringify(metadata));

  // Enviamos a la api
  const response = await fetch('/api/v1/files', {
    headers: { 'Authorization': 'Bearer ' + accessToken },
    method: 'POST',
    body: formData
  });

  // Redirigir a login si no autorizado
  if (response.status === 401) {
    window.location.href = 'login.html';
    return;
  }

  // Si ha habido problemas, generamos una excepcion
  if (!response.ok) {
    const e = await response.text();
    throw new Error(e);
  }
}


// ---
// main
// --
$(function () {
  const $error = $('#error-msg');
  const $status = $('#upload-status');

  if (!userId || !currentUser || !accessToken) {
    sessionStorage.clear();
    window.location.href = 'index.html';
    return;
  }

  $('#upload-btn').prop('disabled', true);
  $('#file-input').on('change', function () {
    $('#upload-btn').prop('disabled', this.files.length === 0);
  });

  // ---
  // Click upload-btn
  // ---
  $('#upload-btn').on('click', async () => {

    const file = $('#file-input')[0].files[0];
    if (!file) {
      $error.text('Selecciona un archivo primero.');
      return;
    }

    // Para evitar reintentos, reset status, show spinner
    $('#upload-form :input').prop('disabled', true);
    $error.text('');
    $status.show(); 

    // Para medir rendimiento, empezamos
    performance.mark('start-upload');

    // encryptFile espera un array de bytes
    const fileDataPlain = new Uint8Array(await file.arrayBuffer());

    // Ojo con el scope de una variable
    let metadata, fileDataEncrypted;
    try {
      // Ciframos datos para nosotros mismos y devolvemos metadatos
      ({ metadata, fileDataEncrypted } = await encryptFile(
        fileDataPlain,	// Contenido fichero devuelto por el navegador
        file.name,      // Nombre del fichero
        file.size,      // Tamanio en bytes
        file.type,      // Mimetype
        userId, 	// ID del que cifra (propietario)
        privateKey,	// Clave privada del que cifra
        publicKey,	// Clave publica del que cifra y para quien cifra
      ));

      // TODO: Pendiente integrar con API REST
      await uploadFile(metadata, fileDataEncrypted);

      // Para medir rendimiento, terminamos
      performance.mark('end-upload');
      performance.measure('upload-time', 'start-upload', 'end-upload');
      console.log(performance.getEntriesByName('upload-time'));
  
      // Redirigimos a pagina principal
      $status.text("Subida completada. Redirigiendo...");
    //  setTimeout(() => window.location.href = 'index.html', 2000);

    } catch(e) {
      $status.hide();
      $error.text("Error al cifrar o enviar.");
      $('#upload-form :input').prop('disabled', false);
      console.log(e);
    }

  });

});

