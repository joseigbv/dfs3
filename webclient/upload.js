// Hemos tenido que usar esta libreria, la unica que funcionaba con navegador ???
import sodium from 'https://esm.sh/libsodium-wrappers';
import { bufferToBase64, base64ToBuffer, sha256Hex } from './common.js';

// Asegura que sodium está cargado antes de usarlo
await sodium.ready;


// ---
// mock api para pruebas
// ---
const originalFetch = window.fetch;
        
window.fetch = async (url, options) => {
  if (url.endsWith('/files')) {
    console.log('[MOCK] POST /files', options.body);
    return new Response(JSON.stringify({ status: 'stored' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    }); 
  }   

  // Resto de fetchs sin cambios
  return originalFetch(url, options);
};


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
  // limpieza siempre
  URL.revokeObjectURL(url); 
}


// --
// Deriva una clave compartida X25519 entre emisor y receptor...
// ... y cifra la clave simétrica con ella usando AES-GCM.
// --
async function encryptSymmetricKeyForUser(symKey, senderPrivateKeyEd, senderPublicKeyEd, recipientPublicKeyEd) {
  // Ojo, esta libreria espera un formato diferente para la clave privada (private + public) !!!
  const senderKeyEd = new Uint8Array([...senderPrivateKeyEd, ...senderPublicKeyEd]);

  // Convertir la clave privada (64 bytes) / publica (32 bytes) Ed25519 a X25519
  const senderPrivateKeyX = sodium.crypto_sign_ed25519_sk_to_curve25519(senderKeyEd);
  const recipientPublicKeyX = sodium.crypto_sign_ed25519_pk_to_curve25519(recipientPublicKeyEd);

  // Creamos un secreto compartido sender / recipient (Diffie-Hellman sobre Curve25519)
  const sharedSecret = sodium.crypto_scalarmult(
    senderPrivateKeyX,  // Uint8Array de 32 bytes
    recipientPublicKeyX // Uint8Array de 32 bytes
  );

  // Con el secreto compartido, creamos una clave simetrica a partir de su hash y generamos el handle (aesKey)
  const rawKey = await crypto.subtle.digest('SHA-256', sharedSecret);
  const aesKey = await crypto.subtle.importKey('raw', rawKey, 'AES-GCM', false, ['encrypt']);

  // Ciframos la clave simetrica con el secreto compartido
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, aesKey, symKey);
  const encryptedKey = new Uint8Array(encrypted);

  // devolvemos una estructura con la clave cifrada y el vector de inicializacion
  return { 
     key: encryptedKey,
     iv: iv 
  };
}


// --
// Descifra la clave simétrica compartida usando la clave privada Ed25519 del receptor
// y la clave pública Ed25519 del emisor (ambas convertidas a X25519).
// --
async function decryptSymmetricKeyFromUser(encryptedKey, iv, recipientPrivateKeyEd, recipientPublicKeyEd, senderPublicKeyEd) {
  // Ojo, esta libreria espera un formato diferente para la clave privada (private + public) !!!
  const recipientKeyEd = new Uint8Array([...recipientPrivateKeyEd, ...recipientPublicKeyEd]);

  // Convertir Ed25519 a X25519
  const recipientPrivateX = sodium.crypto_sign_ed25519_sk_to_curve25519(recipientKeyEd);
  const senderPublicX = sodium.crypto_sign_ed25519_pk_to_curve25519(senderPublicKeyEd);

  // Derivar clave compartida con ECDH
  const sharedSecret = sodium.crypto_scalarmult(recipientPrivateX, senderPublicX);

  // Derivar clave AES desde el secreto compartido
  const rawKey = await crypto.subtle.digest("SHA-256", sharedSecret);
  const aesKey = await crypto.subtle.importKey("raw", rawKey, "AES-GCM", false, ["decrypt"]);

  // Descifrar la clave simétrica
  const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, aesKey, encryptedKey);
  const decryptedKey = new Uint8Array(decrypted);

  // devuelve la clave simétrica original
  return decryptedKey; 
}


// ---
// Permitimos a otro usuario acceder al fichero, es decir, ciframos la clave
// simetrica tambien para el usando su clave publica
// ---
async function authorizeUserForFile(metadata, oPrivateKey, oPublicKey, userId, publicKey) {
  // Primero necesitamos buscar y extraer la clave cifrada del propietario
  const ownerKey = metadata.authorized_users.find(user => user.user_id === metadata.owner);
  const encryptedKey = base64ToBuffer(ownerKey.encrypted_key);
  const iv = base64ToBuffer(ownerKey.iv);

  // Desciframos la clave simetrica compartida con la que se cifro el fichero
  const decryptedKey = await decryptSymmetricKeyFromUser(
    encryptedKey,	// Clave simetrica cifrada
    iv, 		// Vector de inicializacion usado en cifradode la clave
    oPrivateKey,	// Clave privada del receptor (propietario)
    oPublicKey, 	// Clave publica del receptor (propietario)
    oPublicKey		// Clave publica del emisor (propietario)
  );

  // Ahora la ciframos con la clave pública del destinatario 
  const encryptedKey_ = await encryptSymmetricKeyForUser(
    decryptedKey,	// simetrica a cifrar
    oPrivateKey,	// clave privada del emisor (32 bytes)
    oPublicKey,		// clave publica del emisor (32 bytes), necesario para derivar
    publicKey		// clave publica del receptor (32 bytes)
  );

  // Actualizamos metadatos
  metadata.authorized_users.push({
     user_id: userId,
     encrypted_key: bufferToBase64(encryptedKey_.key),
     iv: bufferToBase64(encryptedKey_.iv)
  });

  return metadata;
}


// ---
// Cifra el fichero (file) subido al navegador usando una contrasenia simetrica aleatoria.
// Esta contrasenia a su vez, se cifra a su vez para el propietario usando su clave publica
// Solo el propietario (userId) puede cifrar el fichero y dar permiso a otros.
// ---
async function encryptFile(file, userId, privateKey, publicKey) {
  const fileDataPlain = new Uint8Array(await file.arrayBuffer());

  // Construimos clave simetrica random que usamos para cifrar el fichero
  const symKey = crypto.getRandomValues(new Uint8Array(32)); // AES-256
  const ivData = crypto.getRandomValues(new Uint8Array(12));
  const aesKey = await crypto.subtle.importKey("raw", symKey, "AES-GCM", false, ["encrypt"]);
  const encrypted = await crypto.subtle.encrypt({ name: "AES-GCM", iv: ivData }, aesKey, fileDataPlain);
  const fileDataEncrypted = new Uint8Array(encrypted)

  // Cifrar la clave simétrica con la clave pública de nuestro usuario (Ed25519)
  // ... como Ed25519 no cifra directamente, necesitamos usar clave derivada x25519
  const encryptedKey = await encryptSymmetricKeyForUser(
    symKey,	// simetrica a cifrar
    privateKey,	// clave privada del emisor (32 bytes)
    publicKey,	// clave publica del emisor (32 bytes), necesario para derivar
    publicKey	// clave publica del receptor (32 bytes)
  );

  // Construimos estructura de metadatos
  const metadata = {
    file_id: await sha256Hex(fileDataEncrypted),
    filename: file.name,
    owner: userId,
    size: file.size,
    mimetype: file.type || 'application/octet-stream',
    tags: ['test', 'dfs3'],
    sha256: await sha256Hex(fileDataPlain),
    iv: bufferToBase64(ivData),
    authorized_users: [
      {
        user_id: userId,
        encrypted_key: bufferToBase64(encryptedKey.key),
        iv: bufferToBase64(encryptedKey.iv) 
      }
    ]
  };

  // Devolvemos metadatos y datos cifrados
  return { metadata: metadata, fileDataEncrypted: fileDataEncrypted };
}


// ---
// Descifra y devuelve el contenido de un fichero cifrado y con metadatos. 
// Es necesario que los metadatos incluyan la clave empleada, cifrada para el
// usuario identificado por userId, en posesion de su privateKey y publicKey.
// ---
async function decryptFile(metadata, fileDataEncrypted, userId, privateKey, publicKey) {
  // Extraemos la clave compartida cifrada para el usuario userId
  const user = metadata.authorized_users.find(user => user.user_id === userId);
  const encryptedKey = base64ToBuffer(user.encrypted_key);
  const ivKey = base64ToBuffer(user.iv);

  // TODO: Buscar clave publica del propietario si es distinto de userId
  const ownerPublicKey = publicKey;

  // Desciframos la clave simetrica compartida con la que se cifro el fichero
  const decryptedKey = await decryptSymmetricKeyFromUser(
    encryptedKey,	// Clave simetrica cifrada
    ivKey, 		// Vector de inicializacion usado en cifradode la clave
    privateKey, 	// Clave privada del receptor
    publicKey, 		// Clave publica del receptor
    ownerPublicKey	// Clave publica del emisor (propietario)
  );

  // Con la clave simetrica compartida original, desciframos fichero
  const aesKey = await crypto.subtle.importKey("raw", decryptedKey, "AES-GCM", false, ["decrypt"]);
  const ivData = base64ToBuffer(metadata.iv);
  const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv: ivData }, aesKey, fileDataEncrypted);
  const fileData = new Uint8Array(decrypted);

  // Verificamos el fichero original 
  const sha256 = await sha256Hex(fileData);
  if (sha256 !== metadata.sha256) {
    throw new Error('sha256 no coincide');
  }

  return fileData;
}


// ---
// Subida de fichero a la API
// ---
async function uploadFile(metadata, fileDataEncrypted) {
  const formData = new FormData();
  const fileBlob = new Blob([fileDataEncrypted], { type: metadata.mimetype || "application/octet-stream" });
  formData.append('file', fileBlob, metadata.filename);
  formData.append('metadata', JSON.stringify(metadata));

  // Enviamos a la api
  const response = await fetch('/files', {
    method: 'POST',
    body: formData
  });

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
  const $output = $('#output');

  // Comenzamos recuperando la clave privada sin cifrar y el user_id
  const privateKeyB64 = sessionStorage.getItem('dfs3_private_key');
  const userId = sessionStorage.getItem('active_user_id');

  if (!privateKeyB64 || !userId) {
    alert('No se ha iniciado sesión');
    window.location.href = 'index.html';
    return;
  }

  $('#upload-btn').prop('disabled', true);
  $('#file-input').on('change', function () {
    $('#upload-btn').prop('disabled', this.files.length === 0);
  });

  // Nuestra clave privada, necesaria para derivacion de claves
  const privateKey = base64ToBuffer(privateKeyB64);

  // Obtenemos la clave publica de nuestro usuario (cifraremos la clave simetrica para el) 
  const publicKeyB64 = JSON.parse(localStorage.getItem('dfs3_users'))[userId].public_key;
  const publicKey = base64ToBuffer(publicKeyB64);


  // ---
  // Click upload-btn
  // ---
  $('#upload-btn').on('click', async () => {
    $output.text('');
    $error.text('');

    const file = $('#file-input')[0].files[0];
    if (!file) {
      $error.text('Selecciona un archivo primero.');
      return;
    }

    // Ojo con el scope de una variable
    let metadata, fileDataEncrypted;
   
    try {
      // Ciframos datos para nosotros mismos y devolvemos metadatos
      ({ metadata, fileDataEncrypted } = await encryptFile(
        file,		// Estructura file devuelta por el navegador
        userId, 	// ID del que cifra (propietario)
        privateKey,	// Clave privada del que cifra
        publicKey,	// Clave publica del que cifra y para quien cifra
      ));

      // TODO: Pendiente integrar con API REST
      await uploadFile(metadata, fileDataEncrypted);
      $output.text('Archivo cifrado y enviado.');

      // ---
      // Prueba de aniadir un nuevo usuario, (de momento nosotros mismos)
      // ---
      metadata = await authorizeUserForFile(
        metadata, 	// Metadatos del fichero a autorizar
        privateKey, 	// Clave privada del propietario
        publicKey, 	// Clave publica del propietario
        userId, 	// Id del destinatario
        publicKey	// Clave publica del destinatario
      );

      // Solo para debug
      console.log(metadata);

    } catch(e) {
      $error.text("Error al cifrar o enviar.");
      console.log(e);
    }

    // ---
    // Temporal, para verificar que todo se descifra correctamente
    // ---

    try {   
      // Comprobamos que funciona el descifrado para el propietario
      const fileData = await decryptFile(
        metadata, 
        fileDataEncrypted, 
        userId, 
        privateKey, 
        publicKey
      );

      // Descargamos el fichero descifrado con metadatos originales
      downloadFile(fileData, metadata.filename, metadata.mimetype);

    } catch (e) {
      $error.text("Error al descifrar");
      console.log(e);
    }

  });
});

