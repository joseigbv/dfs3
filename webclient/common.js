// common.js

// Donde guardamos las claves de usuario en el navegador
export const DFS3_USERS = 'dfs3_users';


// --- 
// convierte texto a Uint8Array
// --- 
export function toBytes(str) {
  return new TextEncoder().encode(str);
}


// ---
// convierte Uint8Array a texto
// ---
export function toText(bytes) {
  return new TextDecoder().decode(bytes);
}


// ---
// convierte de binario a base64
// ---
export function bufferToBase64(buf) {
  return btoa(String.fromCharCode(...buf));
}


// ---
// convierte de base64 a binario
// ---
export function base64ToBuffer(b64) {
  return Uint8Array.from(atob(b64), c => c.charCodeAt(0));
}


// ---
// genera una clave base a partir de una una password
// ---
async function getKeyMaterial(password) {
  const enc = new TextEncoder();
  return crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]);
}


// ---
// deriva una clave criptografica segura a partir de una clave base
// ---
async function deriveKey(keyMaterial, salt) {
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}


// ---
// cifra una clave privada 
// ---
export async function encryptPrivateKey(privateKey, password) {
  const keyMaterial = await getKeyMaterial(password);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const aesKey = await deriveKey(keyMaterial, salt);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, privateKey);
  const encryptedPrivateKey = new Uint8Array(ciphertext);
        
  return {
    encryptedPrivateKey,
    salt,
    iv
  }
} 


// ---
// descifra una clave privada
// ---
export async function decryptPrivateKey(encryptedPrivateKey, password, salt, iv) {
  const keyMaterial = await getKeyMaterial(password);
  const aesKey = await deriveKey(keyMaterial, salt);
  const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, aesKey, encryptedPrivateKey);
  const privateKey = new Uint8Array(decrypted);

  return privateKey;
}


// ---
// genera un SHA-256 en formato hexadecimal
// ---
export async function sha256Hex(input) {
  const digest = await crypto.subtle.digest("SHA-256", input);
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
}


// ---
// desbloquea la clave privada de userId usando contraseña
// ---
export async function unlockPrivateKey(userId, password) {
  const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
  const user = users[userId];

  if (!user) throw new Error("Usuario no encontrado");

  const salt = base64ToBuffer(user.salt);
  const iv = base64ToBuffer(user.iv);
  const encryptedPrivateKey = base64ToBuffer(user.encrypted_private_key);

  return await decryptPrivateKey(encryptedPrivateKey, password, salt, iv);
} 

