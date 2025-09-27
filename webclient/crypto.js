import { sha512 } from 'https://esm.sh/@noble/hashes@1.4.0/sha512';
import { etc, sign, getPublicKey, utils } from "https://esm.sh/@noble/ed25519";
import { DFS3_USERS, base64ToBuffer, bufferToBase64, sha256Hex } from './common.js';

// Hemos tenido que usar esta libreria, la unica que funcionaba con navegador para derivar claves ???
import sodium from 'https://esm.sh/libsodium-wrappers'; 
await sodium.ready;

// Error: etc.sha512Sync not set
etc.sha512Sync = sha512;


// ---  
// Genera claves y devuelve ambas
// ---
export async function generateKeys(password) {
  const privateKey = utils.randomPrivateKey();
  const publicKey = await getPublicKey(privateKey);
  return { publicKey, privateKey };
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
export async function authorizeUserForFile(owner, metadata, oPrivateKey, oPublicKey, userId, publicKey) {
  // Primero necesitamos buscar y extraer la clave cifrada del propietario
  const ownerKey = metadata.authorized_users.find(user => user.user_id === owner);
  const encryptedKey = base64ToBuffer(ownerKey.encrypted_key);
  const iv = base64ToBuffer(ownerKey.iv);

  // Desciframos la clave simetrica compartida con la que se cifro el fichero
  const decryptedKey = await decryptSymmetricKeyFromUser(
    encryptedKey,       // Clave simetrica cifrada
    iv,                 // Vector de inicializacion usado en cifradode la clave
    oPrivateKey,        // Clave privada del receptor (propietario)
    oPublicKey,         // Clave publica del receptor (propietario)
    oPublicKey          // Clave publica del emisor (propietario)
  );

  // Ahora la ciframos con la clave pública del destinatario 
  const encryptedKey_ = await encryptSymmetricKeyForUser(
    decryptedKey,       // simetrica a cifrar
    oPrivateKey,        // clave privada del emisor (32 bytes)
    oPublicKey,         // clave publica del emisor (32 bytes), necesario para derivar
    publicKey           // clave publica del receptor (32 bytes)
  );

  // Y devolvemos authorized_file
  return {
     user_id: userId,
     encrypted_key: bufferToBase64(encryptedKey_.key),
     iv: bufferToBase64(encryptedKey_.iv)
  };
}


// ---
// Cifra el fichero (file) subido al navegador usando una contrasenia simetrica aleatoria.
// Esta contrasenia a su vez, se cifra a su vez para el propietario usando su clave publica
// Solo el propietario (userId) puede cifrar el fichero y dar permiso a otros.
// ---
export async function encryptFile(fileDataPlain, fileName, fileSize, fileType, userId, privateKey, publicKey) {
  // Construimos clave simetrica random que usamos para cifrar el fichero
  const symKey = crypto.getRandomValues(new Uint8Array(32)); // AES-256
  const ivData = crypto.getRandomValues(new Uint8Array(12));
  const aesKey = await crypto.subtle.importKey("raw", symKey, "AES-GCM", false, ["encrypt"]);
  const encrypted = await crypto.subtle.encrypt({ name: "AES-GCM", iv: ivData }, aesKey, fileDataPlain);
  const fileDataEncrypted = new Uint8Array(encrypted)

  // Cifrar la clave simétrica con la clave pública de nuestro usuario (Ed25519)
  // ... como Ed25519 no cifra directamente, necesitamos usar clave derivada x25519
  const encryptedKey = await encryptSymmetricKeyForUser(
    symKey,     // simetrica a cifrar
    privateKey, // clave privada del emisor (32 bytes)
    publicKey,  // clave publica del emisor (32 bytes), necesario para derivar
    publicKey   // clave publica del receptor (32 bytes)
  );

  // Construimos estructura de metadatos
  const metadata = {
    filename: fileName,
    file_id: await sha256Hex(fileDataEncrypted),
    size: fileSize,
    mimetype: fileType || 'application/octet-stream',
    sha256: await sha256Hex(fileDataPlain),
    iv: bufferToBase64(ivData),
    tags: ['test', 'dfs3'],
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
export async function decryptFile(metadata, fileDataEncrypted, userId, privateKey, publicKey, ownerPublicKey) {
  // Extraemos la clave compartida cifrada para el usuario userId
  const user = metadata.authorized_users.find(user => user.user_id === userId);
  const encryptedKey = base64ToBuffer(user.encrypted_key);
  const ivKey = base64ToBuffer(user.iv);

  // Desciframos la clave simetrica compartida con la que se cifro el fichero
  const decryptedKey = await decryptSymmetricKeyFromUser(
    encryptedKey,       // Clave simetrica cifrada
    ivKey,              // Vector de inicializacion usado en cifradode la clave
    privateKey,         // Clave privada del receptor
    publicKey,          // Clave publica del receptor
    ownerPublicKey      // Clave publica del emisor (propietario)
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

